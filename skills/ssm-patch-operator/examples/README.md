# End-to-end usage scenario: ssm-patch-operator

A walkthrough showing the skill planning an Install operation on a single
prod Amazon Linux 2 web server during a Saturday maintenance window. The
pre-checks pass on coverage, IAM role, disk space, and baseline scope
(custom `prod-linux-critical` via `Patch Group` tag, 14 Security/Critical+
Important patches approved after 3 days). The skill produces a READY plan
with the exact `send-command` sequence, the CONFIRM gate, the pre-patch
snapshot, and the deferred-reboot caveat — and contrasted with the BLOCKED
case where the instance has no `Patch Group` tag and silently falls back
to the AWS default baseline.

## Input (user prompt)

> Time to install the prod-linux-critical Security patches on
> i-0abc123def456789a. The maintenance window mw-0aaa is open now (95 min
> remaining). Use NoReboot — kernel patches activate on the next
> scheduled reboot.

```json
{
  "Operation": "install",
  "Target": "i-0abc123def456789a",
  "RebootOption": "NoReboot",
  "Instance": {
    "InstanceId": "i-0abc123def456789a",
    "PingStatus": "Active",
    "LastPingDateTime": "2026-08-07T02:30:00Z",
    "PlatformType": "Linux",
    "PlatformName": "Amazon Linux",
    "PlatformVersion": "2.0.20240620.0",
    "IamRoleARN": "arn:aws:iam::111111111111:role/AmazonSSMManagedInstanceCore-Role"
  },
  "EC2": {
    "State": "running",
    "RootVolumeId": "vol-0root123",
    "RootVolumeFreeGB": 18,
    "Tags": {"Patch Group": "prod-linux-critical", "env": "prod"}
  },
  "EffectiveBaseline": {
    "BaselineId": "pb-0aaa1234",
    "Name": "prod-linux-critical",
    "OperatingSystem": "AMAZON_LINUX_2",
    "ApprovalRules": {
      "PatchRules": [
        {
          "PatchFilterGroup": [
            {"Key": "CLASSIFICATION", "Values": ["Security"]},
            {"Key": "SEVERITY", "Values": ["Critical", "Important"]}
          ],
          "ApproveAfterDays": 3,
          "ComplianceLevel": "CRITICAL"
        }
      ]
    },
    "QualifyingPatchCount": 14
  },
  "MaintenanceWindow": {"WindowId": "mw-0aaa", "MinutesRemaining": 95}
}
```

## Skill output

```text
OPERATION: install
VERDICT: READY
TARGET: i-0abc123def456789a
PRE_CHECKS:
  - [PASS] PingStatus Active; LastPingDateTime 2 min ago
  - [PASS] IAM role AmazonSSMManagedInstanceCore-Role includes
    AmazonSSMManagedInstanceCore
  - [PASS] EC2 State running
  - [PASS] Free disk on / is 18 GB (>= 2 GB threshold)
  - [PASS] Effective baseline pb-0aaa1234 (custom prod-linux-critical)
    resolved via Patch Group tag "prod-linux-critical"
  - [PASS] Baseline ApprovalRules reviewed:
    Classification=Security AND Severity=[Critical, Important],
    ApproveAfterDays=3, ComplianceLevel=CRITICAL
    14 patches qualify under the rule
  - [PASS] No concurrent command in flight
  - [PASS] Maintenance window mw-0aaa open, 95 min remaining
    (>= 60 min buffer for an 8-patch Install)
STEPS:
  1. CONFIRM: About to send-command AWS-RunPatchBaseline
     Operation=Install on i-0abc123def456789a in account 111111111111
     region us-east-1. This will install up to 14 Security patches
     (Critical+Important) approved under pb-0aaa1234 and MAY REBOOT the
     host if a kernel update is in scope. Proceed? (yes/no)
  2. aws ec2 create-snapshot --volume-id vol-0root123 \
       --description "pre-patch $(date -u +%FT%TZ)" \
       --tag-specifications "ResourceType=snapshot,Tags=[{Key=purpose,Value=pre-patch},{Key=instance,Value=i-0abc123def456789a}]"
  3. aws ssm send-command \
       --instance-ids i-0abc123def456789a \
       --document-name "AWS-RunPatchBaseline" \
       --parameters '{"Operation":["Install"],"SnapshotIds":[""],"RebootOption":["NoReboot"]}' \
       --comment "Install prod-linux-critical Security patches" \
       --output-s3-bucket-name audit-ssm-output \
       --output-s3-key-prefix "patch-install/$(date -u +%Y/%m/%d)/i-0abc123def456789a"
  4. aws ssm get-command-invocation \
       --command-id <CommandId from step 3> \
       --instance-id i-0abc123def456789a
     (poll every 30 s until Status is Success / Failed / TimedOut)
POST_VERIFY:
  - (pending execution)
  - aws ssm describe-patch-states --instance-ids i-0abc123def456789a
    → verify OperationEndTime is fresh and InstalledPendingCount is 0
    (or surface the pending-reboot count)
  - aws ssm list-compliance-items --resource-ids i-0abc123def456789a \
      --resource-types ManagedInstance --filters "Key=Status,Values=NON_COMPLIANT"
    → expect COMPLIANT for non-kernel patches; INSTALLED_PENDING for
      kernel patches (NoReboot=true)
  - aws ssm describe-instance-information \
      --instance-information-filter-list Key=InstanceIds,ValueSet=i-0abc123def456789a
    → verify PingStatus still Active (no surprise reboot)
COMPLIANCE_DELTA: before: 14 missing (12 Critical + 2 Important) / after: pending
REBOOT: deferred (NoReboot=true; kernel patches will activate on the next
  maintenance-window reboot. The host runs the stale kernel until then.)
NOTES:
  - The host will only report fully COMPLIANT after the next reboot
    activates any kernel patches. Plan a reboot via mw-0aaa next Saturday
    or via ASG instance refresh within the next 7 days.
  - Re-scan in 24 h to catch patches reverted by package-manager hooks
    (yum versionlock, dnf plugins, etc.).
  - Pre-patch snapshot retained for 7 days; delete after the verification
    window closes.
  - Single-instance target — no --max-concurrency needed. For fleet
    Installs, add `--max-errors 0 --max-concurrency "10%"` to the
    send-command.
```

## Contrast — BLOCKED case (no Patch Group tag)

If the operator had targeted `i-0fedcba9876543210` which has no `Patch
Group` tag, the pre-check gate would fire and no CLI would execute:

```text
OPERATION: install
VERDICT: BLOCKED
TARGET: i-0fedcba9876543210
PRE_CHECKS:
  - [PASS] PingStatus Active
  - [PASS] IAM role includes AmazonSSMManagedInstanceCore
  - [PASS] EC2 State running
  - [PASS] Free disk 22 GB on /
  - [FAIL] Effective baseline is AWS-AmazonLinux2DefaultPatchBaseline
    (AWS-owned default). Operator intent was "apply prod-linux-critical
    baseline rules" — the instance is silently on the default. Install
    would apply the default-baseline approved set, NOT the operator's
    prod-linux-critical rules.
  - [PASS] Maintenance window mw-0bbb has the instance as a target
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
COMPLIANCE_DELTA: (none)
REBOOT: (none)
NOTES:
  - Link the instance to prod-linux-critical via the Patch Group tag
    (key MUST be exactly "Patch Group" — space, capital G):
      aws ec2 create-tags --resources i-0fedcba9876543210 \
        --tags Key="Patch Group",Value=prod-linux-critical
    Then re-fetch: aws ssm get-patch-baseline-for-instance \
      --instance-id i-0fedcba9876543210
    Confirm BaselineId is pb-0aaa1234 before retrying.
  - OR set pb-0aaa1234 as the regional default for AMAZON_LINUX_2:
      aws ssm set-default-patch-baseline \
        --baseline-id pb-0aaa1234 --operating-system AMAZON_LINUX_2
    (replaces AWS-AmazonLinux2DefaultPatchBaseline region-wide — review
    blast radius before applying; every AL2 instance without a Patch
    Group tag switches baselines immediately.)
  - Re-run this skill after remediation; pre-checks will re-evaluate.
```

## What the skill caught that a generic assistant misses

1. **`Operation=Install` vs `Operation=Scan`.** A generic assistant emits
   `send-command` and may omit `Operation`, defaulting to Scan (which
   does not patch). The skill always sets `Operation` explicitly and
   surfaces the default-scan trap as a pre-check finding.

2. **Pre-patch snapshot for rollback.** A generic assistant omits the
   `create-snapshot` step. Patch Manager does NOT auto-snapshot. The
   skill captures a tagged pre-patch snapshot before any Install so a
   bad patch can be rolled back at the volume level.

3. **`NoReboot=true` deferred-reboot caveat.** A generic assistant says
   "patches will take effect after a reboot" in passing. The skill
   enumerates exactly which patches are `InstalledPending`, when the
   next reboot is scheduled, and the 7-day stale-kernel window.

4. **Baseline `ApprovalRules` review.** A generic assistant runs the
   Install. The skill dumps the effective baseline first
   (`get-patch-baseline-for-instance`), surfaces the approval scope
   (Classification=Security AND Severity=[Critical, Important],
   ApproveAfterDays=3 → 14 patches), and gives the operator a chance to
   catch an overly broad baseline before fleet execution.

5. **`Patch Group` tag-key case-sensitivity.** A generic assistant
   accepts the tag without checking. The skill verifies the exact key
   `"Patch Group"` (space, capital G) and the value-equals-baseline-Name
   rule, blocking on mismatch instead of running against the wrong
   baseline.

6. **Rate-control for fleet operations.** A generic assistant omits
   `--max-concurrency` and `--max-errors`. The skill surfaces them for
   any multi-instance Install and hardcodes them on every maintenance-
   window task.

7. **CONFIRM gate.** A generic assistant auto-executes. The skill emits
   `CONFIRM:` and waits — Install may reboot the host and restart
   services, the operator must explicitly approve.

8. **Post-verification re-scan.** A generic assistant stops at
   `Status: Success`. The skill surfaces the eventual-consistency lag
   on `describe-patch-states` and `list-compliance-items` and plans a
   24 h re-scan to catch reverted patches.

## Slash-command invocation

```
/aws:operate-ssm-patch
```

Or via the orchestrator:

```
/aws:pipeline
You: "install the prod-linux-critical Security patches on i-0abc123def456789a"
```

The orchestrator emits
`[Phase: Operate | Skills routed: ssm-patch-operator]` and hands off to
this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "install Security patches on i-0abc123def456789a"
# [Phase: Operate | Skills routed: ssm-patch-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the Install completes:

```bash
# Verify the command succeeded
aws ssm get-command-invocation \
  --command-id <CommandId> \
  --instance-id i-0abc123def456789a \
  --profile default \
  --query 'Status'

# Re-fetch patch state (allow ~30 s – 2 min for eventual consistency)
aws ssm describe-patch-states \
  --instance-ids i-0abc123def456789a \
  --profile default

# Surface any remaining NON_COMPLIANT items by severity
aws ssm list-compliance-items \
  --resource-ids i-0abc123def456789a \
  --resource-types ManagedInstance \
  --filters "Key=Status,Values=NON_COMPLIANT" \
  --profile default \
  --output table

# Confirm the host did NOT reboot unexpectedly
aws ssm describe-instance-information \
  --instance-information-filter-list Key=InstanceIds,ValueSet=i-0abc123def456789a \
  --profile default \
  --query 'InstanceInformationList[0].[PingStatus,LastPingDateTime]'

# Plan the kernel-patch reboot at the next maintenance window
aws ssm start-automation-execution \
  --document-name "AWS-RestartEC2Instance" \
  --document-version "$DEFAULT" \
  --parameters "InstanceId=[i-0abc123def456789a]" \
  --profile default
```
