# Maintenance Window and Compliance Reporting Reference

Supplementary reference for the SSM Patch Compliance Automator skill. Use
when configuring maintenance windows, sizing concurrency, building
compliance reports, or debugging patch-state issues.

## Maintenance-window lifecycle

| Stage | API | Description |
|---|---|---|
| Create | `create-maintenance-window` | Define schedule, duration, cutoff |
| Register targets | `register-target-with-maintenance-window` | Select instances (by tag, resource group, or instance IDs) |
| Register tasks | `register-task-with-maintenance-window` | Define what runs (AWS-RunPatchBaseline, custom runbook) |
| Monitor | `describe-maintenance-window-executions` | Track per-window execution status |
| Deregister | `deregister-task-with-maintenance-window` | Remove a task (does not cancel running executions) |
| Delete | `delete-maintenance-window` | Remove the window (running executions continue) |

## Schedule formats

SSM maintenance windows support two schedule formats:

**Cron expressions:**

```
cron(<Minutes> <Hours> <Day-of-month> <Month> <Day-of-week> <Year>)
```

| Field | Values | Wildcards |
|---|---|---|
| Minutes | 0-59 | `,` `-` `*` `/` |
| Hours | 0-23 | `,` `-` `*` `/` |
| Day-of-month | 1-31 | `,` `-` `*` `/` `?` `L` `W` |
| Month | 1-12 or JAN-DEC | `,` `-` `*` `/` |
| Day-of-week | 1-7 or SUN-SAT | `,` `-` `*` `/` `?` `L` `#` |
| Year | 1970-2199 | `,` `-` `*` `/` |

**Important:** Day-of-month and Day-of-week are mutually exclusive.
Use `?` in one when specifying the other.

**Rate expressions:**

```
rate(<value> <unit>)
```

| Example | Meaning |
|---|---|
| `rate(30 minutes)` | Every 30 minutes |
| `rate(4 hours)` | Every 4 hours |
| `rate(1 day)` | Every day at the creation time |

Rate expressions do NOT support schedules at a specific time. Use
cron for time-specific schedules.

## Concurrency and error-budget sizing

| Parameter | Effect | Example |
|---|---|---|
| `MaxConcurrency` | How many instances execute the task simultaneously | `1`, `5`, `10%`, `10` |
| `MaxErrors` | How many errors before the window is cancelled | `1`, `3`, `5%` |

**Concurrency math:**

For a fleet of 200 instances with `MaxConcurrency: 10%`:
- 20 instances patch simultaneously
- Average patch cycle: 15-30 minutes per instance
- Time to complete: 200/20 * 20 min = ~200 min = ~3.3 hours
- Window duration must be > 3.3 hours. With a 4-hour window and
  1-hour cutoff, the effective patching time is 3 hours — TIGHT.

**Error-budget math:**

For a fleet of 200 instances with `MaxErrors: 5%`:
- 10 errors before the window is cancelled
- If the error rate exceeds 5%, the window stops, protecting remaining
  instances from a systematic failure (bad patch, network issue)

**Recommended patterns:**

| Fleet size | MaxConcurrency | MaxErrors | Duration | Cutoff |
|---|---|---|---|---|
| 1-10 | `1` | `1` | 2h | 30m |
| 10-50 | `3` | `2` | 3h | 1h |
| 50-200 | `10%` | `5%` | 4h | 1h |
| 200-1000 | `5%` | `3%` | 6h | 1h |
| > 1000 | `1%` | `1%` | 8h | 2h |

## Compliance-state query patterns

**Per-instance patch state:**

```bash
aws ssm describe-instance-patch-states \
  --instance-ids i-0abc123def
```

**Fleet-wide summary (via aggregator):**

```bash
aws ssm describe-instance-patch-states-for-patch-group \
  --patch-group "al2023-prod" \
  --operating-systems AMAZON_LINUX_2023
```

**Per-instance patch details (individual patches):**

```bash
aws ssm describe-instance-patches \
  --instance-id i-0abc123def \
  --filters '[{"Key":"State","Values":["Missing"]}]'
```

**Compliance summary via Resource Data Sync (multi-account/region):**

```bash
# Create a Resource Data Sync to aggregate patch compliance to a central S3 bucket
aws ssm create-resource-data-sync \
  --sync-name "patch-compliance-aggregator" \
  --sync-type "SyncToDestination" \
  --sync-source '{
    "SourceType": "SingleAccountMultiRegions",
    "AwsOrganizationsSource": {
      "OrganizationSourceType": "ALL_ORGANIZATION_ACCOUNTS"
    }
  }'
```

## Compliance-state values

| State | Meaning | SSM action |
|---|---|---|
| `INSTALLED` | Patch is installed and matches the baseline | None — compliant |
| `INSTALLED_OTHER` | Patch is installed but was not in the baseline at Scan time | Review — may need baseline update |
| `INSTALLED_REJECTED` | Patch is installed but is in the rejected list | Review — remove from rejected or uninstall |
| `INSTALLED_PENDING_REBOOT` | Patch is installed but a reboot is required (NoReboot mode) | Schedule reboot |
| `MISSING` | Patch is in the baseline but not installed | Run Install |
| `NOT_APPLICABLE` | Patch does not apply to this instance (wrong arch, wrong product) | None — expected for heterogeneous fleets |
| `FAILED` | Patch installation attempted and failed | Check SSM command output for error details |

## Integration with AWS Config

Enable the managed Config rule to track patch compliance historically:

```bash
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "ec2-managedinstance-patch-compliance",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "EC2_MANAGEDINSTANCE_PATCH_COMPLIANCE"
    },
    "Scope": {
      "TagKey": "Patch Group",
      "TagValue": "al2023-prod"
    }
  }'
```

This rule emits `COMPLIANT` or `NON_COMPLIANT` per instance on each
evaluation cycle. Combined with Config's timeline, this gives the
full audit trail: when an instance went NonCompliant, when it was
patched, and when it returned to Compliant.

## CloudWatch metrics for patch compliance

| Metric namespace | Metric | Dimensions | Use |
|---|---|---|---|
| `AWS/SSM` | `PatchCompliancePatchingGroup` | `PatchGroup`, `ComplianceType` | Count of Compliant vs NonCompliant instances per patch group |
| `AWS/SSM` | `CommandInternalError` | `DocumentName` | Errors during AWS-RunPatchBaseline execution |
| `AWS/SSM` | `CommandInvocationCount` | `DocumentName` | Total invocations of the patch document |

**Alarm: patch compliance drop**

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "patch-compliance-drop-al2023-prod" \
  --metric-name "PatchCompliancePatchingGroup" \
  --namespace "AWS/SSM" \
  --dimensions Name=PatchGroup,Value=al2023-prod Name=ComplianceType,Value=NON_COMPLIANT \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions "arn:aws:sns:us-east-1:111111111111:patch-alerts"
```

## Deregistration and cleanup

When removing a patch automation:

1. **Deregister tasks** (`deregister-task-with-maintenance-window`) —
   stops new executions but allows running ones to finish.
2. **Deregister targets** (`deregister-target-from-maintenance-window`) —
   removes the instance selection from the window.
3. **Deregister patch-group association**
   (`deregister-patch-baseline-for-patch-group`) — instances fall back
   to the AWS default baseline.
4. **Delete the baseline** (`delete-patch-baseline`) — only after all
   associations are removed.
5. **Remove `Patch Group` tags** from instances — prevents the AWS
   default baseline from continuing to scan/tag them.

**Order matters.** Deleting a baseline before deregistering patch
groups produces an orphaned association. Instances show a stale
baseline ID in their patch state until the association is cleaned up.

## Appendix C — Maintenance-window cron reference (moved from SKILL.md)

| Schedule | Cron | Notes |
|---|---|---|
| Daily 06:00 UTC | `cron(0 6 * * ? *)` | Standard daily Scan |
| Weekly Sat 02:00 UTC | `cron(0 2 ? * SAT *)` | Standard weekly Install |
| Monthly 1st Sun | `cron(0 2 ? * SUN#1 *)` | Conservative monthly |
| Every 4 hours | `rate(4 hours)` | High-frequency Scan |
