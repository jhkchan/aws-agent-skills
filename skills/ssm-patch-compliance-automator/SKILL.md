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
  manages snapshots before patching, controls reboot behavior
  (RebootOption: RebootIfNeeded vs NoReboot), and rolls out multi-account
  patching via Organizations + CloudFormation StackSets. Covers compliance
  reporting (Compliant, NonCompliant, NotApplicable), exception lists for
  critical instances, and SNS notification/approval for patch rollouts.
  Emits AUTOMATION_DEPLOYED with a ready-to-apply baseline + maintenance
  window + compliance monitoring template or REVIEW_REQUIRED with the
  specific gap. Use when automating patch compliance, building maintenance
  windows, or hardening an existing patch rollout.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline workflow design. Live deployment
  uses aws ssm create-patch-baseline, register-patch-baseline-for-patch-group,
  create-maintenance-window, register-task-with-maintenance-window,
  describe-instance-patch-states, send-command (AWS-RunPatchBaseline),
  aws cloudformation create-stack-set (multi-account), and aws events
  put-rule/put-targets (EventBridge auto-remediation) — AWS CLI v2, SSO
  or key-based credentials.
keywords:
  - SSM Patch Manager
  - patch baseline
  - patch group
  - maintenance window
  - patch compliance
  - AWS-RunPatchBaseline
  - RebootOption
  - EventBridge
  - CloudFormation StackSets
  - AWS Organizations
  - compliance reporting
  - NonCompliant
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
  configuration. The default baseline applies to all SSM-managed
  instances, but custom baselines require explicit tag-based targeting.
- **Scan vs Install** is the most dangerous confusion. `Operation: Scan`
  reports compliance without changing anything. `Operation: Install`
  applies patches and may reboot.
- **Compliance reporting is the closing gate.** A patching workflow
  that runs Install but never verifies the compliance state flip
  (NonCompliant → Compliant) is half-built.

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

## Critical rules at a glance (do NOT bury these)

1. **Patch Group targeting is tag-based, NOT resource-group-based.**
   The tag key MUST be exactly `Patch Group` (with a space,
   case-sensitive). `PatchGroup` (no space) or `patch-group`
   (hyphenated) will NOT match. Verify with
   `describe-instance-patch-states` after tagging.

2. **Maintenance-window concurrency is per-instance, not per-window.**
   `MaxConcurrency` controls how many instances within the window patch
   simultaneously. A window with `MaxConcurrency: 1` and 500 targeted
   instances runs sequentially and will not finish within the duration.

3. **Always snapshot EC2 before an Install operation.** Patches can
   break boot (kernel update, glibc update, Windows cumulative update).
   Use `aws:createImage` in a pre-step or
   `AWS-CreateManagedLinuxInstanceWithApproval`.

4. **`AWS-RunPatchBaseline` with `Operation: Install` may reboot.**
   `RebootOption: RebootIfNeeded` (default) reboots if the OS requires
   it. `NoReboot` suppresses reboot — patches staged but not activated
   until the next reboot. NoReboot produces a false sense of compliance:
   Scan reports "installed" but the running kernel is unpatched.

5. **The default patch baseline is NOT necessarily your baseline.**
   Each OS has an AWS-managed default applied to instances without a
   custom baseline. Registering a custom baseline for a patch group
   overrides the default. Removing the association reverts silently.

## Pre-flight: data requirements

| Input | Source | Why |
|---|---|---|
| OS mix of the fleet | `ec2 describe-instances` + SSM Inventory | Drives baseline OS selection |
| Instance count per OS | Same | Drives maintenance-window sizing |
| SSM agent health | `ssm describe-instance-information` | Unhealthy agents are invisible to Patch Manager |
| Existing patch baselines | `ssm describe-patch-baselines` | Don't overwrite blindly |
| Existing maintenance windows | `ssm describe-maintenance-windows` | Avoid schedule conflicts |
| Current compliance state | `ssm describe-instance-patch-states` | Baseline before automation |
| Critical-instance list | Application team input | Exception list (Step 11) |

**If the input is malformed** (missing OS mix, zero SSM-managed
instances), emit:
```text
PATCH: <reference>
VERDICT: ERROR
REASON: Cannot design patch automation — OS mix and SSM-managed instance count are required.
GAP: Run aws ssm describe-instance-information and supply the OS breakdown.
```

## Process — Patch automation design (apply in order)

### Step 0: Expert knowledge — non-obvious Patch Manager behaviors

- **`Patch Group` tag is case-SENSITIVE and space-sensitive.** Must be
  exactly `Patch Group` (capital P, capital G, one space). Tag drift
  (e.g., Terraform applying `PatchGroup`) silently removes instances
  from the patch group.

- **`AWS-RunPatchBaseline` Install with `NoReboot` does NOT defer all
  patches.** Some packages (kernel, glibc) require reboot to take
  effect. With `NoReboot`, the package is installed but the old version
  remains active. Scan reports installed; security scanners report the
  running version as vulnerable.

- **Patch baseline `ApprovalRules` are time-based, not event-based.**
  `ApproveAfterDays: 7` means 7 days after release by the OS vendor.
  For zero-day response, create an emergency baseline with
  `ApproveAfterDays: 0`.

- **Scan-only maintenance windows do NOT consume the Install quota.**
  Daily Scan + weekly Install is the recommended pattern.

- **`register-patch-baseline-for-patch-group` is idempotent on the
  patch-group name, NOT the baseline.** Re-registering with a different
  baseline silently switches the group. Always `describe-patch-groups`
  before re-registering.

- **CloudFormation StackSets deploy the baseline resource but NOT the
  patch-group association.** Associations are per-account API calls
  requiring separate automation (Lambda-backed custom resource or
  `AWS::SSM::Association`).

- **Windows Server patching uses WSUS or Windows Update as source.**
  Private VPC instances without NAT or WSUS fail to download patches
  silently. Verify network egress before deploying a Windows baseline.

- **Amazon Linux 2023 uses DNF, not YUM.** SSM handles this
  transparently, but custom scripts calling `yum` will fail on AL2023.

- **Maintenance-window `MaxErrors` gates the window, not the task.**
  `MaxErrors: 1` with one failure cancels the ENTIRE window for
  remaining instances. Use percentage-based values for large fleets.

- **SSM Inventory `AWS:PatchCompliance` is read-only.** It reflects
  the last Scan result. There is no "trigger Install from Inventory"
  path.

### Step 1: Classify the fleet

| OS family | OperatingSystem value | Default source | Notes |
|---|---|---|---|
| Amazon Linux 2 | `AMAZON_LINUX_2` | AL2 repos | EOL 2025-06; migrate to AL2023 |
| Amazon Linux 2023 | `AMAZON_LINUX_2023` | AL2023 repos (DNF) | Use `dnf` in scripts |
| Ubuntu 20.04/22.04/24.04 | `UBUNTU_20_04` / `UBUNTU_22_04` / `UBUNTU_24_04` | Ubuntu archive | LTS releases |
| Windows Server 2019/2022 | `WINDOWS` | Windows Update / WSUS | Requires NAT or WSUS in private VPC |
| RHEL 8/9 | `REDHAT_ENTERPRISE_LINUX` | RHUI | RHUI entitlements required |

Each OS requires a separate baseline and patch-group tag value. Do NOT
mix OS under one patch group.

### Step 2: Create the OS-specific patch baseline

Amazon Linux 2023 baseline with immediate critical approval + 7-day
medium approval:

```bash
aws ssm create-patch-baseline \
  --name "al2023-prod-baseline" \
  --operating-system AMAZON_LINUX_2023 \
  --approval-rules '{
    "PatchRules": [
      {
        "PatchFilterGroup": {"Key": "SEVERITY", "Values": ["Critical", "Important"]},
        "ComplianceLevel": "CRITICAL", "ApproveAfterDays": 0
      },
      {
        "PatchFilterGroup": {"Key": "CLASSIFICATION", "Values": ["Security", "Bugfix"]},
        "ComplianceLevel": "MEDIUM", "ApproveAfterDays": 7
      }
    ]
  }'
```

Windows Server baseline (MSRC severity, 3-day approval):

```bash
aws ssm create-patch-baseline \
  --name "win2022-prod-baseline" \
  --operating-system WINDOWS \
  --approval-rules '{
    "PatchRules": [{
      "PatchFilterGroup": {"Key": "MSRC_SEVERITY", "Values": ["Critical", "Important"]},
      "ComplianceLevel": "CRITICAL", "ApproveAfterDays": 3
    }]
  }'
```

Common errors: `UnsupportedOperatingSystem` (check regional support),
`PatchFilter key not recognized` (Windows uses `MSRC_SEVERITY`, Linux
uses `SEVERITY`). See **references/patch-baseline-templates.md** for
detailed per-OS templates.

### Step 3: Target instances via Patch Group tag

Tag instances with the EXACT key `Patch Group` (case-sensitive, one space):

```bash
aws ec2 create-tags --resources i-0abc123def \
  --tags "Key=Patch Group,Value=al2023-prod"
```

Register the patch baseline for the patch group:

```bash
aws ssm register-patch-baseline-for-patch-group \
  --baseline-id "<baseline-id>" --patch-group "al2023-prod"
```

Verify: `aws ssm describe-patch-groups --filters "Name=Name,Values=al2023-prod"`

**The most common failure:** the tag key is applied via IaC with wrong
case or spacing. Always verify with `describe-instance-patch-states`.

### Step 4: Configure the maintenance window

```bash
aws ssm create-maintenance-window \
  --name "al2023-prod-patch-window" \
  --schedule "cron(0 2 ? * SAT *)" \
  --duration 4 --cutoff 1
```

Schedule: `cron(0 2 ? * SAT *)` = Saturday 02:00 UTC. Duration: 4 hours.
Cutoff: 1 hour (no new tasks start in the last hour).

Register targets and the patch task:

```bash
aws ssm register-target-with-maintenance-window \
  --window-id "<window-id>" --target-type "RESOURCE_GROUP" \
  --targets "Key=tag:Patch Group,Values=al2023-prod"

aws ssm register-task-with-maintenance-window \
  --window-id "<window-id>" --targets "Key=WindowTargetIds,Values=<target-id>" \
  --task-arn "AWS-RunPatchBaseline" --task-type "RUN_COMMAND" \
  --task-invocation-parameters '{"RunCommand":{"Parameters":{"Operation":["Install"],"RebootOption":["RebootIfNeeded"]}}}' \
  --max-concurrency "10%" --max-errors "5%" --priority 1
```

**Concurrency sizing:**

| Fleet size | MaxConcurrency | MaxErrors | Rationale |
|---|---|---|---|
| < 10 | `1` | `1` | Patch one at a time |
| 10-50 | `3` | `2` | Small batches |
| 50-200 | `10%` | `5%` | Percentage-based |
| 200-1000 | `5%` | `3%` | Conservative |
| > 1000 | `1%` | `1%` | Wave deployment |

### Step 5: Choose Scan vs Install operation

| Operation | What it does | Risk | When |
|---|---|---|---|
| `Scan` | Checks packages against baseline; reports missing | None | Daily |
| `Install` | Downloads + installs patches; may reboot | Reboot, app disruption | Weekly window |

**Recommended: daily Scan + weekly Install.** Never run Install in the
daily scan window — a common misconfiguration that causes unexpected
reboots.

### Step 6: Wire EventBridge auto-remediation on NonCompliant

```bash
aws events put-rule --name "patch-noncompliant-remediation" \
  --event-pattern '{
    "source": ["aws.ssm"],
    "detail-type": ["Patch Compliance State Change"],
    "detail": {"compliance-type": ["Patch"], "new-compliance-status": ["NON_COMPLIANT"]}
  }'
```

Target: SSM Automation running `AWS-RunPatchBaseline` with Install on
the non-compliant instance (via InputTransformer mapping instance-id).

**Safety:** auto-remediation with Install may reboot. For production,
route through SSM Change Manager or add an SNS delay. Do NOT enable
auto-Install on critical instances without a snapshot gate.

### Step 7: Integrate Patch Manager with Inventory

SSM Inventory `AWS:PatchCompliance` is auto-populated by Scan. Query:

```bash
aws ssm describe-instance-patch-states --instance-ids i-0abc123def
```

Key fields: `MissingCount`, `FailedCount`, `InstalledCount`,
`NotApplicableCount`, `Operation`, `OperationEndTime`.

**Config integration:** enable managed rule
`ec2-managedinstance-patch-compliance` for historical compliance audit.

### Step 8: Multi-account rollout via Organizations + StackSets

Deploy baselines via StackSets to all member accounts:

```bash
aws cloudformation create-stack-set \
  --stack-set-name "ssm-patch-baseline-al2023" \
  --template-body file://patch-baseline.yaml \
  --permission-model SERVICE_MANAGED \
  --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false

aws cloudformation create-stack-instances \
  --stack-set-name "ssm-patch-baseline-al2023" \
  --deployment-targets OrganizationalUnitIds=["ou-abc-123defghi"] \
  --regions us-east-1 us-west-2
```

**Important:** StackSets deploys the baseline resource ONLY.
Patch-group associations and instance tagging must be handled via
`AWS::SSM::Association` or Lambda custom resources.

### Step 9: Safety gates — snapshot, approval, notification

Every Install workflow MUST include safety gates:

| Gate | How | When |
|---|---|---|
| Pre-patch AMI snapshot | `aws:createImage` step before Install | Every EC2 Install — non-negotiable |
| SNS notification | `--notification-config` on task | All workflows — non-negotiable |
| Approval gate | SSM Change Manager or `aws:approve` | Production, regulated workloads |
| MaxErrors circuit breaker | `--max-errors "5%"` | All batch-patching |
| Post-patch health check | Custom runbook step | Production with HTTP health |

Custom runbook with pre-patch snapshot (abbreviated):

```yaml
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
parameters:
  InstanceId: {type: String}
  AutomationAssumeRole: {type: String}
mainSteps:
  - name: CreatePrePatchSnapshot
    action: aws:createImage
    inputs:
      InstanceId: '{{ InstanceId }}'
      ImageName: 'pre-patch-{{ InstanceId }}-{{global:DATE_TIME}}'
      NoReboot: true
  - name: RunPatchInstall
    action: aws:runCommand
    inputs:
      DocumentName: AWS-RunPatchBaseline
      InstanceIds: ['{{ InstanceId }}']
      Parameters: {Operation: Install, RebootOption: RebootIfNeeded}
    isCritical: true
    onFailure: abort
```

### Step 10: Build compliance reporting

```bash
aws ssm describe-instance-patch-states \
  --instance-ids $(aws ssm describe-instance-information \
    --query 'InstanceInformationList[?PingStatus==`Online`].InstanceId' \
    --output text | tr '\t' ' ') \
  --query 'InstancePatchStates[].{Id:InstanceId,Group:PatchGroup,Missing:MissingCount,Failed:FailedCount,Installed:InstalledCount,NotApplicable:NotApplicableCount}' \
  --output table
```

| Category | Definition | Action |
|---|---|---|
| Compliant | `MissingCount: 0` and `FailedCount: 0` | None |
| NonCompliant | `MissingCount > 0` | Schedule Install |
| InstallFailed | `FailedCount > 0` | Investigate per-patch failure |
| NotApplicable | All patches `NotApplicable` | Verify baseline matches OS |
| NotScanned | No patch state | Verify SSM agent health + tag |

### Step 11: Handle critical-instance exceptions

For instances that must NOT be auto-patched:

- **Tag exclusion:** do NOT tag with a `Patch Group` value. Untagged
  instances are invisible to Patch Manager.
- **Scan-only patch group:** tag with `Patch Group=critical-scan-only`,
  register a baseline, but create NO Install maintenance window.
- **Approval-required:** create a window with `MaxConcurrency: 1`
  routed through SSM Change Manager.

Maintain an exception register with instance ID, reason, review date,
and approver. Review quarterly — an exception that never expires is a
permanent security hole.

### Step 12: Manage reboot behavior (RebootOption)

| RebootOption | Behavior | Use case |
|---|---|---|
| `RebootIfNeeded` (default) | Reboots if OS requires it after Install | General-purpose patching |
| `NoReboot` | Patches staged, no reboot; running kernel unpatched | Controlled windows with separate reboot |

**The `NoReboot` trap:** Scan reports installed (on disk) but running
kernel/processes use old versions. Security scanners flag the instance
as vulnerable. If using `NoReboot`, schedule a reboot within 24 hours.

## Output format

```text
PATCH: <reference>
FLEET: <OS mix + instance count>
BASELINE:
  - Name: <name> / OS: <os> / Approval rules: <summary>
  - Baseline ID: <ID>
PATCH_GROUP:
  - Tag key: Patch Group / Tag value: <name> / Instance count: <N>
MAINTENANCE_WINDOW:
  - Scan schedule: <cron> / Install schedule: <cron>
  - Duration: <hours> / MaxConcurrency: <value> / MaxErrors: <value>
COMPLIANCE_MONITORING:
  - Inventory: AWS:PatchCompliance / Config rule: <name> / Dashboard: <name>
SAFETY:
  - Pre-patch snapshot: <enabled/disabled>
  - SNS notification: <ARN> / Approval gate: <type>
  - Exception list: <count or none>
REBOOT: RebootIfNeeded | NoReboot
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippets>
```

### Worked example — AUTOMATION_DEPLOYED

```text
PATCH: al2023-prod-patch-rollout
FLEET: 120 Amazon Linux 2023 instances (prod)
BASELINE: al2023-prod-baseline / AMAZON_LINUX_2023 / Critical:0d Medium:7d / pb-0abc123def
PATCH_GROUP: Patch Group=al2023-prod / 120 instances
MAINTENANCE_WINDOW: Scan daily 06:00 UTC / Install weekly Sat 02:00 UTC / 4h / 10% / 5%
COMPLIANCE_MONITORING: AWS:PatchCompliance / ec2-managedinstance-patch-compliance / patch-overview
SAFETY: snapshot=enabled / SNS=arn:...:patch-notify / approval=none / exceptions=2
REBOOT: RebootIfNeeded
VERDICT: AUTOMATION_DEPLOYED
GAP: None
```

### Worked example — REVIEW_REQUIRED

```text
PATCH: win2022-prod-patch-rollout
FLEET: 45 Windows Server 2022 (prod, private VPC)
BASELINE: win2022-prod-baseline / WINDOWS / Critical:3d / pb-0xyz789ghi
PATCH_GROUP: Patch Group=win2022-prod / 45 instances
MAINTENANCE_WINDOW: TBD (blocked)
VERDICT: REVIEW_REQUIRED
GAP: Windows instances in private VPC without NAT/WSUS/VPC endpoints. Patches will fail to download. Resolution: (1) add NAT gateway; (2) deploy WSUS; (3) create VPC endpoints. No snapshot workflow, SNS, or dashboard configured.
TEMPLATE: (blocked until network egress resolved)
```

## Anti-Patterns — NEVER do these things

- NEVER use `PatchGroup` (no space) or `patch-group` as the tag key. SSM
  matches EXACTLY `Patch Group` (capital P, capital G, one space).

- NEVER run `Operation: Install` in a daily maintenance window without
  approval. Daily Install causes unexpected reboots. Scan daily, Install
  weekly.

- NEVER patch without a pre-patch AMI snapshot. Kernel/glibc/Windows
  cumulative updates can break boot.

- NEVER set `MaxErrors: 1` on a large-fleet window. One failure cancels
  the entire window. Use percentage-based `MaxErrors`.

- NEVER set `MaxConcurrency` to the full fleet count. Cap at 10-20% for
  production. A bad patch deployed to 100% of fleet simultaneously is
  unrecoverable.

- NEVER use `NoReboot` without scheduling a follow-up reboot within 24
  hours. Running kernel stays unpatched; security scanners flag it.

- NEVER assume StackSets wire patch-group associations. StackSets deploy
  baseline resources only. Use `AWS::SSM::Association` for associations.

- NEVER enable EventBridge auto-remediation with `Install` on production
  without a snapshot gate and SNS. NonCompliant triggers immediate
  Install, which may reboot during business hours.

- NEVER assume `describe-instance-patch-states` is real-time. It reflects
  the LAST Scan/Install operation. Run Scan before reporting to auditors.

- NEVER mix OS families under one patch group. A WINDOWS baseline on a
  Linux group produces zero patches.

- NEVER delete a patch baseline with active patch-group associations.
  Instances fall back to the AWS default silently. Deregister first.

- NEVER set `--cutoff 0` on a maintenance window. No buffer for
  long-running operations. Set cutoff to at least 1 hour.

- NEVER create an exception list without review dates. Permanent
  exceptions are permanent security holes.

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE** before any state-changing operation.
- **Back up current patch-baseline associations:**
  `aws ssm describe-patch-groups > /tmp/patch-groups-backup.json`
- **Before Scan→Install switch:** run Install manually on 3+ sample
  instances and verify compliance state flips.
- **For critical-instance Install:** route through SSM Change Manager.

## Appendix A — OS-specific baseline quick reference

| OS | Filter keys | Typical approval |
|---|---|---|
| AL2/AL2023 | `CLASSIFICATION`, `SEVERITY` | Critical: 0d; Medium: 7d |
| Ubuntu | `CLASSIFICATION`, `PRIORITY` | Critical: 0d; Standard: 7d |
| Windows | `MSRC_SEVERITY`, `CLASSIFICATION` | Critical: 3d (after Patch Tuesday) |
| RHEL | `CLASSIFICATION`, `SEVERITY` | Critical: 0d; Medium: 7d |

For detailed templates per OS, see **references/patch-baseline-templates.md**.

## Appendix B — Decision tree

```
Routine compliance check? → Operation: Scan (daily)
Scheduled patch rollout? → Operation: Install (weekly window)
  Requires: pre-snapshot, SNS, MaxConcurrency gate
Zero-day emergency? → Emergency baseline (ApproveAfterDays: 0)
  → Install immediately or via Change Manager
```

## Appendix C — Maintenance-window cron reference

| Schedule | Cron | Notes |
|---|---|---|
| Daily 06:00 UTC | `cron(0 6 * * ? *)` | Standard daily Scan |
| Weekly Sat 02:00 UTC | `cron(0 2 ? * SAT *)` | Standard weekly Install |
| Monthly 1st Sun | `cron(0 2 ? * SUN#1 *)` | Conservative monthly |
| Every 4 hours | `rate(4 hours)` | High-frequency Scan |

## Recent AWS features (2024-2026)

- **SSM Quick Setup Patch Manager (2024):** One-click configuration via
  console. Good for greenfield; limited customization.
- **AL2023 full support (2024):** GA in all commercial regions. DNF-
  based, transparent to SSM.
- **Karpenter node patching (2024-2025):** For EKS + Karpenter, patching
  is via AMI rotation, NOT SSM Patch Manager. Do NOT install SSM Patch
  Manager on Karpenter-managed nodes.
- **Patch baseline snapshot (2025):** `SnapshotId` parameter persists
  patch-state snapshots for comparison and audit.
- **StackSets patch baseline (2024-2025):** `AWS::SSM::PatchBaseline`
  fully supported in StackSets (previously required custom resources).
- **Change Manager + Patch Manager (2024):** Native integration for
  approval workflows. Required for regulated environments.

## Expert heuristic: patch-window blast radius

> ALWAYS patch in waves: deploy to a canary patch group (1-3 instances),
> verify for 24 hours, then deploy to the broader fleet. Never set
> MaxConcurrency above 10% for the first cycle after a baseline change.

**Why:** baselines update as OS vendors release packages. A safe
baseline last week may pull a broken kernel update this week. Canary
catches this before fleet-wide damage.

**Wave pattern:**

| Wave | Patch group | Concurrency | Delay | Verify |
|---|---|---|---|---|
| 1 (canary) | `<os>-canary` (1-3) | `1` | Day 0 | Manual health + compliance |
| 2 (early) | `<os>-early` (10%) | `3` | Day +1 | Automated health + SNS |
| 3 (fleet) | `<os>-prod` (90%) | `10%` | Day +2 | Standard monitoring |

**Pre-production validation (2-cycle rule):**
1. Cycle 1: Scan-only in prod. Verify Scan produces accurate data.
2. Cycle 2: Canary Install in prod (1-3 non-critical instances). Verify
   success + compliance flip + clean reboot. Monitor 24h.

**Bad-patch detection:** alarm on `AWS/SSM InstanceOnline` dropping >N%
within 15 min of window start. Alarm on `FailedCount` exceeding
`MaxErrors`. Both should page on-call and cancel the window.

## Domain

AWS CloudOps / Management Automation — SSM Patch Manager compliance.

## AWS documentation

- **SSM Patch Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-patch.html
- **SSM Maintenance Windows** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-maintenance.html
- **AWS-RunPatchBaseline** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-patch-runbaselinedoc.html
- **SSM Inventory** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-inventory.html
- **CloudFormation StackSets** — https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html
