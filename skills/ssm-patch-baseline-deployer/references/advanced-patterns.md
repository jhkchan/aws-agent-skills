# Advanced Patterns — SSM Patch Baseline Deployer

Step-0 expert behaviors and recent-feature notes moved from SKILL.md. Load on demand.

## Step 0: Expert knowledge — non-obvious Patch Manager behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational Patch Manager
experience. Each changes a plan if ignored:

- **The default AWS patch baseline auto-approves all patches
  immediately.** Every supported OS has an AWS-managed baseline with
  `ApproveAfterDays: 0`. Custom baselines override this for specific
  patch groups. Registering a custom baseline as the default for an OS
  replaces the AWS baseline for ALL instances, not just tagged ones.

- **`ApproveAfterDays: 0` means immediate approval.** Patches are
  approved the day they are released by the OS vendor. This is the
  most aggressive posture — suitable for dev/staging, risky for
  production where a patch reboot can cause an outage.

- **`ComplianceLevel` controls the dashboard severity, not the patch
  severity.** A `ComplianceLevel: CRITICAL` on an approval rule means
  missing patches show as CRITICAL in the compliance dashboard, even
  if the patch itself is a `Low` severity update. Set the compliance
  level based on your operational urgency, not the vendor severity.

- **Patch filters are AND-combined within a rule.** A rule with
  classification `Security` and severity `Critical` matches patches that
  are BOTH security AND critical. Multiple `PatchFilters` entries with
  different products are OR-combined (patches from either product).

- **`AWS-RunPatchBaseline` is the only document that updates
  compliance.** Using `AWS-RunShellScript` to run `yum update` does
  not report to the compliance dashboard. The `Operation` parameter
  (`Scan` vs `Install`) controls whether patches are only scanned or
  also installed.

- **Patch groups are tag-key-based, not resource-based.** The
  `Patch Group` tag on an EC2 instance or managed instance is the only
  way Patch Manager discovers targets. There is no ARN-based targeting.

- **macOS patching (2024-2026) requires the SSM agent on macOS.**
  macOS instances managed by Jamf or MDM do not automatically report
  to SSM. The instance must have the SSM agent installed and the
  instance profile with `AmazonSSMManagedInstanceCore`.

- **Amazon Linux 2023 uses a different package manager (dnf).** The
  patch baseline product is `Amazon Linux 2023` (not `Amazon Linux 2`).
  Using the AL2 product filter on an AL2023 baseline matches zero
  patches — the most common AL2023 patching mistake.

- **Custom repositories (2024-2026).** Patch Manager can patch from
  custom repositories defined in the baseline via `Sources`. This is
  used for air-gapped environments or when pulling from a local mirror.
  The `Name` in `Sources` must match a configured repository on the
  instance.

- **Rejected patches block installation.** `RejectedPatches` with
  `BLOCK_AS_PENDING` (default) prevents a patch from installing even if
  it matches an approval rule. `ALLOW_AS_DEPENDENCY` permits it only if
  another approved patch requires it as a dependency.

- **Maintenance window task `MaxConcurrency` and `MaxErrors`.** These
  control how many instances patch simultaneously. A `MaxConcurrency`
  of `10%` means 10% of targets patch at once; the rest wait.
  `MaxErrors` of `3` stops the task after 3 failures. Set these
  conservatively for production to avoid mass reboots.
## Recent AWS features 2024-2026 (moved from SKILL.md)

- **SSM Patch Manager for macOS (2024-2025):** macOS is now a supported
  operating system for Patch Manager. Requires the SSM agent on macOS
  instances (not managed by Jamf/MDM-only). Supports `Scan` and
  `Install` operations via `AWS-RunPatchBaseline`.
- **Amazon Linux 2023 patch baseline (2024-2025):** AL2023 uses `dnf`
  as its package manager. The product filter is `Amazon Linux 2023`
  (not `Amazon Linux 2`). The most common AL2023 patching mistake is
  reusing AL2 baselines, which match zero patches.
- **Patch Baseline with custom repositories (2024-2025):** the `Sources`
  parameter on `create-patch-baseline` allows defining custom package
  repositories (yum/dnf/apt) for air-gapped or mirrored environments.
  The `Configuration` field accepts the full repo file content.
- **Patch Manager compliance dashboard enhancements (2024-2026):**
  the compliance dashboard now aggregates patch state across accounts
  via Organizations, with per-OU and per-baseline filtering. Compliance
  severity is now configurable per approval rule (not just per baseline).
- **Maintenance window task `CloudWatchOutputConfig` (2024-2025):**
  task output can now be streamed to CloudWatch Logs directly from the
  maintenance window task registration, simplifying audit without
  S3 bucket setup.
- **`AWS-ApplyPatchBaseline` for Windows offline patching (2024-2025):**
  a new document for Windows that applies patches from a pre-staged
  offline catalog — useful for air-gapped Windows Server fleets.
- **Rocky Linux 9 and AlmaLinux 9 support (2025-2026):** both are now
  first-class supported operating systems with product-specific patch
  filters, reducing reliance on the RHEL-compatible baseline workaround.
