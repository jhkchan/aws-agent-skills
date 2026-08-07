---
name: ssm-patch-operator
description: >-
  Operates SSM Patch Manager workflows safely — patch baseline authoring
  (AWS-managed and custom), patch group tag targeting, AWS-RunPatchBaseline
  Scan and Install operations, maintenance window task scheduling, and
  patch compliance reporting. Runs deterministic pre-checks (instance
  managed-status, SSM Agent health, baseline association, free disk
  space, reboot tolerance, maintenance-window target membership,
  rate-control budget), executes the patching operation behind a
  CONFIRM gate, and emits a verdict (READY | BLOCKED | COMPLETED) per
  operation with the exact send-command sequence, expected side-effects
  (reboot, compliance delta), and post-verification. Use when running a
  security patch sweep, scheduling a maintenance-window patch task,
  diagnosing a NON_COMPLIANT instance, planning a fleet-wide Install
  with rate-control, or building a custom baseline with approval rules.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws ssm describe-instance-information, describe-patch-baseline,
  describe-patch-baselines, describe-patch-states, list-compliance-items,
  send-command (AWS-RunPatchBaseline), get-command-invocation,
  create-association, update-association, create-maintenance-window,
  register-task-with-maintenance-window, and aws ec2 describe-instances
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Systems Manager
  - SSM
  - Patch Manager
  - patch baseline
  - AWS-RunPatchBaseline
  - AWS-ApplyPatchBaseline
  - patch group
  - Scan
  - Install
  - compliance
  - NON_COMPLIANT
  - maintenance window
  - rate-control
  - ApprovalRules
  - ApproveAfterDays
  - AmazonSSMManagedInstanceCore
  - AmazonLinux2
  - Ubuntu
  - Windows
  - macOS
  - kernel panic
  - reboot
  - NoReboot
  - SSM Quick Setup
tags: [ssm, systems-manager, patch-manager, management, patching, compliance, maintenance-window, operate]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Management
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY | BLOCKED | COMPLETED"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags: [ssm, systems-manager, patch-manager, management, patching, compliance, maintenance-window, operate]
  dependencies: [aws-orchestrator]
  keywords:
    - Systems Manager
    - SSM
    - Patch Manager
    - patch baseline
    - AWS-RunPatchBaseline
    - patch group
    - maintenance window
  when_to_use: >-
    Running a security patch sweep against an EC2 or hybrid fleet, creating
    or modifying a custom patch baseline with approval rules, scheduling a
    maintenance-window task that runs AWS-RunPatchBaseline with
    Operation=Install, diagnosing a NON_COMPLIANT instance, planning a
    fleet-wide Install with rate-control and max-errors, switching an
    association from Scan to Install, or pre-checking a host before the
    next patch window.
  activation_triggers:
    - "patch this instance"
    - "run AWS-RunPatchBaseline"
    - "scan for missing patches"
    - "install missing patches"
    - "create patch baseline"
    - "custom patch baseline rules"
    - "patch group tag"
    - "schedule patching maintenance window"
    - "diagnose NON_COMPLIANT patch"
    - "Operation=Install"
    - "Operation=Scan"
    - "rate-control patching"
    - "approve after days"
    - "NoReboot patch install"
  invocation_schema: >-
    Input: either (a) a patch operation request (operation=scan|install|
    create-baseline|update-baseline|create-mw|register-task) paired with
    instance(s), patch baseline, and optional maintenance-window context,
    OR (b) an instance-id / baseline-id / maintenance-window-id for live-
    account execution. Output: deterministic OPERATION/VERDICT/PRE_CHECKS/
    STEPS/POST_VERIFY block per operation, where VERDICT is one of READY,
    BLOCKED, COMPLETED.
---

# SSM Patch Operator

## What this skill does

Executes SSM Patch Manager operations on EC2 and hybrid (`mi-*`) fleets
correctly and safely. Runs deterministic pre-checks (instance managed
status, SSM Agent health, baseline association, free disk space, reboot
tolerance, maintenance-window target membership), plans the exact
`aws ssm send-command` / association / maintenance-window sequence, and
verifies the result via compliance items and command invocations. Every
state-changing operation runs behind a CONFIRM gate — `Operation=Install`
can reboot hosts and restart services, never auto-trigger.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority order + OS-by-OS baseline matrix | Before any operation |
| **§ Mindset** | Why pre-checks matter, the Scan-vs-Install trap, the reboot surprise | Understanding the safety model |
| **§ Pre-flight** | Instance metadata gate — managed status, agent, baseline, free disk | Before executing any CLI |
| **§ Process** | Per-operation planning: scan, install, baseline author, maintenance window | When choosing which operation to run |
| **§ Output format** | Structured VERDICT block with COMMANDS, COMPLIANCE_DELTA, REBOOT | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that reboot fleets or miss compliance drift | Review before any Install |
| **§ Pre-flight safety** | CONFIRM gate, rate-control, snapshot pre-state, rollback | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (instance UNMANAGED, agent offline, no baseline associated, free disk < 2 GB on root, instance-state not `running`, maintenance-window target empty, baseline auto-approves more than expected) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator `yes` |
| `COMPLETED` | Operation finished and post-verification passed (command `Success`, compliance delta verified, host back online if rebooted) | Emit compliance summary, side-effects, follow-ups |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY):**

1. **Managed status** — instance must appear in `describe-instance-information`
   with `PingStatus: Active` and `LastPingDateTime` < 30 min ago. Downstream
   pre-checks are noise on an unreachable host.
2. **IAM role** — EC2 instance profile (or hybrid activation role) must carry
   `AmazonSSMManagedInstanceCore` (or verified-equivalent) so the agent can
   run `AWS-RunPatchBaseline`.
3. **Disk space** — `AWS-RunPatchBaseline` with `Operation=Install` needs
   roughly 2 GB free on the root volume (and on Windows `%SystemDrive%`) to
   stage packages and backups. Install on a full disk fails mid-way and
   leaves the package manager in a broken state.
4. **Patch baseline association** — instance must reach a baseline either via
   the regional default, a `Patch Group` tag, or an explicit
   `AWS-ApplyPatchBaseline`/`AWS-RunPatchBaseline` association. No baseline →
   Scan returns zero findings (silent false-clean), Install no-ops.
5. **Baseline scope** — surface what the baseline auto-approves. A custom
   baseline with `ApproveAfterDays: 0` and broad classifications will install
   far more than the operator expects. Always dump `describe-patch-baseline`
   before the first Install.
6. **Reboot tolerance & maintenance window** — Install may reboot the host;
   if the instance is in an ASG without ELB grace, in a Multi-AZ RDS primary
   pair, or outside the maintenance window, BLOCK until the operator confirms.

**Cost/time baselines (2026):**

- Scan: ~30 seconds to 5 minutes per host (package-manager-bound).
- Install: minutes to ~1 hour per host (depends on patch count; Windows
  cumulative updates dominate).
- Cross-region Patch Baseline export/import: the baseline itself is small
  JSON; replication is metadata-only (seconds).
- SSM data transfer for command output: free in-region; cross-region command
  output to S3 incurs normal S3 + replication costs.

## OS-by-OS baseline matrix

| OS | Default baseline | Default document | Reboot-on-Install |
|---|---|---|---|
| Amazon Linux 2 | `AWS-AmazonLinux2DefaultPatchBaseline` | `AWS-RunPatchBaseline` | Kernel update reboots; userspace usually does not |
| Amazon Linux 2023 | `AWS-AmazonLinux2023DefaultPatchBaseline` | `AWS-RunPatchBaseline` | Kernel update reboots |
| Ubuntu 20.04 / 22.04 / 24.04 | `AWS-UbuntuDefaultPatchBaseline` | `AWS-RunPatchBaseline` | Kernel update reboots (snapd holds kernel) |
| RHEL 7/8/9 | `AWS-RedHatDefaultPatchBaseline` | `AWS-RunPatchBaseline` | Kernel update reboots |
| SUSE SLES | `AWSSUSEDefaultPatchBaseline` | `AWS-RunPatchBaseline` | Kernel update reboots |
| Windows Server 2012R2–2022 | `AWS-WindowsDefaultPatchBaseline` | `AWS-RunPatchBaseline` (uses `AWS-WindowsPatchBaseline` family on the baseline side) | Cumulative update reboots; `NoReboot=true` leaves `InstalledPending` |
| macOS (EC2 Mac hosts) | `AWS-macOSDefaultPatchBaseline` | `AWS-RunPatchBaseline` | OS or firmware update reboots; macOS host may need `aws ssm start-automation-execution AWS-UpdateMacOS` flow |

The default baseline only applies if no custom baseline is set as the
regional default AND no `Patch Group` tag matches a custom baseline. Always
verify which baseline is in effect for the specific instance before judging
compliance.

## Mindset

**One-line takeaway:** `Operation=Scan` writes a compliance record without
touching packages; `Operation=Install` mutates the host and may reboot it.
Driven by three Patch Manager realities:

- **Scan is non-destructive, Install is state-changing.** A bare
  `send-command AWS-RunPatchBaseline` defaults to `Operation=Scan`. Many
  operators assume the association they "enabled" is patching; in reality
  the default is to *report* compliance, not remediate it. A fleet can sit
  `NON_COMPLIANT` for years while every association shows `Success` — the
  scan knew about the gap and nothing installed patches.
- **Baseline scope is the install contract.** `ApprovalRules` decide what
  the Install actually applies. `ApproveAfterDays: 0` approves every patch
  on release (aggressive); `ApproveAfterDays: 7` waits a week.
  Classification + Severity filters narrow which package classes are in
  scope. An Install without first dumping the baseline's
  `ApprovalRules.PatchRules[]` is "sign without reading".
- **Patch Group is a tag, not an association.** Instances link to a custom
  baseline via the case-sensitive tag key `Patch Group` (space, capital G).
  Without the tag, the instance falls back to the regional default baseline
  — silently. A "patched" fleet with no `Patch Group` tags may be patching
  against the wrong baseline entirely.

## Pre-flight: instance metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-instance-information` returns 50/page by default
— drain `--next-token` for fleet-wide operations. `describe-patch-states`
paginates at 100/page. `list-compliance-items` paginates similarly.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws ssm describe-instance-information --instance-information-filter-list
   Key=InstanceIds,ValueSet=<id>` — confirm `PingStatus: Active` and
   `LastPingDateTime` < 30 min ago. Capture `PlatformType`, `PlatformName`,
   `PlatformVersion`, `ResourceType`, `IamRoleARN`.
2. `aws ec2 describe-instances --instance-ids <id>` — confirm `State: running`
   and capture the IAM instance profile, VPC, subnet, and tags. Diff against
   SSM's view to find instances that have never appeared in SSM (silent
   coverage gap).
3. `aws ssm describe-patch-baselines --filters Key=OWNER,Values=Self,Key=OPERATING_SYSTEM,Values=<OS>`
   — list custom baselines. Separately fetch AWS-owned:
   `--filters Key=OWNER,Values=AWS`.
4. `aws ssm get-patch-baseline-for-instance --instance-id <id>` — returns the
   *effective* baseline for this instance (resolves default + `Patch Group`
   tag + explicit association). This is the source of truth, not
   `describe-patch-baselines`.
5. `aws ssm describe-patch-states --instance-ids <id>` — last scan timestamp,
   installed/missing counts by severity.
6. `aws ssm list-compliance-items --resource-ids <id> --resource-types ManagedInstance`
   — per-patch compliance rows.
7. `aws ssm describe-instance-associations-status --instance-id <id>` — is
   there a `AWS-ApplyPatchBaseline`/`AWS-RunPatchBaseline` association?
   Which Operation?
8. `aws ssm describe-maintenance-window-executions --window-id <id>` (if a
   maintenance window is the target) — last execution status.
9. (Optional, requires SSM document execution) `aws ssm send-command
   --document-name AWS-RunShellScript --parameters commands=["df -m /",
   "df -m /var"]` — confirm free disk space pre-Install.

**Malformed input:** if the input JSON is invalid or missing required fields,
emit `VERDICT: ERROR` with `REASON: Instance/operation configuration is not
valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws ssm describe-instance-information
--instance-information-filter-list Key=InstanceIds,ValueSet=<id> --output
json and aws ssm get-patch-baseline-for-instance --instance-id <id>
--output json, then re-plan.`

| Instance attribute | Effect on operation |
|---|---|
| `PingStatus: Active` + `LastPingDateTime` < 30 min | Pre-check passes. |
| `PingStatus: ConnectionLost` / `Inactive` | BLOCKED — host unreachable. Classify UNMANAGED and stop. |
| `ResourceType: EC2Instance`, no `IamInstanceProfile` | BLOCKED — no SSM role. |
| `ResourceType: ManagedInstance` (`mi-*`), role lacks `AmazonSSMManagedInstanceCore` | BLOCKED — hybrid activation role gap. |
| `PlatformType: Linux` / `Windows` / `macOS` | Selects the OS-family default baseline and the patch-filter taxonomy. |
| `IsLatestVersion: false` | WARN — old agent; may misreport compliance. Surface but do not BLOCK. |
| No `Patch Group` tag AND no explicit association | Falls back to the regional default. Surface as a CONFIG_GAP-style note, not a BLOCKED unless the operator's intent is to use a custom baseline. |
| Instance `State: stopped`, `stopping`, `shutting-down` | BLOCKED — patch execution requires `running`. |
| Free disk < 2 GB on root (Linux) / `%SystemDrive%` (Windows) | BLOCKED for Install; Scan can still proceed. |
| `AWS-RunPatchBaseline` association with `Operation=Scan` only | Install will not run on schedule; surface for explicit Install command or association update. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Patch Manager behaviors

These behaviors are easy to misjudge without operational SSM experience.
Each changes a plan if ignored:

- **`AWS-RunPatchBaseline` and `AWS-ApplyPatchBaseline` are two documents,
  one family.** `AWS-RunPatchBaseline` is the modern document (Linux,
  Windows, macOS). `AWS-ApplyPatchBaseline` is the legacy Windows-only
  document kept for back-compat. Both accept `Operation: Scan | Install`.
  New associations should use `AWS-RunPatchBaseline`.

- **Default Operation is `Scan`.** A bare `send-command --document-name
  "AWS-RunPatchBaseline"` with no `--parameters` runs Scan. An association
  created without `Operation=Install` is also Scan. The single most common
  "why are we still NON_COMPLIANT?" root cause is a Scan-only association
  reporting green.

- **`NoReboot=true` does not eliminate reboots; it defers them.** On
  Windows, patches that require a reboot install but stay
  `InstalledPending` until the next reboot. On Linux, a kernel update is
  installed to disk and only activates on reboot. The host is technically
  running stale code; compliance will show COMPLIANT only after reboot.
  Never claim "patched without reboot" without surfacing the
  `InstalledPending` state.

- **Patch Group tag key is case-sensitive.** `Patch Group` (space, capital
  G) is the recognized key. `patch group`, `PatchGroup`, `patch-group` are
  NOT recognized — the instance falls back to the default baseline silently.
  Always quote-tag in shell: `Key="Patch Group",Value=prod-linux-critical`.

- **Custom baseline requires being "set as default" OR a matching Patch
  Group.** Creating `pb-0123` with custom rules does nothing until either
  `set-default-patch-baseline --baseline-id pb-0123 --operating-system
  AMAZON_LINUX_2` is run (replaces the AWS default for that OS in that
  region) OR a `Patch Group` tag value matches the baseline's name. A
  custom baseline that is neither is dead configuration.

- **Baseline rules are AND-ed across filters.** A rule with
  `Classification=Security, Severity=Critical` installs only patches that
  match BOTH. Multiple `PatchRules[]` entries are OR-ed (any rule match
  qualifies the patch). Misreading this produces "we approved Critical but
  nothing installed" when the patch was classified `Security/Important`.

- **ApproveAfterDays counts from patch RELEASE, not from baseline creation.**
  `ApproveAfterDays: 7` approves a patch 7 days after the upstream vendor
  publishes it. A baseline created today with `ApproveAfterDays: 7` will
  immediately approve any patch older than 7 days — a backdoor to "install
  everything" on first run. Always test on a single instance first.

- **Scan results report against the EFFECTIVE baseline, not the default.**
  If the instance's effective baseline is custom and narrow, a Scan may
  report `COMPLIANT` while a broad Security advisory is missing — it was
  out-of-scope for the baseline. The compliance report is "compliant with
  the configured baseline", not "all known CVEs are addressed".

- **`Install` on a fleet without `--max-errors 0 --max-concurrency "10%"`
  reboots the fleet simultaneously.** A bare `send-command --instance-ids
  i-a,i-b,i-c,...,i-z` runs in parallel across all targets and reboots them
  concurrently. Always use rate-control for fleet Installs.

- **Maintenance Window target membership is computed at execution time.**
  An instance added to the `Patch Group` tag mid-window is NOT picked up
  that cycle. Always patch-target via `--targets Key=tag:Patch
  Group,Values=<group>` on the maintenance window and verify membership
  before the window opens.

- **`AWS-RunPatchBaseline` reboots via the OS-native mechanism.** On Linux
  this is `shutdown -r`. On Windows it is the Windows Update API reboot.
  `NoReboot=true` suppresses BOTH — but a kernel patch on Linux still
  requires eventual reboot to activate.

- **Patch Manager does NOT auto-update the SSM Agent.** A separate
  `AWS-UpdateSSMAgent` association is required. Old agents misreport
  compliance on newer OSes (Amazon Linux 2023 in particular needs a
  recent agent).

- **`describe-patch-states` and `list-compliance-items` are eventually
  consistent after a Scan.** Allow ~30 seconds to 2 minutes for the
  compliance items to converge before re-checking. A "scan returned no
  findings" immediately after `Operation=Scan` is usually eventual
  consistency, not an empty result.

- **Cross-account / cross-region patch baseline replication is manual.**
  There is no native "replicate baseline" API. Export the baseline JSON
  via `describe-patch-baseline`, then `create-patch-baseline` in the
  destination account/region. The baseline ID will differ.

- **Install with `Snapshot Ids` is for Debian/Ubuntu patch holds.** Ubuntu
  snap-based packages can pin via `Snapshot Ids` in the baseline. Misuse
  causes "Install no-op" because the snapshot version is held.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is BLOCKED
with the failed checks enumerated in PRE_CHECKS. Do NOT execute the
operation.

**For ALL operations:**
1. Instance is `running` (`ec2 describe-instances`) and `PingStatus: Active`
   with `LastPingDateTime` < 30 min (`ssm describe-instance-information`).
2. IAM role includes `AmazonSSMManagedInstanceCore` (or verified equivalent
   that grants `ssm:SendCommand`, `ssm:GetCommandInvocation`,
   `ssm:StartSession`, and the patch-related SSM actions).
3. The caller (operator role) holds `ssm:SendCommand`,
   `ssm:GetCommandInvocation`, `ssm:DescribePatch*`,
   `ssm:ListComplianceItems`, and (for Install) `ssm:StartAssociationsOnce`.
4. No concurrent command on the instance (`ssm list-commands --filters
   Key=InstanceId,Values=<id> Key=Status,Values=Pending,InProgress`).
   Default per-instance concurrency is 1; a second command returns
   `TargetNotConnected` or `InvalidInstanceId`.

**For Scan (`send-command AWS-RunPatchBaseline Operation=Scan`):**
5. The instance's effective baseline is non-empty (verify via
   `get-patch-baseline-for-instance`). A baseline with zero rules produces
   a Scan that returns zero findings — silent false-clean.
6. SSM Agent version is recent enough for the OS (Amazon Linux 2023 needs
   agent v3.x+).

**For Install (`send-command AWS-RunPatchBaseline Operation=Install`):**
5. ALL of the Scan pre-checks.
6. Free disk on root (Linux) / `%SystemDrive%` (Windows) >= 2 GB. Verify
   via a quick `AWS-RunShellScript "df -m /"` (Linux) or
   `Get-PSDrive C` (Windows) before the Install command.
7. Snapshot pre-state for rollback: tag the AMI or capture
   `describe-instances` JSON. Patch Manager does NOT auto-snapshot.
8. Reboot tolerance confirmed: instance is NOT in an active ALB target
   without deregistration, is NOT a Multi-AZ RDS primary's only EC2
   dependency, and IS inside the maintenance window (if applicable).
9. Baseline `ApprovalRules` reviewed and matches operator intent. A
   custom baseline with `ApproveAfterDays: 0` and broad classifications
   will install far more than expected. Dump
   `aws ssm describe-patch-baseline --baseline-id <id>` and surface the
   approval scope in NOTES.
10. (Optional but recommended) Pre-Install snapshot:
    `aws ec2 create-snapshot --volume-id <root-volume-id>
    --description "pre-patch $(date -u +%FT%TZ)"`.

**For create/update patch baseline:**
5. The baseline payload references valid `OperatingSystem`, `Product`
   values (`AmazonLinux2`, `AmazonLinux2023`, `Ubuntu2004`, `Ubuntu2204`,
   `Ubuntu2404`, `RedhatEnterpriseLinux7`/`8`/`9`, `Suse15`,
   `WindowsServer2019`, `WindowsServer2022`, `macOS12.5` etc.).
6. `ApprovalRules.PatchRules[]` `PatchFilterGroup` values match the
   supported classification/severity taxonomy for that OS.
7. The baseline is being set as default OR has a `Patch Group` tag value
   mapped to its name. Otherwise the baseline is dead configuration.
8. (For update) `--baseline-version` is being incremented intentionally;
   the previous version is preserved in baseline history but not auto-
   rolled back.

**For maintenance window create / register-task:**
5. `--schedule` cron expression is valid and points to the intended time
   zone (`--schedule-timezone`, default UTC).
6. `--duration 2` (hours) and `--cutoff 1` (hours) leave a safe buffer.
7. `--targets` resolves to a non-empty set at the planned execution time
   (verify via `aws ssm describe-maintenance-window-targets --window-id
   <id>` after registration).
8. The task's `--task-parameters` reference `Operation=Install` (or
   `Scan`), the right `Snapshot Ids`, and `NoReboot` as intended.
9. The maintenance window's IAM service role (`--service-role-arn`) trusts
   `ssm.amazonaws.com` and has `AmazonSSMAutomationRole` or equivalent.

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI sequence
and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the baseline +
  instance configuration.
- The expected duration (Scan: 30 s – 5 min; Install: minutes to ~1 hour;
  maintenance window: until scheduled end).
- The expected side-effects (compliance delta for Scan; potential reboot +
  `InstalledPending` count for Install).
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (Install, association update to Install, baseline create/update, MW
  create/register-task), emit:
  `CONFIRM: About to <operation> on <instance-id or fleet-tag> in account
  <account> region <region>. This will <consequence, e.g. install patches
  and may reboot the host(s)>. Proceed? (yes/no)`.
- Capture pre-state for rollback: tag the AMI or run
  `aws ec2 create-create-snapshot --volume-id <root> --description
  "pre-patch $(date -u +%FT%TZ)"` for Install.
- Execute the CLI. Capture the `CommandId`.
- For long-running commands, poll
  `aws ssm get-command-invocation --command-id <id> --instance-id <id>`
  until `Status` is `Success` / `Failed` / `TimedOut` / `Cancelled`.
- For maintenance window task, capture the `WindowTaskId` and poll
  `describe-maintenance-window-executions`.

### Step 4: Post-verification — COMPLETED

After the operation finishes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `get-command-invocation` returns `Status: Success` (or the maintenance
   window execution `Status: COMPLETED`).
2. For Scan: re-fetch `describe-patch-states --instance-ids <id>` and
   verify the `OperationEndTime` is fresh. Surface the missing-count delta.
3. For Install: re-fetch `list-compliance-items` and verify
   `ComplianceStatus: COMPLIANT` (or surface remaining
   `NON_COMPLIANT` items by severity).
4. Verify the host came back online after any reboot:
   `describe-instance-information` `PingStatus: Active` AND
   `ec2 describe-instances` `State: running`.
5. For Windows `NoReboot=true` Installs: surface the
   `InstalledPending` count and the explicit next-reboot requirement.
6. Surface side-effects: changed services, applied patch list (from the
   command output's `InstalledPatches` field), reboot happened Y/N.
7. Plan follow-up: re-scan in 24 h to catch reverted patches; remove
   pre-patch snapshots after the verification window (e.g., 7 days).

If ANY verification fails, emit `VERDICT: ERROR` with the failure details
— do not claim COMPLETED.

## Output format (per operation)

```text
OPERATION: <scan | install | create-baseline | update-baseline | create-mw | register-mw-task>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <instance-id | tag:Patch Group,Values=<group> | baseline-id | window-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / poll command>
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
COMPLIANCE_DELTA: <before: missing X / after: missing Y>
REBOOT: <yes | no | deferred>
NOTES: <rate-control, snapshot, caveats, follow-ups>
```

### Worked example — Install on a single Linux host

```text
OPERATION: install
VERDICT: READY
TARGET: i-0abc123def456789a
PRE_CHECKS:
  - [PASS] i-0abc123def456789a PingStatus Active, LastPingDateTime 2 min ago
  - [PASS] IAM role AmazonSSMManagedInstanceCore-Role includes
    AmazonSSMManagedInstanceCore
  - [PASS] EC2 State running
  - [PASS] Free disk on / is 18 GB (>= 2 GB)
  - [PASS] Effective baseline pb-0aaa1234 (custom prod-linux-critical)
    via Patch Group tag "prod-linux-critical"
  - [PASS] Baseline ApprovalRules: Classification=Security,
    Severity=Critical+Important, ApproveAfterDays=3 — 14 patches qualify
  - [PASS] No concurrent command in flight
  - [PASS] Instance is in maintenance window mw-0aaa (cutoff in 95 min)
STEPS:
  1. CONFIRM: About to send-command AWS-RunPatchBaseline Operation=Install
     on i-0abc123def456789a in account 111111111111 region us-east-1.
     This will install up to 14 Security patches (Critical+Important) and
     MAY REBOOT the host if a kernel update is in scope. Proceed? (yes/no)
  2. aws ec2 create-snapshot --volume-id vol-0root123 \
       --description "pre-patch $(date -u +%FT%TZ)"
  3. aws ssm send-command \
       --instance-ids i-0abc123def456789a \
       --document-name "AWS-RunPatchBaseline" \
       --parameters '{"Operation":["Install"],"SnapshotIds":[""],"RebootOption":["NoReboot"]}' \
       --comment "Install Security/Critical+Important on prod host" \
       --output-s3-bucket-name audit-ssm-output \
       --output-s3-key-prefix patch-install/$(date -u +%Y/%m/%d)
  4. aws ssm get-command-invocation \
       --command-id <CommandId from step 3> \
       --instance-id i-0abc123def456789a
     (poll until Status is Success / Failed / TimedOut)
POST_VERIFY:
  - (pending execution)
COMPLIANCE_DELTA: (before: 14 missing / after: pending)
REBOOT: deferred (NoReboot=true; kernel patch will activate on next reboot,
  host is running stale kernel until then)
NOTES:
  - The host will report COMPLIANT only after the next reboot activates the
    kernel patch. Plan a reboot via maintenance window or ASG instance
    refresh within the next 7 days.
  - Re-scan in 24 h to catch any patches reverted by package-manager hooks.
  - Pre-patch snapshot snap-0prepatch123 retained for 7 days; delete after
    the verification window.
  - Rate-control: single-instance target — no --max-concurrency needed.
    For fleet Installs, add `--max-errors 0 --max-concurrency "10%"`.
```

### Worked example — Scan-only association missing patches

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
    (no Patch Group tag, no custom baseline association). Operator intent
    was "apply the prod-linux-critical baseline" — the instance is
    silently on the AWS default. Install would apply the default-baseline
    approved set, NOT the operator's prod-linux-critical rules.
  - [PASS] Maintenance window mw-0bbb has the instance as a target
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
COMPLIANCE_DELTA: (none)
REBOOT: (none)
NOTES:
  - Either tag the instance for the prod-linux-critical baseline:
      aws ec2 create-tags --resources i-0fedcba9876543210 \
        --tags Key="Patch Group",Value=prod-linux-critical
    then re-fetch get-patch-baseline-for-instance to confirm.
  - OR set pb-0aaa1234 as the regional default for AMAZON_LINUX_2:
      aws ssm set-default-patch-baseline \
        --baseline-id pb-0aaa1234 --operating-system AMAZON_LINUX_2
    (replaces AWS-AmazonLinux2DefaultPatchBaseline region-wide — review
    blast radius before applying.)
  - Re-run this skill after remediation; pre-checks will re-evaluate.
```

### Worked example — Maintenance window register-task

```text
OPERATION: register-mw-task
VERDICT: READY
TARGET: mw-0bbb (prod-patch-window, cron 0 02 ? * SAT *)
PRE_CHECKS:
  - [PASS] mw-0bbb exists, enabled, schedule valid (Saturdays 02:00 UTC,
    4 h duration, 1 h cutoff)
  - [PASS] Targets: Key=tag:"Patch Group",Values=prod-linux-critical →
    14 instances match
  - [PASS] Service role arn:aws:iam::111111111111:role/service-role/AmazonSSMAutomationRole
    trusts ssm.amazonaws.com
  - [PASS] Task parameters: Operation=Install, RebootOption=NoReboot
  - [PASS] Task invocation lambda/automation role attached
STEPS:
  1. CONFIRM: About to register-task-with-maintenance-window on mw-0bbb
     in account 111111111111 region us-east-1. This will run
     AWS-RunPatchBaseline Operation=Install on up to 14 instances tagged
     Patch Group=prod-linux-critical every Saturday 02:00 UTC. Rate
     control: max-concurrency 10%, max-errors 0. Proceed? (yes/no)
  2. aws ssm register-task-with-maintenance-window \
       --window-id mw-0bbb \
       --targets "Key=tag:Patch Group,Values=prod-linux-critical" \
       --task-arn "AWS-RunPatchBaseline" \
       --task-type RUN_COMMAND \
       --service-role-arn arn:aws:iam::111111111111:role/service-role/AmazonSSMAutomationRole \
       --task-invocation-parameters '{"RunCommand":{"DocumentVersion":"$DEFAULT","Parameters":{"Operation":["Install"],"RebootOption":["NoReboot"],"SnapshotIds":[""]}}}' \
       --max-concurrency "10%" --max-errors 0 \
       --priority 1 \
       --name "Install-Security-Patches"
  3. aws ssm describe-maintenance-window-tasks --window-id mw-0bbb
POST_VERIFY:
  - (pending next execution)
COMPLIANCE_DELTA: (will be reported after the next Saturday 02:00 UTC run)
REBOOT: deferred (NoReboot; kernel patches activate on next reboot)
NOTES:
  - Verify target membership weekly: instances drift in/out of the Patch
    Group tag.
  - First execution is the next Saturday 02:00 UTC. To run immediately for
    verification: aws ssm start-automation-execution or send a one-off
    send-command to a single instance.
```

## Anti-Patterns — NEVER do these things

- NEVER run `Operation=Install` without first dumping the effective
  baseline's `ApprovalRules.PatchRules[]` via `describe-patch-baseline`.
  A baseline with `ApproveAfterDays: 0` and broad classifications will
  install far more than the operator expects — including major-version
  package upgrades that break applications.

- NEVER assume `NoReboot=true` means "no reboot needed." It suppresses the
  Patch Manager-initiated reboot, but kernel patches on Linux and
  cumulative updates on Windows still require a reboot to activate. The
  host runs stale code until the next reboot; compliance will show
  `InstalledPending` until then.

- NEVER issue a fleet-wide `Operation=Install` via `send-command
  --instance-ids i-a,i-b,...,i-z` without `--max-errors 0
  --max-concurrency "10%"`. Without rate-control, every target reboots
  in parallel — a fleet-wide outage from a single bad patch.

- NEVER trust an association `Status: Success` as proof of patch
  compliance. A `Success` association with `Operation=Scan` reports
  green while leaving the host `NON_COMPLIANT` — the scan ran, the
  patches are still missing. Always cross-check
  `list-compliance-items` `ComplianceStatus`.

- NEVER tag instances with `patch group`, `PatchGroup`, or `patch-group`.
  The recognized tag key is `Patch Group` (space, capital G). Wrong-case
  tags silently fall back to the default baseline.

- NEVER create a custom patch baseline without either setting it as the
  regional default OR mapping a `Patch Group` tag to its name. A
  baseline that is neither is dead configuration — the operator thinks
  they have custom rules in effect, but instances use the default.

- NEVER delete an association as the first remediation step. Modify-then-
  test (`update-association` to change `Operation=Scan` to `Install`)
  preserves targeting and schedule; deleting loses the configuration
  context.

- NEVER rely on `describe-patch-baselines --filters Key=OWNER,Values=Self`
  to find the *effective* baseline for an instance. Use
  `get-patch-baseline-for-instance` — it resolves the regional default,
  the `Patch Group` tag, and any explicit association in priority order.

- NEVER evaluate patch compliance on an instance with `PingStatus:
  ConnectionLost` or `Inactive`. Downstream data is stale; reporting it
  produces noise. Restore coverage first, re-scan, then evaluate.

- NEVER assume `AmazonEC2RoleforSSM` (legacy) is equivalent to
  `AmazonSSMManagedInstanceCore` (modern). The legacy policy lacks
  several patch and inventory permissions and breaks Session Manager.
  Flag instances still on the legacy policy.

- NEVER run an Install in a private subnet without confirming the SSM VPC
  endpoints (`ssm`, `ssmmessages`, `ec2messages`) are present. Without
  them, the agent cannot return command output and the Install appears
  to hang.

- NEVER auto-execute `Operation=Install` during business hours without a
  maintenance window. Even `NoReboot=true` Installs restart services
  (httpd, nginx, docker) that can drop in-flight requests.

- NEVER use `--targets Key=InstanceIds,Values=*` or a tag-based wildcard
  for an Install without explicit operator confirmation. Always scope to
  a known `Patch Group` value or an explicit instance-id list.

- NEVER skip the free-disk check before Install. A full root volume
  causes the package manager to fail mid-Install, leaving the host in a
  broken state that requires manual rescue.

- NEVER assume Scan results are immediately visible. `describe-patch-states`
  and `list-compliance-items` are eventually consistent after a Scan
  (~30 s – 2 min). Re-poll before declaring the result.

- NEVER assume `AWS-RunPatchBaseline` is the same as `AWS-ApplyPatchBaseline`.
  `Apply` is the legacy Windows-only document; `Run` is the modern cross-
  OS document. New associations should always use `Run`.

- NEVER claim "fully patched" based on a single Scan. Re-scan in 24 h to
  catch reverted patches, package-manager hook rollbacks, and Windows
  cumulative-update supersession.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`send-command Operation=Install`, `update-association` to `Install`,
  `create/update-patch-baseline`, `set-default-patch-baseline`,
  `create/register-task-with-maintenance-window`), emit:
  `CONFIRM: About to <operation> on <target> in account <account> region
  <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT execute
  until the operator confirms.

- **Capture pre-state for rollback.** Before any Install:
  `aws ec2 create-snapshot --volume-id <root> --description "pre-patch
  $(date -u +%FT%TZ)"`. Patch Manager does NOT auto-snapshot. An AMI is
  even safer for fleet operations.

- **Always pass explicit `--instance-ids <id>` or a scoped
  `--targets Key=tag:"Patch Group",Values=<group>`** for Installs.
  Wildcards and `Values=*` are fleet-outage vectors.

- **Rate-control is MANDATORY for fleet Installs.** Set
  `--max-errors 0` (halt on first error) and `--max-concurrency "10%"`
  (or `"1"` for high-risk patches). Halting on first error contains a
  bad patch to the first batch.

- **Verify target membership before the maintenance window opens.**
  `describe-maintenance-window-targets --window-id <id>` — empty targets
  means the window will no-op.

- **Verify the baseline scope before the first Install on a new custom
  baseline.** Run a Scan on a single instance; review the
  `InstalledPendingCount` and `MissingCount` deltas before fleet-wide
  Install.

- **Prefer reversible changes.** For baseline updates, increment the
  baseline version (`--baseline-version`) so the previous version is
  preserved in baseline history. For association updates, snapshot
  `describe-association --association-id <id>` first.

- **Test patches on a single instance before fleet rollout.** Use a
  "canary" `Patch Group` (e.g., `prod-linux-canary`) targeting one or
  two hosts; observe for 24-48 h; then promote to the production group.

## Recent AWS features (2024-2026)

- **SSM Quick Setup patching (2024-2025):** Quick Setup now provides
  pre-configured patching configurations deployable via CloudFormation
  across an OU or entire organization. Operators should verify that Quick
  Setup-managed baselines and associations are not locally overridden, and
  that Quick Setup's "Patch Manager" configuration is the source of truth.

- **Patch Manager for macOS (2024-2025):** EC2 Mac hosts now support
  Patch Manager via `AWS-macOSDefaultPatchBaseline`. macOS patching uses
  `softwareupdate` under the hood and may require the
  `AWS-UpdateMacOS` automation document for major-version upgrades. The
  SSM Agent on macOS requires host-level registration via Mac dedicated
  host setup.

- **Amazon Linux 2023 patch baseline enhancements (2024):** Dedicated
  baseline `AWS-AmazonLinux2023DefaultPatchBaseline` with dnf-based
  package manager integration. Operators migrating from Amazon Linux 2
  must update their custom baselines to OS = `AMAZON_LINUX_2023` — the
  AmazonLinux2 baseline does NOT apply to AL2023.

- **Ubuntu 24.04 LTS baseline (2024-2025):** Baseline
  `AWS-UbuntuDefaultPatchBaseline` extended for Ubuntu 24.04 with snap
  patch hold support via `Snapshot Ids` in baseline rules.

- **SSM Document versioning (2024):** SSM Documents support explicit
  versioning. Production associations should reference a specific
  `$DEFAULT` or version, not `$LATEST`, to prevent implicit patch-rule
  drift.

- **Patch baseline as a CloudFormation resource (2024-2025):**
  `AWS::SSM::PatchBaseline` and `AWS::SSM::PatchBaselineAttachment` are
  GA, enabling baseline-as-code. Operators should verify that Cloud-
  Formation-managed baselines are not locally edited (drift detection).

- **Compliance reporting via AWS Config (2024):** SSM patch compliance
  now publishes richer items to AWS Config (`AWS::SSM::PatchCompliance`),
  enabling cross-account aggregation via Config aggregation. Operators
  should verify that the Config aggregator includes the
  `AWS::SSM::PatchCompliance` resource type.

## Domain

AWS CloudOps / Systems Manager Patch Manager Operations & Compliance.

## AWS documentation

- **AWS Systems Manager User Guide** — https://docs.aws.amazon.com/systems-manager/latest/userguide/what-is-systems-manager.html
- **AWS Systems Manager Patch Manager** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-patch.html
- **Working with patch baselines** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-patch-baselines.html
- **About the AWS-RunPatchBaseline document** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-patch-runbaseline.html
- **Working with maintenance windows** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-maintenance.html
- **Patch compliance** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-compliance.html
- **AWS Systems Manager Quick Setup** — https://docs.aws.amazon.com/systems-manager/latest/userguide/quick-setup.html
- **AWS CLI Command Reference: ssm** — https://docs.aws.amazon.com/cli/latest/reference/ssm/
