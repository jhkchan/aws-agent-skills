---
name: ssm-patch-compliance-automator
description: >-
  Designs and implements SSM Patch Manager automation workflows for EC2
  fleets. Creates OS-specific patch baselines (Amazon Linux 2/2023, Ubuntu,
  Windows Server), configures patch groups via tag-based targeting
  (Patch Group key), sets up maintenance windows with cron schedules and
  per-instance concurrency, wires Scan vs Install operations, integrates
  Patch Manager with Inventory for compliance reporting, builds
  EventBridge-driven auto-remediation on NonCompliant state transitions,
  manages snapshots before patching (AWS-UpdateEC2Config), controls
  reboot behavior (RebootOption: RebootIfNeeded vs NoReboot), and rolls
  out multi-account patching via Organizations + CloudFormation StackSets.
  Covers compliance reporting (Compliant, NonCompliant, NotApplicable),
  exception lists for critical instances, and SNS notification/approval
  for patch rollouts. Emits AUTOMATION_DEPLOYED with a ready-to-apply
  baseline+maintenance-window+compliance-monitoring template or
  REVIEW_REQUIRED with the specific gap. Use when automating patch
  compliance, building maintenance windows, or hardening an existing
  patch rollout.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline workflow design. Live deployment
  uses aws ssm create-patch-baseline, register-patch-baseline-for-patch-group,
  create-maintenance-window, register-task-with-maintenance-window,
  describe-instance-patch-states, describe-patch-baseline,
  send-command (AWS-RunPatchBaseline), aws cloudformation create-stack-set
  (multi-account), and aws events put-rule/put-targets (EventBridge
  auto-remediation) — AWS CLI v2, SSO or key-based credentials.
keywords:
  - SSM Patch Manager
  - patch baseline
  - patch group
  - maintenance window
  - patch compliance
  - AWS-RunPatchBaseline
  - patch compliance scanning
  - auto-remediation
  - EventBridge
  - CloudFormation StackSets
  - AWS Organizations
  - Amazon Linux 2
  - Amazon Linux 2023
  - Ubuntu
  - Windows Server
  - RebootOption
  - patch snapshot
  - compliance reporting
  - NonCompliant
  - patch exception list
tags: [ssm, patch-manager, maintenance-window, compliance, multi-account, eventbridge, automate]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "AUTOMATION_DEPLOYED | REVIEW_REQUIRED"
  when_to_use: >-
    Automating OS patching for EC2 fleets, creating patch baselines for
    Amazon Linux 2/2023/Ubuntu/Windows, configuring maintenance windows
    with per-instance concurrency, building EventBridge auto-remediation
    for NonCompliant patch states, rolling out multi-account patching via
    StackSets, or hardening an existing patch workflow with snapshots,
    approval gates, and compliance reporting.
  activation_triggers:
    - "automate patch compliance"
    - "create patch baseline"
    - "maintenance window patching"
    - "AWS-RunPatchBaseline"
    - "patch group tag"
    - "SSM Patch Manager setup"
    - "multi-account patching"
    - "NonCompliant patch auto-remediation"
    - "patch compliance reporting"
    - "RebootOption NoReboot"
  invocation_schema: >-
    Input: either (a) a fleet description (OS mix, instance count,
    environment, patch cadence) plus compliance requirements, OR (b) a
    patch automation request ("patch all Amazon Linux 2023 instances every
    Saturday", "scan for missing Windows updates daily"). Output:
    deterministic PATCH block — BASELINE/PATCH_GROUP/MAINTENANCE_WINDOW/
    COMPLIANCE_MONITORING/SAFETY/VERDICT — where VERDICT is
    AUTOMATION_DEPLOYED (templates ready) or REVIEW_REQUIRED (specific gap
    cited).
---

# SSM Patch Compliance Automator

## Mindset

**One-line takeaway:** every patch-compliance automation is a five-stage
pipeline — **baseline** (what patches to approve) → **target** (which
instances via Patch Group tag) → **schedule** (maintenance window with
cron + concurrency) → **action** (Scan vs Install) → **verify** (patch
state compliance reporting). A gap in ANY stage produces a silent
failure: instances scan but never install, or install without a
snapshot, or patch the wrong instances because the tag is missing.

- **A patch baseline** without a **patch group** association is dead
  configuration: SSM has rules but no targets. The default baseline is
  applied to all SSM-managed instances, but custom baselines require
  explicit tag-based targeting.
- **Scan vs Install** is the most dangerous confusion. `Operation: Scan`
  reports compliance without changing anything. `Operation: Install`
  applies patches and may reboot. A maintenance window running Install
  without a pre-snapshot and an approval gate is a production risk.
- **Compliance reporting is the closing gate.** A patching workflow
  that runs Install but never verifies the compliance state flip
  (NonCompliant → Compliant) is half-built. `describe-instance-patch-states`
  is the audit trail.

## Quick navigation

| You want to... | Go to |
|---|---|
| Create an OS-specific patch baseline | Step 2 + Appendix A |
| Target instances via Patch Group tag | Step 3 |
| Set up a maintenance window with cron + concurrency | Step 4 |
| Choose Scan vs Install operation | Step 5 |
| Wire EventBridge auto-remediation for NonCompliant | Step 6 |
| Integrate Patch Manager + Inventory | Step 7 |
| Multi-account rollout via StackSets | Step 8 |
| Add snapshot + approval gates before Install | Step 9 |
| Build compliance reporting dashboard | Step 10 |
| Handle critical-instance exceptions | Step 11 |
| Manage reboot behavior (RebootOption) | Step 12 |
| Avoid common patching pitfalls | Anti-Patterns |
| Recent features (Karpenter node patching, Quick Setup) | Recent AWS features |

## Critical rules at a glance (do NOT bury these)

1. **Patch Group targeting is tag-based, NOT resource-group-based.**
   The tag key MUST be exactly `Patch Group` (with a space, case-sensitive).
   The tag value is the patch group name. A common error is using
   `PatchGroup` (no space) or `patch-group` (hyphenated) — SSM does not
   match these. Verify with
   `aws ssm describe-instance-patch-states` after tagging.

2. **Maintenance-window concurrency is per-instance, not per-window.**
   `MaxConcurrency` (e.g., `"1"`, `"10%"`, `"10"`) controls how many
   instances within the window patch simultaneously. A window with
   `MaxConcurrency: 1` and 500 targeted instances runs sequentially —
   it will not finish within the window duration. Set concurrency
   based on blast-radius tolerance, not convenience.

3. **Always snapshot EC2 before an Install operation.** Patches can
   break boot (kernel update, glibc update, Windows cumulative update).
   Without a pre-patch AMI snapshot, rollback requires manual EBS
   recovery. Use `AWS-CreateManagedLinuxInstanceWithApproval` or a
   pre-step `aws:createImage` in the maintenance-window task document.

4. **`AWS-RunPatchBaseline` with `Operation: Install` may reboot.**
   The `RebootOption` parameter controls this: `RebootIfNeeded` (default)
   reboots after patching if required by the OS. `NoReboot` suppresses
   reboot — patches are staged but not activated until the next reboot.
   NoReboot produces a false sense of compliance: Scan reports
   "installed" but the running kernel is unpatched until reboot.

5. **The default patch baseline is NOT the AWS-managed baseline.**
   Each OS has an AWS-managed default that SSM applies to any instance
   without a custom baseline. Registering a custom baseline for a patch
   group overrides the default. If you remove the custom baseline
   association, instances fall back to the AWS default — which may
   have a different approval threshold.

## Pre-flight: data requirements

Designing a patch-compliance workflow requires these inputs:

| Input | Source | Why |
|---|---|---|
| OS mix of the fleet | `aws ec2 describe-instances` + SSM Inventory | Drives baseline OS selection |
| Instance count per OS | Same | Drives maintenance-window sizing |
| SSM agent health | `aws ssm describe-instance-information` | Instances with unhealthy agents are invisible to Patch Manager |
| Existing patch baselines | `aws ssm describe-patch-baselines` | Don't overwrite blindly |
| Existing patch groups | `aws ssm describe-patch-groups` | Don't re-register blindly |
| Existing maintenance windows | `aws ssm describe-maintenance-windows` | Avoid schedule conflicts |
| Current compliance state | `aws ssm describe-instance-patch-states` | Baseline before automation |
| Critical-instance list | Application team input | Exception list (see Step 11) |

**If the input is malformed** (missing OS mix, zero SSM-managed
instances), emit:

```text
PATCH: <reference>
VERDICT: ERROR
REASON: Cannot design patch automation — OS mix and SSM-managed instance count are required.
GAP: Run aws ssm describe-instance-information --query 'InstanceInformationList[!null(PingStatus)]' and supply the OS breakdown.
```

## Process — Patch automation design (apply in order)

### Step 0: Expert knowledge — non-obvious Patch Manager behaviors

These behaviors change the workflow design if ignored:

- **`Patch Group` tag is case-SENSITIVE and space-sensitive.** The key
  must be exactly `Patch Group` (capital P, capital G, one space). SSM
  does not fuzzy-match. Tag drift (e.g., Terraform applying
  `PatchGroup`) silently removes instances from the patch group. Audit
  tags regularly via
  `aws ec2 describe-tags --filters "Name=key,Values=Patch Group"`.

- **Maintenance-window `MaxErrors` gates the window, not the task.**
  If `MaxErrors: 1` and one instance fails, the ENTIRE window is
  cancelled for remaining instances — including ones that have not
  started. For large fleets, set `MaxErrors` to a percentage (e.g.,
  `"5%"`) to avoid a single failure blocking all patching.

- **`AWS-RunPatchBaseline` Install with `NoReboot` does NOT defer
  all patches.** Some packages (kernel, glibc on Linux; certain
  cumulative updates on Windows) require a reboot to take effect. With
  `NoReboot`, the package is installed but the old version remains
  active. Scan reports it as installed; security scanners report the
  running version as vulnerable. This is the most dangerous
  false-positive in patch compliance.

- **The patch baseline `ApprovalRules` are time-based, not event-based.**
  `ApproveAfterDays: 7` means patches are approved 7 days after
  release by the OS vendor (Microsoft Patch Tuesday, Ubuntu security
  notices). There is no CI/CD trigger. For zero-day response, create
  a separate emergency baseline with `ApproveAfterDays: 0`.

- **Scan-only maintenance windows do NOT consume the Install quota.**
  You can run Scan daily and Install weekly. The compliance state from
  Scan is what Config (if integrated) reports. A daily Scan +
  weekly Install is the recommended pattern for most fleets.

- **`register-patch-baseline-for-patch-group` is idempotent on the
  patch-group name, NOT the baseline.** Re-registering a patch group
  with a different baseline silently switches the group to the new
  baseline. There is no warning. Always `describe-patch-groups` before
  re-registering.

- **CloudFormation StackSets for patch baselines deploy the baseline
  resource but NOT the patch-group association.** StackSets create
  resources in member accounts; patch-group associations are per-account
  API calls that must be scripted separately (Lambda-backed custom
  resource or a separate SSM State Manager association).

- **SSM Inventory `AWS:PatchCompliance` schema is read-only.** It
  reflects the last Scan result. There is no "trigger Install from
  Inventory" path. Inventory is observability, Patch Manager is the
  action layer.

- **Windows Server patching via Patch Manager uses WSUS or Windows
  Update as the source.** If instances are in a private VPC without
  a NAT gateway or WSUS server, patches fail to download. The
  `OperatingSystem: WINDOWS` baseline is useless without network
  egress to Windows Update endpoints. Verify VPC endpoints or NAT
  before deploying a Windows patch baseline.

- **Amazon Linux 2023 uses DNF, not YUM.** SSM Patch Manager handles
  this transparently, but custom pre/post scripts that call `yum`
  will fail on AL2023. Always use `dnf` or rely on SSM's built-in
  package management.

### Step 1: Classify the fleet

For each fleet segment, classify by OS and environment:

| OS family | Baseline operating system value | Default source repo | Notes |
|---|---|---|---|
| Amazon Linux 2 | `AMAZON_LINUX_2` | Amazon Linux 2 repos | EOL 2025-06; plan migration to AL2023 |
| Amazon Linux 2023 | `AMAZON_LINUX_2023` | AL2023 repos (DNF) | Use `dnf` in custom scripts |
| Ubuntu 20.04 LTS | `UBUNTU_20_04` | Ubuntu archive | EOL 2025-04; consider 22.04/24.04 |
| Ubuntu 22.04 LTS | `UBUNTU_22_04` | Ubuntu archive | Current LTS |
| Ubuntu 24.04 LTS | `UBUNTU_24_04` | Ubuntu archive | Latest LTS |
| Windows Server 2019 | `WINDOWS` | Windows Update / WSUS | Requires NAT or WSUS in private VPC |
| Windows Server 2022 | `WINDOWS` | Windows Update / WSUS | Same network requirement |
| RHEL 8/9 | `REDHAT_ENTERPRISE_LINUX` | Red Hat Update Infrastructure | RHUI entitlements required |
| CentOS 7 | `CENTOS` | CentOS vault (EOL) | EOL 2024-06; migrate to RHEL/AL |

If the fleet has mixed OS, each OS requires a separate baseline and a
separate patch-group tag value. Do NOT mix OS under one patch group —
the baseline is per patch group, and a WINDOWS baseline applied to a
Linux patch group produces zero patches installed.

### Step 2: Create the OS-specific patch baseline

CLI pattern for an Amazon Linux 2023 baseline with a 7-day approval
window and critical-severity auto-approval:

```bash
aws ssm create-patch-baseline \
  --name "al2023-prod-baseline" \
  --operating-system AMAZON_LINUX_2023 \
  --approval-rules '{
    "PatchRules": [
      {
        "PatchFilterGroup": {
          "Key": "PRODUCT",
          "Values": ["Amazon Linux 2023"]
        },
        "PatchFilterGroup": {
          "Key": "CLASSIFICATION",
          "Values": ["Security", "Bugfix"]
        },
        "PatchFilterGroup": {
          "Key": "SEVERITY",
          "Values": ["Critical", "Important"]
        },
        "ComplianceLevel": "CRITICAL",
        "ApproveAfterDays": 0
      },
      {
        "PatchFilterGroup": {
          "Key": "CLASSIFICATION",
          "Values": ["Security", "Bugfix"]
        },
        "ComplianceLevel": "MEDIUM",
        "ApproveAfterDays": 7
      }
    ]
  }' \
  --tags '[{"Key":"Environment","Value":"prod"}]'
```

For Windows Server (cumulative updates, security-only):

```bash
aws ssm create-patch-baseline \
  --name "win2022-prod-baseline" \
  --operating-system WINDOWS \
  --approval-rules '{
    "PatchRules": [
      {
        "PatchFilterGroup": {
          "Key": "MSRC_SEVERITY",
          "Values": ["Critical", "Important"]
        },
        "PatchFilterGroup": {
          "Key": "CLASSIFICATION",
          "Values": ["Security Updates", "Critical Updates"]
        },
        "ComplianceLevel": "CRITICAL",
        "ApproveAfterDays": 3
      }
    ]
  }'
```

Common errors and fixes:

| Error | Cause | Fix |
|---|---|---|
| `UnsupportedOperatingSystem` | OS value not supported in region | Check regional support; AL2023 not available in all regions at launch |
| `PatchFilter key not recognized` | Wrong filter key for the OS | Windows uses `MSRC_SEVERITY`; Linux uses `SEVERITY` |
| `ApprovalRules malformed` | JSON structure incorrect | PatchRules is an array of rule objects with PatchFilterGroup arrays |

### Step 3: Target instances via Patch Group tag

Tag instances with the exact key `Patch Group`:

```bash
# Tag a single instance
aws ec2 create-tags \
  --resources i-0abc123def \
  --tags "Key=Patch Group,Value=al2023-prod"

# Verify the tag landed (note the exact key with space)
aws ec2 describe-tags \
  --filters "Name=resource-id,Values=i-0abc123def" "Name=key,Values=Patch Group"
```

Register the patch baseline for the patch group:

```bash
aws ssm register-patch-baseline-for-patch-group \
  --baseline-id "$(aws ssm describe-patch-baselines --query 'BaselineIdentities[?BaselineName==`al2023-prod-baseline`].BaselineId' --output text)" \
  --patch-group "al2023-prod"
```

Verify the association:

```bash
aws ssm describe-patch-groups \
  --filters "Name=Name,Values=al2023-prod"
```

**Bulk tagging pattern** for a fleet (tag all AL2023 instances in
a specific environment):

```bash
# Get all AL2023 instances in prod and tag them
for instance_id in $(aws ec2 describe-instances \
  --filters "Name=instance-state-name,Values=running" \
            "Name=tag:OS,Values=Amazon Linux 2023" \
            "Name=tag:Environment,Values=prod" \
  --query 'Reservations[].Instances[].InstanceId' --output text); do
  aws ec2 create-tags --resources "$instance_id" \
    --tags "Key=Patch Group,Value=al2023-prod"
done
```

**The most common failure here:** the tag key `Patch Group` is applied
via Infrastructure-as-Code (Terraform, CloudFormation) but with a
different case or spacing. Always verify with
`describe-instance-patch-states` after tagging — if the instance shows
no baseline association, the tag key is wrong.

### Step 4: Configure the maintenance window

Create the window with a cron schedule, duration, and per-instance
concurrency:

```bash
aws ssm create-maintenance-window \
  --name "al2023-prod-patch-window" \
  --schedule "cron(0 2 ? * SAT *)" \
  --duration 4 \
  --cutoff 1 \
  --allow-unassociated-targets \
  --tags '[{"Key":"Environment","Value":"prod"}]'
```

Schedule semantics:
- `cron(0 2 ? * SAT *)` — every Saturday at 02:00 UTC
- `--duration 4` — window is 4 hours long
- `--cutoff 1` — no new tasks start in the last 1 hour (tasks already
  running continue). This is the safety margin.

Register targets (the patch group):

```bash
aws ssm register-target-with-maintenance-window \
  --window-id "$(aws ssm describe-maintenance-windows --query 'WindowIdentities[?Name==`al2023-prod-patch-window`].WindowId' --output text)" \
  --target-type "RESOURCE_GROUP" \
  --targets "Key=tag:Patch Group,Values=al2023-prod"
```

Register the patch task with concurrency control:

```bash
aws ssm register-task-with-maintenance-window \
  --window-id "<window-id>" \
  --targets "Key=WindowTargetIds,Values=<target-id>" \
  --task-arn "AWS-RunPatchBaseline" \
  --task-type "RUN_COMMAND" \
  --task-invocation-parameters '{
    "RunCommand": {
      "Parameters": {
        "Operation": ["Install"],
        "SnapshotId": ["prod-patch-snapshot"],
        "RebootOption": ["RebootIfNeeded"]
      }
    }
  }' \
  --max-concurrency "10%" \
  --max-errors "5%" \
  --priority 1
```

**Concurrency sizing guide:**

| Fleet size | MaxConcurrency | MaxErrors | Rationale |
|---|---|---|---|
| < 10 instances | `1` | `1` | Patch one at a time; no blast radius |
| 10-50 | `3` | `2` | Small batches; one failure does not block |
| 50-200 | `10%` | `5%` | Percentage-based; scales with fleet |
| 200-1000 | `5%` | `3%` | Conservative; large fleet = large blast radius |
| > 1000 | `1%` | `1%` | Very conservative; use wave deployment |

### Step 5: Choose Scan vs Install operation

| Operation | What it does | Compliance state | When to use |
|---|---|---|---|
| `Scan` | Checks installed packages against baseline; reports missing | Updates `AWS:PatchCompliance` inventory | Daily compliance check; no risk |
| `Install` | Downloads and installs missing/rejected patches; may reboot | Updates compliance + actually patches | Scheduled patch window |

**Recommended pattern:** daily Scan + weekly Install.

Daily Scan maintenance window:

```bash
aws ssm create-maintenance-window \
  --name "al2023-prod-daily-scan" \
  --schedule "cron(0 6 * * ? *)" \
  --duration 2 \
  --cutoff 1
```

Install task in the weekly window uses `Operation: Install`. Scan task
in the daily window uses `Operation: Scan`.

**Never run `Install` in the daily scan window.** A common misconfiguration
is copying the Scan window's task to Install — this patches every day,
causing unexpected reboots and application instability.

### Step 6: Wire EventBridge auto-remediation on NonCompliant

When an instance transitions to `NonCompliant` after a Scan, trigger
auto-remediation via EventBridge + SSM (or Lambda for custom logic).

EventBridge rule for patch-compliance state change:

```bash
aws events put-rule \
  --name "patch-noncompliant-remediation" \
  --event-pattern '{
    "source": ["aws.ssm"],
    "detail-type": ["Patch Compliance State Change"],
    "detail": {
      "compliance-type": ["Patch"],
      "new-compliance-status": ["NON_COMPLIANT"]
    }
  }'
```

Target: an SSM Automation document that runs `AWS-RunPatchBaseline`
with `Operation: Install` on the non-compliant instance.

```bash
aws events put-targets \
  --rule "patch-noncompliant-remediation" \
  --targets '[{
    "Id": "auto-patch-install",
    "Arn": "arn:aws:ssm:us-east-1:111111111111:automation-definition/AWS-RunPatchBaseline",
    "RoleArn": "arn:aws:iam::111111111111:role/service-role/AmazonSSMAutomationRole",
    "InputTransformer": {
      "InputPathsMap": {
        "instance-id": "$.detail.resource-id"
      },
      "InputTemplate": "{\"InstanceId\":[<instance-id>],\"Operation\":[\"Install\"]}"
    }
  }]'
```

**Safety note:** auto-remediation with `Install` may reboot instances.
For production, route through SSM Change Manager or add a delay (e.g.,
SNS topic that pages on-call before triggering Install). Do NOT
enable auto-Install on critical instances without a snapshot gate.

### Step 7: Integrate Patch Manager with Inventory

SSM Inventory `AWS:PatchCompliance` schema is automatically populated
by Scan operations. No additional configuration is needed beyond
enabling Inventory collection.

Verify Inventory is collecting patch data:

```bash
aws ssm get-inventory \
  --type-name "AWS:PatchCompliance" \
  --filters "Key=InstanceId,Values=i-0abc123def"
```

Query fleet-wide patch compliance:

```bash
aws ssm describe-instance-patch-states \
  --instance-ids i-0abc123def i-0ghi456jkl
```

Output fields:
- `Operation` — Scan or Install (last operation)
- `OperationEndTime` — when the last operation completed
- `PatchGroup` — the patch group the instance belongs to
- `BaselineId` — the baseline applied
- `InstalledCount` — patches installed
- `InstalledRejectedCount` — patches installed but later rejected by baseline
- `MissingCount` — patches missing (NonCompliant)
- `FailedCount` — patches that failed to install
- `NotApplicableCount` — patches not applicable to this instance

**Patch Manager + Config integration:** enable the Config managed rule
`patch-compliance-scanner-check` to track compliance state changes
in the Config timeline. This gives a historical audit trail of when
instances went NonCompliant and when they returned to Compliant.

### Step 8: Multi-account rollout via Organizations + StackSets

For fleets spanning multiple accounts, deploy baselines via
CloudFormation StackSets to all member accounts.

StackSet template (patch-baseline.yaml):

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'SSM Patch Baseline for Amazon Linux 2023'
Resources:
  PatchBaseline:
    Type: AWS::SSM::PatchBaseline
    Properties:
      Name: !Sub "${Environment}-al2023-baseline"
      OperatingSystem: AMAZON_LINUX_2023
      ApprovalRules:
        PatchRules:
          - PatchFilterGroup:
              Key: CLASSIFICATION
              Values:
                - Security
                - Bugfix
            PatchFilterGroup:
              Key: SEVERITY
              Values:
                - Critical
                - Important
            ComplianceLevel: CRITICAL
            ApproveAfterDays: 0
          - PatchFilterGroup:
              Key: CLASSIFICATION
              Values:
                - Security
                - Bugfix
            ComplianceLevel: MEDIUM
            ApproveAfterDays: 7
      Tags:
        - Key: Environment
          Value: !Ref Environment
Parameters:
  Environment:
    Type: String
    Default: prod
    AllowedValues: [prod, staging, dev]
Outputs:
  BaselineId:
    Value: !Ref PatchBaseline
```

Deploy via StackSets:

```bash
aws cloudformation create-stack-set \
  --stack-set-name "ssm-patch-baseline-al2023" \
  --template-body file://patch-baseline.yaml \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false \
  --capabilities CAPABILITY_IAM

aws cloudformation create-stack-instances \
  --stack-set-name "ssm-patch-baseline-al2023" \
  --deployment-targets OrganizationalUnitIds=["ou-abc-123defghi"] \
  --regions us-east-1 us-west-2
```

**Important:** StackSets deploys the baseline resource only. Patch-group
associations and instance tagging must be handled separately — either
via SSM State Manager associations (CloudFormation `AWS::SSM::Association`)
or a Lambda-backed custom resource that calls
`register-patch-baseline-for-patch-group` per account.

### Step 9: Safety gates — snapshot, approval, notification

Every Install workflow MUST include safety gates. A patching workflow
without gates is unsafe by construction.

| Gate | How | When to use |
|---|---|---|
| Pre-patch AMI snapshot | `aws:createImage` step in a custom runbook before `AWS-RunPatchBaseline` Install | Every EC2 Install — non-negotiable |
| SNS notification | `--notification-config` on the maintenance-window task | All workflows — non-negotiable |
| Approval gate | SSM Change Manager or `aws:approve` step | Production environments, regulated workloads |
| MaxErrors circuit breaker | `--max-errors "5%"` on the task | All batch-patching workflows |
| Post-patch health check | Custom runbook step that verifies app health endpoint | Production with HTTP health checks |
| Rollback AMI | Pre-patch AMI retained for 7 days; documented rollback procedure | Every destructive patch cycle |

Custom runbook with pre-patch snapshot:

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Patch with pre-snapshot and post-health-check'
parameters:
  InstanceId:
    type: String
  AutomationAssumeRole:
    type: String
mainSteps:
  - name: CreatePrePatchSnapshot
    action: aws:createImage
    inputs:
      InstanceId: '{{ InstanceId }}'
      ImageName: !Sub 'pre-patch-${InstanceId}-{{global:DATE_TIME}}'
      NoReboot: true
    outputs:
      - Name: ImageId
        Selector: '$.ImageId'
        Type: String
  - name: RunPatchInstall
    action: aws:runCommand
    inputs:
      DocumentName: AWS-RunPatchBaseline
      InstanceIds:
        - '{{ InstanceId }}'
      Parameters:
        Operation: Install
        RebootOption: RebootIfNeeded
    isCritical: true
    onFailure: abort
  - name: VerifyHealth
    action: aws:invokeLambdaFunction
    inputs:
      FunctionName: post-patch-health-check
      Payload: '{"InstanceId": "{{ InstanceId }}"}'
```

### Step 10: Build compliance reporting

Fleet-wide compliance summary:

```bash
# Count compliant vs non-compliant instances
aws ssm describe-instance-patch-states \
  --instance-ids $(aws ssm describe-instance-information \
    --query 'InstanceInformationList[?PingStatus==`Online`].InstanceId' \
    --output text | tr '\t' ' ') \
  --query 'InstancePatchStates[].{
    InstanceId: InstanceId,
    PatchGroup: PatchGroup,
    Missing: MissingCount,
    Failed: FailedCount,
    Installed: InstalledCount,
    NotApplicable: NotApplicableCount,
    Operation: Operation,
    LastOperation: OperationEndTime
  }' --output table
```

Compliance categories:

| Category | Definition | Action |
|---|---|---|
| Compliant | `MissingCount: 0` and `FailedCount: 0` | None — fully patched |
| NonCompliant | `MissingCount > 0` | Schedule Install in next maintenance window |
| InstallFailed | `FailedCount > 0` | Investigate per-patch failure; check logs |
| NotApplicable | All patches in baseline are `NotApplicable` | Verify baseline matches the OS / architecture |
| NotScanned | Instance has no patch state | Verify SSM agent health and patch-group tag |

**CloudWatch dashboard** for patch compliance:

```bash
aws cloudwatch put-metric-dashboard \
  --dashboard-name "patch-compliance-overview" \
  --dashboard-body '{
    "widgets": [
      {
        "type": "metric",
        "properties": {
          "metrics": [
            ["AWS/SSM", "PatchCompliancePatchingGroup", "PatchGroup", "al2023-prod", "ComplianceType", "COMPLIANT"],
            [".", ".", ".", ".", ".", "NON_COMPLIANT"]
          ],
          "period": 300,
          "stat": "Sum",
          "region": "us-east-1",
          "title": "Patch Compliance — AL2023 Prod"
        }
      }
    ]
  }'
```

### Step 11: Handle critical-instance exceptions

For instances that must NOT be auto-patched (databases, single-AZ
stateful services, instances in a change-frozen window):

**Option A: Tag exclusion.** Do NOT tag the instance with a `Patch Group`
value. Untagged instances are invisible to Patch Manager (unless
`--allow-unassociated-targets` is set on the window, which is
discouraged for production).

**Option B: Scan-only patch group.** Tag the instance with
`Patch Group=critical-scan-only` and register a baseline with NO
maintenance window for Install. The instance is scanned daily for
compliance reporting but never auto-installed.

**Option C: Approval-required patch group.** Create a maintenance
window with `--max-concurrency 1` and route through SSM Change Manager
with mandatory approval from the application owner.

Maintain an exception register:

```yaml
# exception-register.yaml
exceptions:
  - instance_id: i-0db123prod
    reason: "Primary RDS proxy — change-frozen until Q4 migration"
    patch_group: "critical-scan-only"
    review_date: "2026-10-01"
    approver: "db-team@company.com"
  - instance_id: i-0aux456legacy
    reason: "Legacy app — patching breaks JCE provider"
    patch_group: "critical-scan-only"
    review_date: "2026-09-15"
    approver: "platform@company.com"
```

**Review exceptions quarterly.** An exception that never expires is a
permanent security hole. Set calendar reminders for each exception's
review date.

### Step 12: Manage reboot behavior (RebootOption)

| RebootOption | Behavior | Use case |
|---|---|---|
| `RebootIfNeeded` (default) | SSM reboots the instance after Install if the OS requires it | General-purpose patching; most workloads |
| `NoReboot` | Patches are staged but no reboot occurs; running kernel/processes are unpatched | Controlled-maintenance windows where a separate reboot is scheduled later |

**The `NoReboot` trap:** Scan reports patches as installed (they are on
disk), but the running kernel and processes still use the old versions.
Security scanners that check the running version flag the instance as
vulnerable. This creates a disagreement between SSM compliance (Compliant)
and vulnerability scanners (Vulnerable).

**Resolution:** if using `NoReboot`, schedule a separate reboot window
within 24 hours and verify compliance state after reboot. Never leave
`NoReboot` instances un-rebooted for more than 48 hours.

## Output format

```text
PATCH: <reference>
FLEET: <OS mix + instance count>
BASELINE:
  - Name: <baseline name>
  - OS: <operating system>
  - Approval rules: <summary>
  - Baseline ID: <ARN or ID>
PATCH_GROUP:
  - Tag key: Patch Group
  - Tag value: <patch-group name>
  - Instance count: <N>
MAINTENANCE_WINDOW:
  - Scan schedule: <cron>
  - Install schedule: <cron>
  - Duration: <hours>
  - MaxConcurrency: <value>
  - MaxErrors: <value>
COMPLIANCE_MONITORING:
  - Inventory schema: AWS:PatchCompliance
  - Config rule: patch-compliance-scanner-check (optional)
  - Dashboard: <CloudWatch dashboard name>
SAFETY:
  - Pre-patch snapshot: <enabled/disabled>
  - SNS notification: <topic ARN>
  - Approval gate: <Change Manager / none>
  - Exception list: <count or none>
REBOOT: RebootIfNeeded | NoReboot
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippets for baseline + patch group + maintenance window>
```

### Worked example — AUTOMATION_DEPLOYED, Amazon Linux 2023 fleet

```text
PATCH: al2023-prod-patch-rollout
FLEET: 120 Amazon Linux 2023 instances (prod)
BASELINE:
  - Name: al2023-prod-baseline
  - OS: AMAZON_LINUX_2023
  - Approval rules: Critical/Important approved immediately; Medium approved after 7 days
  - Baseline ID: pb-0abc123def
PATCH_GROUP:
  - Tag key: Patch Group
  - Tag value: al2023-prod
  - Instance count: 120
MAINTENANCE_WINDOW:
  - Scan schedule: cron(0 6 * * ? *) daily 06:00 UTC
  - Install schedule: cron(0 2 ? * SAT *) weekly Saturday 02:00 UTC
  - Duration: 4 hours
  - MaxConcurrency: 10% (12 instances at a time)
  - MaxErrors: 5% (6 errors before window cancels)
COMPLIANCE_MONITORING:
  - Inventory schema: AWS:PatchCompliance (auto-populated by Scan)
  - Config rule: patch-compliance-scanner-check enabled
  - Dashboard: patch-compliance-overview
SAFETY:
  - Pre-patch snapshot: enabled (aws:createImage before Install)
  - SNS notification: arn:aws:sns:us-east-1:111111111111:patch-notify
  - Approval gate: none (reversible via AMI rollback)
  - Exception list: 2 instances (i-0db123prod, i-0aux456legacy)
REBOOT: RebootIfNeeded
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws ssm create-patch-baseline --name "al2023-prod-baseline" --operating-system AMAZON_LINUX_2023 --approval-rules '...'
  aws ec2 create-tags --resources <instance-id> --tags "Key=Patch Group,Value=al2023-prod"
  aws ssm register-patch-baseline-for-patch-group --baseline-id pb-0abc123def --patch-group al2023-prod
  aws ssm create-maintenance-window --name "al2023-prod-patch-window" --schedule "cron(0 2 ? * SAT *)" --duration 4 --cutoff 1
  aws ssm register-task-with-maintenance-window --window-id <id> --task-arn "AWS-RunPatchBaseline" --task-invocation-parameters '{"RunCommand":{"Parameters":{"Operation":["Install"],"RebootOption":["RebootIfNeeded"]}}}' --max-concurrency "10%" --max-errors "5%"
```

### Worked example — REVIEW_REQUIRED, Windows fleet without NAT

```text
PATCH: win2022-prod-patch-rollout
FLEET: 45 Windows Server 2022 instances (prod, private VPC)
BASELINE:
  - Name: win2022-prod-baseline
  - OS: WINDOWS
  - Approval rules: Critical/Important security updates approved after 3 days
  - Baseline ID: pb-0xyz789ghi
PATCH_GROUP:
  - Tag key: Patch Group
  - Tag value: win2022-prod
  - Instance count: 45
MAINTENANCE_WINDOW:
  - Scan schedule: cron(0 6 * * ? *) daily 06:00 UTC
  - Install schedule: cron(0 2 ? * SUN *) weekly Sunday 02:00 UTC
  - Duration: 6 hours
  - MaxConcurrency: 5%
  - MaxErrors: 3%
COMPLIANCE_MONITORING:
  - Inventory schema: AWS:PatchCompliance
  - Config rule: TBD
  - Dashboard: TBD
SAFETY:
  - Pre-patch snapshot: TBD
  - SNS notification: TBD
  - Approval gate: TBD
  - Exception list: TBD
REBOOT: TBD
VERDICT: REVIEW_REQUIRED
GAP: Windows instances are in a private VPC without NAT gateway or WSUS. Patches will fail to download from Windows Update. Resolution options: (1) add a NAT gateway to the private subnet; (2) deploy a WSUS server in the VPC; (3) create VPC endpoints for Windows Update (limited support). Additionally, no pre-patch snapshot workflow is defined, and SNS notification is not configured.
TEMPLATE: (blocked until network egress is resolved)
```

## Anti-Patterns — NEVER do these things

- NEVER use `PatchGroup` (no space) or `patch-group` (hyphenated) as
  the tag key. SSM Patch Manager matches EXACTLY `Patch Group`
  (capital P, capital G, one space). A mistagged instance is invisible
  to Patch Manager and will silently never be patched. Always verify
  with `describe-instance-patch-states` after tagging.

- NEVER run `Operation: Install` in a daily maintenance window without
  an explicit approval gate. Daily Install causes unexpected reboots
  and package churn. Use `Operation: Scan` for daily compliance and
  `Operation: Install` only in the weekly patch window.

- NEVER patch without a pre-patch AMI snapshot. Kernel updates, glibc
  updates, and Windows cumulative updates can break boot. Without a
  snapshot, rollback requires manual EBS recovery. The snapshot is
  your insurance — always include it.

- NEVER set `MaxErrors: 1` on a large-fleet maintenance window. A
  single instance failure cancels the entire window for all remaining
  instances. Use percentage-based `MaxErrors` (e.g., `"5%"`) for
  fleets > 10 instances.

- NEVER set `MaxConcurrency` to the full instance count. If all
  instances patch simultaneously and a bad patch is deployed, the
  entire fleet goes down at once. Cap concurrency at 10-20% of the
  fleet for production workloads.

- NEVER use `NoReboot` without scheduling a follow-up reboot within
  24 hours. `NoReboot` stages patches but does not activate them. The
  running kernel and processes remain vulnerable. Security scanners
  will flag the instance even though SSM reports it as Compliant.

- NEVER assume a CloudFormation StackSet for patch baselines wires
  the patch-group association. StackSets deploy the baseline resource;
  the `register-patch-baseline-for-patch-group` association is a
  separate API call per account. Use a CloudFormation
  `AWS::SSM::Association` or a Lambda-backed custom resource.

- NEVER enable EventBridge auto-remediation with `Operation: Install`
  on production instances without a snapshot gate and an SNS
  notification. A NonCompliant finding triggers immediate Install,
  which may reboot the instance during business hours. Route through
  SSM Change Manager or add a time-window filter.

- NEVER forget to verify SSM agent health before scheduling a patch
  window. Instances with `PingStatus: ConnectionLost` or
  `PingStatus: Stopped` are invisible to Patch Manager. The
  maintenance window reports zero executions for these instances —
  no error, no alert, just silence.

- NEVER create an exception list without a review date. An exception
  that never expires is a permanent security hole. Every critical-
  instance exception must have a calendar-reminder review date and a
  named approver.

- NEVER assume `describe-instance-patch-states` reflects real-time
  compliance. It reflects the LAST Scan or Install operation. If the
  last operation was 23 hours ago, new vulnerabilities released since
  then are not reflected. Run Scan before reporting compliance to
  auditors.

- NEVER mix OS families under one patch group. A WINDOWS baseline
  applied to a Linux patch group produces zero patches. Each OS
  family requires its own baseline, patch-group value, and
  maintenance window.

- NEVER delete a patch baseline that has registered patch groups.
  Instances fall back to the AWS-managed default baseline, which may
  have a different approval threshold. Always deregister patch groups
  first (`deregister-patch-baseline-for-patch-group`), then delete the
  baseline.

- NEVER skip the SNS notification on a maintenance-window task. A
  patch window that fails silently (all instances fail, no one knows)
  is worse than no patching. The SNS notification is the operational
  visibility layer.

- NEVER set `--cutoff 0` on a maintenance window. `cutoff: 0` means
  new tasks can start right up to the window end, leaving no buffer
  for long-running patch operations. Set cutoff to at least 1 hour
  (or 25% of the duration, whichever is larger).

## Pre-flight safety checks (run before applying any patch CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-patch-baseline`, `register-patch-baseline-for-patch-group`,
  `create-maintenance-window`, `register-task-with-maintenance-window`),
  emit:
  `CONFIRM: About to <action> for patch group <group> in account
  <account>. This affects <consequence>. Proceed? (yes/no)`

- **Back up the current patch-baseline associations** before modifying:
  `aws ssm describe-patch-groups > /tmp/patch-groups-backup-$(date +%s).json`
  Patch-group associations have no version history.

- **Before switching from Scan to Install in a maintenance window**,
  run Install manually against at least 3 sample instances and verify
  all succeed AND the compliance state flips to Compliant.

- **Before deploying a StackSet patch baseline**, dry-run the
  CloudFormation template locally:
  `aws cloudformation validate-template --template-body file://patch-baseline.yaml`

- **For critical-instance Install operations**, route through SSM
  Change Manager: create a Change Template, submit a change request,
  obtain approval, then execute.

## Appendix A — OS-specific baseline quick reference

| OS | OperatingSystem value | Default source | Key filters | Typical approval window |
|---|---|---|---|---|
| Amazon Linux 2 | `AMAZON_LINUX_2` | AL2 repos | `CLASSIFICATION`, `SEVERITY` | Critical: 0 days; Medium: 7 days |
| Amazon Linux 2023 | `AMAZON_LINUX_2023` | AL2023 repos (DNF) | `CLASSIFICATION`, `SEVERITY` | Critical: 0 days; Medium: 7 days |
| Ubuntu 20.04/22.04/24.04 | `UBUNTU_20_04` / `UBUNTU_22_04` / `UBUNTU_24_04` | Ubuntu archive | `CLASSIFICATION`, `PRIORITY` | Critical: 0 days; Standard: 7 days |
| Windows Server 2019/2022 | `WINDOWS` | Windows Update / WSUS | `MSRC_SEVERITY`, `CLASSIFICATION` | Critical: 3 days (after Patch Tuesday) |
| RHEL 8/9 | `REDHAT_ENTERPRISE_LINUX` | RHUI | `CLASSIFICATION`, `SEVERITY` | Critical: 0 days; Medium: 7 days |
| CentOS 7 | `CENTOS` | CentOS vault (EOL) | `CLASSIFICATION`, `SEVERITY` | EOL — migrate off |
| macOS | `MACOS` | Apple Software Update | `PRODUCT` | Not supported via SSM in all regions |

For detailed filter keys per OS and example baselines, see
**references/patch-baseline-templates.md**.

## Appendix B — Decision tree (Scan vs Install vs Emergency)

```
Is this a routine compliance check?
├─ Yes → Operation: Scan (daily or weekly)
│        No risk; updates AWS:PatchCompliance inventory.
└─ No  → Is this a scheduled patch rollout?
        ├─ Yes → Operation: Install (weekly maintenance window)
        │        Requires: pre-snapshot, SNS, MaxConcurrency gate.
        └─ No  → Is this a zero-day emergency?
                ├─ Yes → Create emergency baseline (ApproveAfterDays: 0)
                │        Operation: Install immediately (or via Change Manager)
                │        Post-install: verify compliance, retain snapshot.
                └─ No  → REVIEW_REQUIRED — clarify intent.
```

## Appendix C — Maintenance-window cron quick reference

| Schedule | Cron expression | Notes |
|---|---|---|
| Daily 06:00 UTC | `cron(0 6 * * ? *)` | Standard daily Scan |
| Weekly Saturday 02:00 UTC | `cron(0 2 ? * SAT *)` | Standard weekly Install |
| Monthly first Sunday 02:00 UTC | `cron(0 2 ? * SUN#1 *)` | Conservative monthly Install |
| Every 4 hours | `rate(4 hours)` | High-frequency Scan (use rate, not cron) |
| Bi-weekly Saturday 02:00 UTC | Custom EventBridge + Lambda | SSM cron does not support bi-weekly natively |

**Note:** SSM cron syntax is slightly different from standard cron.
`?` is used in the day-of-month OR day-of-week field (not both). `#`
specifies the nth occurrence of a day (e.g., `SUN#1` = first Sunday).

## Recent AWS features (2024-2026)

- **SSM Quick Setup Patch Manager (2024):** One-click patch-manager
  configuration via Quick Setup in the Systems Manager console.
  Deploys a baseline, patch group, and maintenance window in a
  guided flow. Useful for greenfield fleets; limited customization
  compared to CLI-defined workflows.

- **Patch Manager AL2023 full support (2024):** AL2023 baselines
  GA in all commercial regions. DNF-based package management is
  transparent — no script changes needed beyond updating the
  baseline `OperatingSystem` value.

- **Karpenter node patching via SSM (2024-2025):** For EKS clusters
  using Karpenter, node AMIs are managed by Karpenter's
  `amiFamily` selector. Patching is handled by AMI rotation
  (disruption + replacement), not SSM Patch Manager. Do NOT install
  SSM Patch Manager on Karpenter-managed nodes — it conflicts with
  the AMI-rotation lifecycle.

- **Patch baseline snapshot support (2025):** The `SnapshotId`
  parameter on `AWS-RunPatchBaseline` now persists patch-state
  snapshots for comparison across patch cycles. Useful for audit
  trails and rollback verification.

- **Multi-account Patch Manager via Organizations (2024-2025):**
  Enhanced StackSet support for deploying patch baselines across
  an Organization. The `AWS::SSM::PatchBaseline` CloudFormation
  resource is now fully supported in StackSets (previously required
  custom resources).

- **SSM Change Manager integration with Patch Manager (2024):**
  Native integration allowing patch windows to route through
  Change Manager approval workflows. Required for regulated
  environments where patch deployment must have an approval trail.

## Expert heuristic: patch-window blast radius

Patch deployment is the highest-frequency production-risk operation in
fleet management. A single bad kernel patch deployed via a 10%-concurrency
maintenance window can take down 10% of the fleet simultaneously — and
the remaining 90% are queued to receive the same patch.

**The rule (non-obvious but critical):**

> ALWAYS patch in waves: deploy to a canary patch group (1-3 instances),
> verify for 24 hours, then deploy to the broader fleet. Never set
> MaxConcurrency above 10% for the first cycle after a baseline change.

**Why this rule exists:** Patch baselines are updated as new packages
are released by the OS vendor. A baseline that was safe last week may
pull in a broken kernel update this week. Canary patching catches this
before it reaches the fleet.

**Wave deployment pattern:**

| Wave | Patch group | Concurrency | Delay | Verification |
|---|---|---|---|---|
| 1 (canary) | `al2023-canary` (1-3 instances) | `1` | Day 0 | Manual health check + compliance verify |
| 2 (early adopters) | `al2023-early` (10% of fleet) | `3` | Day +1 | Automated health check + SNS alert |
| 3 (fleet) | `al2023-prod` (remaining 90%) | `10%` | Day +2 | Standard monitoring |

**Pre-production validation protocol (2-cycle rule):**

1. **Cycle 1 — Scan-only in prod.** Deploy the baseline, patch-group
   tags, and a Scan-only maintenance window. Verify Scan produces
   accurate compliance data (not all `NotApplicable`, not all
   `Missing`). This validates the baseline OS/filter configuration
   without risk.

2. **Cycle 2 — Canary Install in prod.** Create a separate patch group
   (`<os>-canary`) with 1-3 non-critical instances. Run Install with
   pre-snapshot. Verify all 3 succeed, reboot cleanly, and flip to
   Compliant. Monitor for 24 hours before promoting to fleet-wide.

**Detection of bad-patch rollout post-deploy:** CloudWatch alarm on
`AWS/SSM InstanceOnline` dropping by > N% within 15 minutes of a
maintenance-window start (suggests a bad patch causing boot failure).
Also alarm on `FailedCount` from `describe-instance-patch-states`
exceeding `MaxErrors` threshold. Both alarms should page the on-call
and trigger an EventBridge rule that cancels the maintenance window
via `aws ssm deregister-task-with-maintenance-window`.

**Surface in the output:** for any recommended patch automation,
include `BLAST_RADIUS: <scope>` (e.g., `fleet-wide`, `canary-only`,
`critical-exception`) and `VALIDATION_STATUS: <scan-only |
canary-install | fleet-install>`. If `VALIDATION_STATUS` is not
`fleet-install`, do NOT mark the recommendation as fully deployed.

## Domain

AWS CloudOps / Management Automation — SSM Patch Manager compliance.

## AWS documentation

- **SSM Patch Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-patch.html
- **SSM Maintenance Windows** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-maintenance.html
- **AWS-RunPatchBaseline** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-patch-runbaselinedoc.html
- **SSM Inventory** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-inventory.html
- **CloudFormation StackSets** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html
