# Advanced Patterns — ssm-patch-operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Cost/time baselines (2026)

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
