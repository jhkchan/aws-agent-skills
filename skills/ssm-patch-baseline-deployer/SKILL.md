---
name: ssm-patch-baseline-deployer
description: Provisions SSM Patch Baselines with secure patch-management defaults — baseline creation (OS, product, classification, severity), approval rules (auto-approve after N days, compliance level), patch groups (tag-based targeting), default vs custom baseline selection, maintenance window integration, and custom repositories for Amazon Linux 2023, RHEL, Ubuntu, Windows, macOS. Runs pre-checks (OS validity, product-OS matching, Patch Group tag key, instance role AmazonSSMManagedInstanceCore, IAM permissions, maintenance window task document), emits create-patch-baseline, register-patch-baseline -for-patch-group, register-task-with-maintenance-window CLIs behind a CONFIRM gate, verifies via describe-patch-baseline. Emits READY_TO_DEPLOY | PREREQUISITES_MISSING. Use when creating patch baselines, configuring approval rules, targeting patch groups, or integrating with maintenance windows.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws ssm create-patch-baseline, update-patch-baseline, register-patch-baseline-for-patch-group, describe-patch-baseline, describe-instance-patch-states, register-target-with-maintenance-window, register-task-with-maintenance-window (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Management
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: ssm, patch-baseline, management, patch-manager, maintenance-window, deploy, compliance, os-patching
  dependencies: aws-orchestrator
  keywords: SSM Patch Manager, Patch Baseline, patch baseline, approval rule, auto-approve, compliance level, patch group, tag-based targeting, maintenance window, operating system, Amazon Linux 2023, macOS patching, Windows Server, Ubuntu, RHEL, custom repository, SSM, Systems Manager, patch compliance, AmazonSSMManagedInstanceCore
  when_to_use: Creating or updating an SSM Patch Baseline (approval rules, operating system, classification, severity), registering a patch group for tag-based targeting, setting default vs custom baseline selection, integrating a patch baseline with a maintenance window (register targets and tasks), or configuring custom repositories for Amazon Linux 2023, RHEL, Ubuntu, Windows, or macOS patching.
  activation_triggers: create patch baseline, provision SSM patch baseline, deploy patch baseline, approval rule patching, auto-approve patches, patch group, register patch baseline, maintenance window patching, Amazon Linux 2023 patches, macOS patching SSM, Windows Server patch baseline, Ubuntu patch baseline, RHEL patch baseline, custom repository patching, patch compliance severity, ssm create-patch-baseline, register-patch-baseline-for-patch-group, default patch baseline
  invocation_schema: 'Input: either (a) a patch baseline deployment intent (create or update) with target operating system, approval rules (classification, severity, auto-approve days, compliance level), patch group, and optional maintenance window integration; OR (b) a baseline ID for live-account update or validation. Output: deterministic BASELINE/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY_TO_DEPLOY, PREREQUISITES_MISSING.'
---

# SSM Patch Baseline Deployer

## What this skill does

Provisions SSM Patch Baselines with secure patch-management defaults —
correct operating system selection, approval rules with compliance
severity, tag-based patch group targeting, and maintenance window
integration. Enforces approval rules that auto-approve critical and
security patches within a documented window, compliance severity levels
that surface unpatched instances in the compliance dashboard, patch
groups keyed by `Patch Group` tag, and maintenance window tasks that
reference the correct document (`AWS-RunPatchBaseline`) with the correct
parameters. Runs deterministic pre-checks before any state-changing
CLI, emits the exact `create-patch-baseline`,
`register-patch-baseline-for-patch-group`, and maintenance window
registration CLIs behind a CONFIRM gate, and verifies the deployment via
`describe-patch-baseline` and `describe-instance-patch-states`. Every
baseline plan surfaces the operating system, approval rule matrix, patch
group tag key, and the default-vs-custom baseline selection.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + pre-check priority order + baseline config matrix | Before any operation |
| **Mindset** | Why defaults matter; Patch Manager silent-failure modes; overwrite traps | Understanding the deployment model |
| **Pre-flight** | Baseline metadata gate — OS, approval rules, patch group tags, instance roles | Before executing any CLI |
| **Process** | Per-operation planning: create baseline, register patch group, maintenance window | When choosing which operation |
| **Common patterns** | Amazon Linux 2023 / Windows auto-approve / macOS / maintenance window boilerplate | Boilerplate lookup |
| **STRICT output contract** | Required BASELINE/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules that prevent common insecure patterns | Review before deploy |
| **Expert heuristic** | Choosing auto-approve delay (0 vs N days) per environment | Choosing approval strategy |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (unsupported OS, approval rule missing required fields, patch group tag key not `Patch Group`, instance profile missing AmazonSSMManagedInstanceCore, maintenance window not found, IAM permission missing, baseline name collision on create) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with full baseline config, wait for operator yes |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY_TO_DEPLOY):**

1. **Baseline name uniqueness** — `describe-patch-baselines` returns no
   custom baseline with the target name (for create) or matches exactly
   one (for update).
2. **Operating system support** — the `OperatingSystem` is one of
   `AMAZON_LINUX_2023`, `AMAZON_LINUX_2`, `AMAZON_LINUX`, `UBUNTU_22.04`,
   `UBUNTU_20.04`, `DEBIAN_11`, `DEBIAN_12`, `REDHAT_ENTERPRISE_LINUX_8`,
   `REDHAT_ENTERPRISE_LINUX_9`, `WINDOWS_SERVER`, `MACOS`, `SUSE`,
   `CENTOS_7`, `ORACLE_LINUX_8`, `ROCKY_LINUX_9`, `ALMA_LINUX_9`,
   `RASPBIAN`.
3. **Approval rule completeness** — each approval rule has
   `ApproveAfterDays` (0-100), `ComplianceLevel` (`CRITICAL`, `HIGH`,
   `MEDIUM`, `LOW`, `INFORMATIONAL`, `UNSPECIFIED`), and at least one
   `PatchFilter` (product, classification, severity).
4. **Approval rule product** — the product matches the OS (e.g.,
   `Amazon Linux 2023` for `AMAZON_LINUX_2023`, `Ubuntu2204` for
   `UBUNTU_22.04`). Mismatched product = zero patches matched.
5. **Patch filter classification** — classification values are valid for
   the OS (e.g., `Security`, `Bugfix`, `Enhancement`, `Recommended`,
   `Newpackage`). Invalid classifications silently match nothing.
6. **Patch filter severity** — severity values are valid for the OS
  (e.g., `Critical`, `Important`, `Medium`, `Low`). Windows uses
  Microsoft severity; Linux uses distro severity.
7. **Patch group tag key** — the tag key used for registration is
   exactly `Patch Group` (case-sensitive). AWS Patch Manager looks up
   instances by this tag key only.
8. **Patch group tag value format** — the tag value matches
   `[A-Za-z0-9:_-]{1,255}` and does not contain spaces or special
   characters.
9. **Instance role** — the SSM instance profile attached to target
   EC2/macOS instances includes `AmazonSSMManagedInstanceCore`
   (and `AmazonSSMPatchAssociation` for association execution).
10. **Maintenance window existence** — if maintenance window integration
    is requested, the window ID exists and is in the same account/region.
11. **Maintenance window task document** — the task document is
    `AWS-RunPatchBaseline` (or `AWS-ApplyPatchBaseline` for Windows
    offline patching). The `Operation` parameter is `Scan` or `Install`.
12. **Compliance level consistency** — the `ComplianceLevel` on approval
    rules is not `UNSPECIFIED` for production baselines (UNSPECIFIED =
    no compliance reporting).
13. **Rejected patches** — if `RejectedPatches` are listed, the
    `RejectedPatchesAction` is `BLOCK_AS_PENDING` (default) or
    `ALLOW_AS_DEPENDENCY`.
14. **IAM permissions** — the operator principal holds
    `ssm:CreatePatchBaseline`, `ssm:RegisterPatchBaselineForPatchGroup`,
    `ssm:RegisterTargetWithMaintenanceWindow`, and
    `ssm:RegisterTaskWithMaintenanceWindow` (as applicable).

**SSM Patch Manager limits (2026):**

- Patch baselines per account (default): 1000 (soft limit).
- Patch groups per account: 10000 (soft limit).
- Approval rules per baseline: 1 (operating-system level) — can contain
  multiple `PatchFilters` entries.
- Patch filters per approval rule: 1-100.
- Rejected patches per baseline: 1-1000.
- One patch group registration per baseline (default baseline per OS
  per account).
- Maintenance windows per account: 1000 (soft).

## Mindset

**One-line takeaway:** SSM Patch Manager silently matches zero patches
when approval rules are misconfigured. A baseline for `AMAZON_LINUX_2023`
with a product filter of `Amazon Linux 2` will deploy cleanly — but no
patches will ever be approved, and the compliance dashboard will show
every instance as compliant (zero missing patches). The skill enforces
product-OS matching at the pre-check gate.

Driven by three Patch Manager realities:

- **Approval rules match patches by product, classification, and
  severity.** If the product does not match the OS, zero patches match.
  If the classification is misspelled (`Security` vs `security`), zero
  patches match. The pre-flight gate verifies product-OS alignment and
  classification casing.

- **Patch groups are looked up by the `Patch Group` tag key.** The tag
  key is case-sensitive (`Patch Group`, not `patch-group`). Instances
  without the tag are never patched regardless of baseline registration.

- **Maintenance window tasks must use `AWS-RunPatchBaseline`.** Using
  `AWS-RunShellScript` or a custom document with patch parameters does
  not update the compliance dashboard. The skill verifies the document
  name on every maintenance window task.

## Pre-flight: patch baseline metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-patch-baselines` returns at most 50 per page
(via `--max-results`). Use `--next-token` to drain.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws ssm describe-patch-baselines --operating-system <os>
   --max-results 50` — confirm the baseline name does not collide (for
   create) or matches (for update).
2. `aws ssm describe-patch-baselines --operating-system <os>
   --filters Key=OWNER,Values=AWS` — check the default AWS baseline for
   the OS (to decide default-vs-custom).
3. `aws ec2 describe-instances --filters "Name=tag:Patch
   Group,Values=<patch-group>"` — confirm instances exist with the tag.
4. `aws iam list-instance-profiles` — confirm the target instance
   profile includes `AmazonSSMManagedInstanceCore`.
5. `aws ssm describe-maintenance-windows --window-id <id>` — for
   maintenance window integration, confirm the window exists.
6. `aws ssm describe-instance-patch-states --instance-ids <ids>` —
   baseline snapshot of current patch compliance.

**Malformed input:** if the baseline spec is missing required fields
(`Name`, `OperatingSystem`, or `ApprovalRules`), emit `VERDICT:
PREREQUISITES_MISSING` with `REASON: Baseline spec missing required
field — Name, OperatingSystem, or ApprovalRules. Cannot plan.` and
`REMEDIATION: Provide the full baseline configuration per
https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-create-baseline.html.`

| Attribute | Effect on operation |
|---|---|
| OS not in supported list | API rejects. PREREQUISITES_MISSING. |
| Product mismatched to OS | Zero patches matched. PREREQUISITES_MISSING. |
| Classification case-sensitive error | Zero patches matched. PREREQUISITES_MISSING. |
| Patch Group tag key not exact `Patch Group` | Instances never patched. PREREQUISITES_MISSING. |
| Instance role missing AmazonSSMManagedInstanceCore | SSM agent cannot register. PREREQUISITES_MISSING. |
| ComplianceLevel UNSPECIFIED | No compliance reporting. Flag in NOTES. |
| Maintenance window task not AWS-RunPatchBaseline | Compliance not updated. PREREQUISITES_MISSING. |
| ApproveAfterDays > 100 | API rejects. PREREQUISITES_MISSING. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious Patch Manager behaviors

Step-0 expert behaviors moved to [references/advanced-patterns.md](references/advanced-patterns.md) —
load when a plan hinges on default-baseline, approval-rule, or product-filter semantics.

### Step 1: Pre-check gate — PREREQUISITES_MISSING if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is
PREREQUISITES_MISSING with the failed checks enumerated in PRE_CHECKS.
Do NOT execute.

**For ALL operations:**
1. Baseline name is set, <= 128 chars, matches `[a-zA-Z0-9_.-]+`.
2. `OperatingSystem` is in the supported list.
3. IAM principal holds the relevant `ssm:` permission.

**For create-patch-baseline:**
4. Baseline name does not collide with an existing custom baseline.
5. `ApprovalRules` contains at least one `PatchRule`.
6. Each `PatchRule` has `ApproveAfterDays` in range 0-100.
7. Each `PatchRule` has `ComplianceLevel` set to a non-UNSPECIFIED value
   for production baselines.
8. Each `PatchRule.PatchFilterGroup` has product matching the OS.
9. Classification values are valid and correctly cased for the OS.
10. Severity values are valid for the OS.
11. `RejectedPatchesAction` is `BLOCK_AS_PENDING` or
    `ALLOW_AS_DEPENDENCY` (if rejected patches are listed).

**For register-patch-baseline-for-patch-group:**
12. The `Patch Group` tag key is used (case-sensitive).
13. The patch group value matches `[A-Za-z0-9:_-]{1,255}`.
14. The baseline ID exists and is for the correct OS.
15. At least one instance exists with the `Patch Group` tag value
    (checked via `ec2:describe-instances` if live).

**For register-target-with-maintenance-window:**
16. The maintenance window ID exists.
17. The `Targets` use the `Patch Group` tag or resource groups.
18. The `OwnerInformation` (if set) does not contain secrets.

**For register-task-with-maintenance-window:**
19. The task document is `AWS-RunPatchBaseline` (or
    `AWS-ApplyPatchBaseline` for Windows offline).
20. The `TaskParameters` include `Operation: Scan` or
    `Operation: Install`.
21. `MaxConcurrency` and `MaxErrors` are set (not omitted — defaults
    may be too aggressive for production).
22. The `CloudWatchOutputConfig` is enabled for audit logging.

### Step 2: READY_TO_DEPLOY — emit deployment plan

If all pre-checks pass, emit `VERDICT: READY_TO_DEPLOY` with the exact
CLI sequence and the CONFIRM gate. The plan includes:

- The exact `aws ssm create-patch-baseline` CLI with the full config
  (OperatingSystem, ApprovalRules, GlobalFilters, RejectedPatches,
  Sources, Description, Tags).
- The follow-up `register-patch-baseline-for-patch-group` CLI for each
  patch group.
- The follow-up `register-target-with-maintenance-window` CLI for
  maintenance window integration.
- The follow-up `register-task-with-maintenance-window` CLI with the
  `AWS-RunPatchBaseline` document.
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-patch-baseline`, `register-patch-baseline-for-patch-group`,
  `register-task-with-maintenance-window`), emit:
  `CONFIRM: About to <operation> <resource> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.
- Snapshot the current baseline config before modification:
  `aws ssm describe-patch-baseline --baseline-id <id> --output json
  > /tmp/<baseline-name>-backup-$(date +%s).json`.
- Execute the CLI with the full baseline config.

### Step 4: Post-verification

After the operation finishes, run post-verification:

1. `describe-patch-baseline --baseline-id <id>` returns the expected
   config (OperatingSystem, ApprovalRules, ComplianceLevel).
2. `describe-patch-groups --operating-system <os>` returns the patch
   group registered to this baseline.
3. For maintenance window: `describe-maintenance-window-tasks --window-id
   <id>` returns the `AWS-RunPatchBaseline` task with correct parameters.
4. Trigger a `Scan` operation on one target instance:
   `aws ssm send-command --document-name AWS-RunPatchBaseline
   --parameters '{"Operation":["Scan"]}' --targets <targets>`.
5. After scan completes: `describe-instance-patch-states --instance-ids
   <id>` returns the expected patch count and compliance status.

## Common baseline patterns (boilerplate)

Boilerplate patterns moved to [references/worked-examples.md](references/worked-examples.md):
AL2023, Windows, macOS baselines; maintenance-window Install task; air-gapped custom repository.

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
BASELINE: <baseline-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <baseline-name> (baseline-id: <id> for updates)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> <resource> in account <account> region <region>. This will <consequence>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
OPERATING_SYSTEM: AMAZON_LINUX_2023 | WINDOWS_SERVER | MACOS | UBUNTU_22.04 | ...
APPROVAL_RULES: <count> rule(s) (classifications: <list>, auto-approve: <N> days)
COMPLIANCE_LEVEL: CRITICAL | HIGH | MEDIUM | LOW
PATCH_GROUPS: <count> registered (values: <list>)
MAINTENANCE_WINDOW: <window-id> | NONE
INSTANCE_ROLE: AmazonSSMManagedInstanceCore | MISSING
NOTES: <patching posture, approval strategy, compliance caveats>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll create…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]`
  or `[FAIL]` and a specific reason for each failure.
- NEVER emit a plan with placeholder values in a READY_TO_DEPLOY plan —
  every field must be populated with actual values from the input.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation.
- NEVER claim success without verifying that the baseline was created
  (via `describe-patch-baseline`).
- NEVER put-update a baseline without snapshotting the existing config
  first — updates to `ApprovalRules` overwrite silently.
- NEVER silently allow a maintenance window task with a non-
  `AWS-RunPatchBaseline` document — block it with a [FAIL] pre-check row.

### Perfect example output

```text
BASELINE: al2023-prod-security
VERDICT: READY_TO_DEPLOY
TARGET: al2023-prod-security
PRE_CHECKS:
  - [PASS] Baseline name unique (no collision in describe-patch-baselines)
  - [PASS] Operating System: AMAZON_LINUX_2023 is supported
  - [PASS] Product filter Amazon Linux 2023 matches OS
  - [PASS] Classification Security, Bugfix are valid for AL2023
  - [PASS] Severity Critical, Important are valid
  - [PASS] ApproveAfterDays: 7 (in range 0-100)
  - [PASS] ComplianceLevel: CRITICAL (non-UNSPECIFIED)
  - [PASS] Patch Group tag key is "Patch Group" (case-sensitive)
  - [PASS] Instance role includes AmazonSSMManagedInstanceCore
  - [PASS] IAM principal holds ssm:CreatePatchBaseline
STEPS:
  1. CONFIRM: About to create-patch-baseline al2023-prod-security in account 111111111111 region us-east-1. This will CREATE a new baseline for AMAZON_LINUX_2023 with 7-day auto-approve on Security and Bugfix patches. Proceed? (yes/no)
  2. aws ssm create-patch-baseline --name al2023-prod-security --operating-system AMAZON_LINUX_2023 --approval-rules '{"PatchRules":[{"PatchFilterGroup":{"OperatingSystem":"AMAZON_LINUX_2023","PatchFilters":[{"Key":"PRODUCT","Values":["Amazon Linux 2023"]},{"Key":"CLASSIFICATION","Values":["Security","Bugfix"]},{"Key":"SEVERITY","Values":["Critical","Important"]}]},"ApproveAfterDays":7,"ComplianceLevel":"CRITICAL","EnableNonSecurity":true}]}' --tags '[{"Key":"Environment","Value":"prod"}]'
  3. aws ssm register-patch-baseline-for-patch-group --baseline-id <returned-id> --patch-group al2023-prod-web
POST_VERIFY:
  - (pending execution)
  - describe-patch-baseline returns OperatingSystem=AMAZON_LINUX_2023, ApproveAfterDays=7
  - describe-patch-groups returns al2023-prod-web registered to this baseline
OPERATING_SYSTEM: AMAZON_LINUX_2023
APPROVAL_RULES: 1 rule (classifications: Security, Bugfix; auto-approve: 7 days)
COMPLIANCE_LEVEL: CRITICAL
PATCH_GROUPS: 1 (al2023-prod-web)
MAINTENANCE_WINDOW: NONE
INSTANCE_ROLE: AmazonSSMManagedInstanceCore
NOTES:
  - ApproveAfterDays 7 means patches are approved 7 days after vendor release — balances freshness with soak time.
  - EnableNonSecurity true also approves non-security updates matching the product filter.
  - Register a maintenance window task (AWS-RunPatchBaseline Operation=Install) to actually install patches.
```

## NEVER (top 5)

These are the highest-impact, most-frequent failure modes in SSM Patch
Baseline deployments. Violating any one of these is a security or
operational regression.

1. **NEVER create a baseline with a product filter that does not match
   the operating system.** An `AMAZON_LINUX_2023` baseline with a
   product of `Amazon Linux 2` matches zero patches — the compliance
   dashboard shows all instances as compliant when they are not. The
   pre-check gate verifies product-OS alignment.

2. **NEVER register a patch group without verifying the instance role
   includes `AmazonSSMManagedInstanceCore`.** Instances without the role
   cannot register with SSM, cannot be patched, and will silently appear
   as non-compliant with no actionable error. The pre-check gate
   verifies the role on at least one instance in the patch group.

3. **NEVER set `ComplianceLevel: UNSPECIFIED` on a production baseline.**
   UNSPECIFIED means missing patches do not appear in the compliance
   dashboard — you lose visibility into unpatched instances. Always use
   CRITICAL, HIGH, or MEDIUM for production.

4. **NEVER create a maintenance window task with a document other than
   `AWS-RunPatchBaseline` for patching.** Using `AWS-RunShellScript` to
   run `yum update` or `apt upgrade` does not report to the compliance
   dashboard. The skill verifies the document name on every patch task.

5. **NEVER register a custom baseline as the default for an OS without
   understanding it replaces the AWS baseline for ALL instances.** The
   default baseline applies to every instance of that OS in the account,
   not just tagged ones. Only set a custom baseline as default when you
   intend a fleet-wide override. Otherwise, register via patch groups.

## Expert heuristic: choosing auto-approve delay

The right `ApproveAfterDays` is a function of environment, risk
tolerance, and operational maturity — not a one-size-fits-all. The
heuristic below resolves the trade-off deterministically.

```
Environment / risk posture
   ├─ Production, regulated (PCI/HIPAA/SOC2)?
   │    └─ ApproveAfterDays: 3-7. Security patches soak 3-7 days in
   │         pre-prod before auto-approving in prod. Pair with a
   │         maintenance window for controlled installation windows.
   │
   ├─ Production, non-regulated?
   │    └─ ApproveAfterDays: 7-14. Longer soak time for stability.
   │         Critical security patches may need a separate rule with
   │         ApproveAfterDays: 0 for emergency response.
   │
   ├─ Staging / pre-prod?
   │    └─ ApproveAfterDays: 1-3. Short soak time — catch breakages
   │         before promoting to production.
   │
   └─ Development?
        └─ ApproveAfterDays: 0. Immediate approval — keep dev instances
             on the latest patches for testing compatibility.
```

**Decision rules:**
- Default to `ApproveAfterDays: 7` for production. It is the safest
  default that balances security urgency with operational stability.
- For critical security patches, consider a separate approval rule with
  `ApproveAfterDays: 0` and `ComplianceLevel: CRITICAL` — these are
  emergency patches that should not wait.
- Always pair `ApproveAfterDays` with a maintenance window. Without a
  maintenance window, patches are approved but never installed.
- `ComplianceLevel` should reflect operational urgency: CRITICAL for
  production security patches, HIGH for important patches, MEDIUM for
  the rest.
- For air-gapped environments, set `ApproveAfterDays: 0` (the mirror
  controls timing) and use custom `Sources` for the local repository.

ALWAYS emit `ComplianceLevel` as a non-UNSPECIFIED value for production
baselines. Without it, the compliance dashboard is blind to missing
patches.

## Recent AWS features (2024-2026)

2024-2026 feature notes (macOS Patch Manager, AL2023 dnf, Sources,
dashboard enhancements) moved to [references/advanced-patterns.md](references/advanced-patterns.md).

## AWS documentation

- **SSM Patch Manager Developer Guide** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-patch.html
- **Create a patch baseline** — https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-create-baseline.html
- **About patch groups** — https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-patch-patchgroups.html
- **Maintenance windows** — https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-maintenance.html
- **AWS-RunPatchBaseline document** — https://docs.aws.amazon.com/systems-manager/latest/userguide/patch-manager-ssm-documents.html
- **SSM CLI reference** — https://docs.aws.amazon.com/cli/latest/reference/ssm/

## References (load on demand)

- [references/baseline-config-and-approval-rules.md](references/baseline-config-and-approval-rules.md) — Canonical per-OS baseline configurations and approval-rule patterns.
- [references/patch-groups-and-maintenance-windows.md](references/patch-groups-and-maintenance-windows.md) — Patch group registration and maintenance-window integration detail.
- [references/worked-examples.md](references/worked-examples.md) — Full CLI boilerplate for each OS archetype (moved from Common baseline patterns).
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 expert Patch Manager behaviors and 2024-2026 feature notes (moved from SKILL.md).

## Domain

AWS CloudOps / Management & Governance — SSM Patch Baseline Provisioning.
