# SSM Patch Baselines Reference

Supplementary reference for the Inspector2 Automation Automator
skill. Use when designing the patch baseline for Inspector-driven
EC2 remediation, mapping severities to approval windows, or
debugging a patch that did not apply.

## Patch baseline anatomy

A patch baseline defines:
1. **Approved patches** — explicit list, by CVE or package name
2. **Approval rules** — filters that auto-approve patches by
   classification (Security, Bugfix), severity (Critical, Important),
   and product (Amazon Linux 2, Ubuntu 20.04, etc.)
3. **Patch groups** — tags (`Patch Group: <value>`) that link
   instances to baselines
4. **Rejected patches** — explicit blocklist

## Creating a baseline aligned to Inspector Critical findings

```bash
aws ssm create-patch-baseline \
  --name "al2-critical-inspector-patches" \
  --operating-system AMAZON_LINUX_2 \
  --patch-groups "critical-inspector-group" \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {
        "PatchFilters": [{
          "Key": "CLASSIFICATION",
          "Values": ["Security"]
        }, {
          "Key": "SEVERITY",
          "Values": ["Critical"]
        }]
      },
      "ApproveAfterDays": 0,
      "ComplianceLevel": "CRITICAL"
    }]
  }'
```

**Parameter meanings:**
- `ApproveAfterDays: 0` — patches auto-approved immediately. Use 7
  for High, 30 for Medium to allow soak time.
- `ComplianceLevel: CRITICAL` — non-compliant instances appear as
  "Critical" in the SSM compliance dashboard.
- `PatchGroups` — instances tagged `Patch Group: critical-inspector-group`
  receive patches from this baseline.

## Severity-to-baseline mapping

| Inspector severity | Baseline name pattern | ApproveAfterDays | ComplianceLevel |
|---|---|---|---|
| Critical | `*-critical-patches` | 0 | CRITICAL |
| High | `*-high-patches` | 7 | HIGH |
| Medium | `*-medium-patches` | 30 | MEDIUM |
| Low | `*-low-patches` | 90 | LOW |

**Decision rule:** always run Critical in non-prod for 1 cycle
before production. High/Medium/Low can roll into maintenance windows.

## Registering the baseline as default

```bash
aws ssm register-default-patch-baseline \
  --baseline-id "pb-abc123def456"
```

Or scope to a specific OS:

```bash
aws ssm register-patch-baseline-for-patch-groups \
  --baseline-id "pb-abc123def456" \
  --patch-groups "critical-inspector-group"
```

**Default gotcha:** the default baseline is used when an instance is
NOT tagged with a patch group. Tagging instances explicitly is
safer than relying on the default.

## Associating instances to a baseline

```bash
# Tag EC2 instances
aws ec2 create-tags \
  --resources i-0abc123def456 i-0def456ghi789 \
  --tags Key="Patch Group",Value="critical-inspector-group"

# Verify association
aws ssm describe-instance-patch-states \
  --instance-ids i-0abc123def456
```

**Patch group tag key is case-sensitive.** `Patch Group` (with
space) is the convention; `patch-group` (with hyphen) does not
match unless explicitly registered.

## AWS-RunPatchBaseline parameters

| Parameter | Type | Required | Purpose |
|---|---|---|---|
| `Operation` | String | Yes | `Scan` (read-only) or `Install` (patches) |
| `SnapshotId` | String | Yes | Empty string for default; explicit ID otherwise |
| `InstanceId` | String | Yes (single) | Target instance |
| `InstanceIds` | StringList | Yes (custom runbook) | Multiple instances |
| `RebootOption` | String | No (default `RebootIfNeeded`) | `NoReboot` for canary patches |

## SSM Automation runbook with snapshot + patch

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Snapshot then patch instance flagged by Inspector'
parameters:
  InstanceId:
    type: String
  AutomationAssumeRole:
    type: String
mainSteps:
  - name: PrePatchSnapshot
    action: aws:createImage
    inputs:
      InstanceId: '{{ InstanceId }}'
      ImageName: 'pre-inspector-patch-{{ global:DATE_TIME }}'
      NoReboot: true
    outputs:
      - Name: ImageId
        Selector: '$.ImageId'
        Type: String
  - name: PatchInstall
    action: aws:runCommand
    inputs:
      DocumentName: AWS-RunPatchBaseline
      InstanceIds: ['{{ InstanceId }}']
      Parameters:
        Operation: Install
        RebootOption: RebootIfNeeded
        SnapshotId: ''
    isCritical: true
    onFailure: abort
  - name: VerifyInstalled
    action: aws:waitForAwsResourceProperty
    inputs:
      Service: ssm
      Api: DescribeInstancePatches
      InstanceId: '{{ InstanceId }}'
      PropertySelector: '$.Patches[?(@.State=="Installed")].State'
      DesiredValues: ['Installed']
      Waiter: 'InstancePatchesState'
```

## Common patch failures and fixes

| Failure | Root cause | Fix |
|---|---|---|
| `ACCESS_DENIED` on patch execution | Instance profile missing `AmazonSSMManagedInstanceCore` | Attach the managed profile |
| Instance not in patch compliance dashboard | Instance not tagged with `Patch Group` | Tag with `Key=Patch Group, Value=<group>` |
| Patch baseline applied but CVE persists | Patch baseline missing the affected product/repo | Add source repository via `patch-baseline-operations` |
| Stuck in `InstalledPendingReboot` | `RebootOption: NoReboot` and instance never rebooted | Manually reboot or change to `RebootIfNeeded` |
| Patches approved but never installed | ApproveAfterDays too high; patch not yet approved | Lower `ApproveAfterDays` for Critical baseline |
| Inspector finding stays OPEN post-patch | Inspector rescan not triggered | Trigger rescan via SSM `AWS-RefreshAssociation` or wait for next Inspector cycle |

## Inspector + SSM patch workflow

1. Inspector detects CVE on instance.
2. EventBridge rule matches `severity=CRITICAL, status=OPEN, resourceType=AWS_EC2_INSTANCE`.
3. EventBridge invokes SSM Automation (custom runbook from this
   reference) or Lambda that calls `start-automation-execution`.
4. SSM creates pre-patch AMI snapshot.
5. SSM runs `AWS-RunPatchBaseline` with `Operation=Install`.
6. SSM reboots the instance (`RebootOption=RebootIfNeeded`).
7. Inspector rescans the instance (next cycle or manual trigger).
8. Finding transitions `OPEN → CLOSED`.
9. Security Hub finding closes within 5 minutes.
10. CloudTrail audit trail captures every API call.

## Maintenance window integration

For non-Critical findings, route patches through a maintenance
window instead of event-driven automation:

```bash
aws ssm create-maintenance-window \
  --name "monthly-inspector-patch-window" \
  --schedule "cron(0 2 15 * ? *)" \
  --duration 4 \
  --cutoff 1 \
  --allow-unassociated-targets
```

Add targets (instance IDs or resource groups) and register the
`AWS-RunPatchBaseline` runbook as a task.
