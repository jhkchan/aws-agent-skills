# End-to-end usage scenario: ssm-patch-baseline-deployer

A walkthrough showing the skill creating an Amazon Linux 2023 patch
baseline, registering a patch group, integrating with a maintenance
window, and finally blocking an attempt with a missing instance role.
Each path includes pre-checks, CONFIRM gate, and post-verification.

## Input (user prompt)

> Create a production patch baseline for Amazon Linux 2023 in us-east-1.
> Auto-approve Security and Bugfix patches (Critical/Important) after 7
> days. Register patch group "al2023-prod-web". Then integrate with
> maintenance window mw-0abc123 for weekly Sunday installs.

```json
{
  "Operation": "create",
  "Region": "us-east-1",
  "Account": "111111111111",
  "Baseline": {
    "Name": "al2023-prod-security",
    "OperatingSystem": "AMAZON_LINUX_2023",
    "ApprovalRules": {
      "PatchRules": [{
        "PatchFilterGroup": {
          "OperatingSystem": "AMAZON_LINUX_2023",
          "PatchFilters": [
            {"Key": "PRODUCT", "Values": ["Amazon Linux 2023"]},
            {"Key": "CLASSIFICATION", "Values": ["Security", "Bugfix"]},
            {"Key": "SEVERITY", "Values": ["Critical", "Important"]}
          ]
        },
        "ApproveAfterDays": 7,
        "ComplianceLevel": "CRITICAL",
        "EnableNonSecurity": true
      }]
    }
  },
  "PatchGroup": "al2023-prod-web",
  "MaintenanceWindow": {
    "WindowId": "mw-0abc123",
    "Operation": "Install",
    "MaxConcurrency": "10%",
    "MaxErrors": "3"
  }
}
```

## Skill output — create baseline + register patch group

```text
BASELINE: al2023-prod-security
VERDICT: READY_TO_DEPLOY
TARGET: al2023-prod-security
PRE_CHECKS:
  - [PASS] Baseline name unique
  - [PASS] OS AMAZON_LINUX_2023 is supported
  - [PASS] Product Amazon Linux 2023 matches OS
  - [PASS] Classifications Security, Bugfix valid for AL2023
  - [PASS] Severity Critical, Important valid
  - [PASS] ApproveAfterDays 7 (range 0-100)
  - [PASS] ComplianceLevel CRITICAL (non-UNSPECIFIED)
  - [PASS] Patch Group tag key is "Patch Group"
  - [PASS] Instance role includes AmazonSSMManagedInstanceCore
  - [PASS] IAM principal holds ssm:CreatePatchBaseline
STEPS:
  1. CONFIRM: About to create-patch-baseline al2023-prod-security in
     account 111111111111 region us-east-1. This will CREATE a baseline
     for AMAZON_LINUX_2023 with 7-day auto-approve. Proceed? (yes/no)
  2. aws ssm create-patch-baseline --name al2023-prod-security
     --operating-system AMAZON_LINUX_2023 --approval-rules '{...}'
  3. aws ssm register-patch-baseline-for-patch-group
     --baseline-id <returned-id> --patch-group al2023-prod-web
POST_VERIFY:
  - (pending execution)
  - describe-patch-baseline returns OS=AMAZON_LINUX_2023, ApproveAfterDays=7
  - describe-patch-groups returns al2023-prod-web registered
OPERATING_SYSTEM: AMAZON_LINUX_2023
APPROVAL_RULES: 1 rule (Security, Bugfix; auto-approve: 7 days)
COMPLIANCE_LEVEL: CRITICAL
PATCH_GROUPS: 1 (al2023-prod-web)
MAINTENANCE_WINDOW: NONE (register separately)
INSTANCE_ROLE: AmazonSSMManagedInstanceCore
NOTES:
  - ApproveAfterDays 7 gives 7-day soak time before auto-approval.
  - EnableNonSecurity true also approves non-security updates.
```

## Skill output — maintenance window task registration

```text
BASELINE: al2023-prod-security
VERDICT: READY_TO_DEPLOY
TARGET: al2023-prod-security (maintenance window: mw-0abc123)
PRE_CHECKS:
  - [PASS] Maintenance window mw-0abc123 exists
  - [PASS] Task document AWS-RunPatchBaseline is valid
  - [PASS] Operation Install is valid
  - [PASS] MaxConcurrency 10% and MaxErrors 3 are set
  - [PASS] Service role arn:aws:iam::111111111111:role/MaintenanceWindowRole exists
  - [PASS] CloudWatchOutputConfig enabled
STEPS:
  1. CONFIRM: About to register-task-with-maintenance-window on mw-0abc123.
     This will INSTALL approved patches on al2023-prod-web targets every
     Sunday at 2 AM. Proceed? (yes/no)
  2. aws ssm register-target-with-maintenance-window --window-id mw-0abc123
     --resource-type INSTANCE
     --targets '[{"Key":"tag:Patch Group","Values":["al2023-prod-web"]}]'
     --name al2023-web-targets
  3. aws ssm register-task-with-maintenance-window --window-id mw-0abc123
     --targets '[{"Key":"WindowTargetIds","Values":["<target-id>"]}]'
     --task-arn AWS-RunPatchBaseline --task-type RUN_COMMAND
     --task-parameters '{"Operation":["Install"]}'
     --max-concurrency "10%" --max-errors "3"
POST_VERIFY:
  - (pending execution)
  - describe-maintenance-window-tasks returns AWS-RunPatchBaseline task
OPERATING_SYSTEM: AMAZON_LINUX_2023
APPROVAL_RULES: 1 rule (7-day auto-approve)
COMPLIANCE_LEVEL: CRITICAL
PATCH_GROUPS: 1 (al2023-prod-web)
MAINTENANCE_WINDOW: mw-0abc123 (Sunday 2 AM, Install, 10%/3)
INSTANCE_ROLE: AmazonSSMManagedInstanceCore
NOTES:
  - MaxConcurrency 10% means 10% of targets patch at once.
  - MaxErrors 3 stops the task after 3 failures.
```

## Skill output — missing instance role (blocked)

```text
BASELINE: win-prod-critical
VERDICT: PREREQUISITES_MISSING
TARGET: win-prod-critical
PRE_CHECKS:
  - [PASS] Baseline name unique
  - [PASS] OS WINDOWS_SERVER is supported
  - [PASS] Product WindowsServer2022 matches OS
  - [FAIL] Instance profile for targets in patch group win-prod-servers
    does not include AmazonSSMManagedInstanceCore. SSM agent cannot
    register; instances will be invisible to Patch Manager.
STEPS: (none — pre-checks failed; attach the instance role)
POST_VERIFY: (none)
OPERATING_SYSTEM: WINDOWS_SERVER
APPROVAL_RULES: 1 rule (Critical Updates; auto-approve: 0 days)
COMPLIANCE_LEVEL: CRITICAL
PATCH_GROUPS: 1 (win-prod-servers)
MAINTENANCE_WINDOW: NONE
INSTANCE_ROLE: MISSING
NOTES:
  - Root cause: EC2 instance profile missing AmazonSSMManagedInstanceCore.
  - Remediation: create or attach an instance profile with
    AmazonSSMManagedInstanceCore to all instances tagged with
    Patch Group = win-prod-servers.
  - Command: aws iam attach-role-policy --role-name <role>
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonSSMManagedInstanceCore
```

## What the skill caught that a generic assistant misses

1. **Product-OS matching.** A generic assistant uses `Amazon Linux 2` for
   an AL2023 baseline — zero patches match. The skill verifies product
   alignment at the pre-check gate.

2. **Patch Group tag key casing.** A generic assistant writes
   `patch-group` or `PatchGroup`. The skill enforces the exact
   case-sensitive `Patch Group` tag key.

3. **Instance role verification.** A generic assistant creates the
   baseline and assumes instances will report. The skill verifies
   `AmazonSSMManagedInstanceCore` is attached to target instances.

4. **Maintenance window document check.** A generic assistant uses
   `AWS-RunShellScript` for patching. The skill blocks it — only
   `AWS-RunPatchBaseline` updates the compliance dashboard.

5. **ComplianceLevel non-UNSPECIFIED.** A generic assistant omits it.
   The skill defaults to CRITICAL for production baselines.

6. **MaxConcurrency/MaxErrors.** A generic assistant omits them. The
   skill requires explicit values for production maintenance window tasks.

7. **CONFIRM gate.** A generic assistant auto-executes. The skill emits
   `CONFIRM:` and waits — patching can trigger reboots across a fleet.

## Slash-command invocation

```
/aws:deploy-ssm-patch-baseline
```

Or via the orchestrator:

```
/aws:pipeline
You: "create a patch baseline for Amazon Linux 2023"
```

The orchestrator emits
`[Phase: Deploy | Skills routed: ssm-patch-baseline-deployer]` and hands
off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "create an ssm patch baseline"
# [Phase: Deploy | Skills routed: ssm-patch-baseline-deployer]
```

## Live-account follow-up (optional, requires AWS CLI)

After the baseline is created:

```bash
aws ssm describe-patch-baseline \
  --baseline-id pb-0abc123 \
  --profile default \
  --query 'ApprovalRules.PatchRules[0].[ApproveAfterDays,ComplianceLevel]'

aws ssm describe-patch-groups \
  --operating-system AMAZON_LINUX_2023 \
  --profile default

aws ssm describe-instance-patch-states \
  --instance-ids i-0abc123 \
  --profile default \
  --query 'InstancePatchStates[].[InstalledCount,MissingCount,FailedCount]'
```
