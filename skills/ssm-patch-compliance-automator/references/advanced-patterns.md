# Advanced Patterns — SSM Patch Compliance Automator

Expert-knowledge deep dives and recent-feature notes moved from SKILL.md. Load on demand.

## Step 0: Expert knowledge — non-obvious Patch Manager behaviors (moved from SKILL.md)

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
## Recent AWS features 2024-2026 (moved from SKILL.md)

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
## Expert heuristic: patch-window blast radius (moved from SKILL.md)

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
