# Patch Baseline Design Reference

Load this reference when authoring or modifying a custom patch baseline.
The patterns below cover the canonical approval-rule shapes, the OS-by-OS
product taxonomy, the `Patch Group` targeting model, and the maintenance-
window task invocation contract.

## Decision tree — baseline archetype

| Workload profile | Archetype | ApprovalRules shape | Reboot strategy |
|---|---|---|---|
| Internet-facing, regulated (PCI/HIPAA/SOC2) | `prod-critical` | `Classification=Security`, `Severity=Critical+Important`, `ApproveAfterDays=3` | Maintenance window + canary; `NoReboot=true` with explicit next-reboot |
| Internal production, low-risk tolerance | `prod-standard` | `Classification=Security`, `Severity=Critical+Important+Medium`, `ApproveAfterDays=7` | Maintenance window; reboot allowed inside window |
| Staging / pre-prod | `stage-early` | `Classification=Security+Bugfix`, all severities, `ApproveAfterDays=0` | Reboot allowed anytime; canary for prod |
| Dev / sandbox | `dev-latest` | All classifications, all severities, `ApproveAfterDays=0` | Reboot anytime; ring-0 for prod |
| Locked / frozen (change freeze) | `frozen` | Empty rules + `RejectedPatches` for freeze block; relies on manual `Install` only | No auto-Install |
| Compliance-drift ring-fence | `compliance-only` | `Classification=Security`, `Severity=Critical`, `ApproveAfterDays=0`, explicit `RejectedPatches` for non-compliant drivers | Maintenance window only |

## Approval rule anatomy

```json
{
  "OperatingSystem": "AMAZON_LINUX_2",
  "Name": "prod-linux-critical",
  "ApprovalRules": {
    "PatchRules": [
      {
        "PatchFilterGroup": [
          {"Key": "CLASSIFICATION", "Values": ["Security"]},
          {"Key": "SEVERITY", "Values": ["Critical", "Important"]}
        ],
        "ApproveAfterDays": 3,
        "ApproveUntilDate": "",
        "EnableNonSecurity": false,
        "ComplianceLevel": "CRITICAL"
      }
    ]
  },
  "ApprovedPatches": [],
  "RejectedPatches": ["kernel-4.14.348-*"],
  "RejectedPatchesAction": "BLOCK",
  "GlobalFilters": {
    "PatchFilters": [
      {"Key": "ARCHITECTURE", "Values": ["x86_64", "aarch64"]}
    ]
  },
  "Sources": []
}
```

### Field semantics (the AND/OR contract)

- **Within a single `PatchFilterGroup` entry:** filters are AND-ed. A patch
  must match every `{Key, Values}` pair to qualify for that rule.
- **Across `PatchRules[]` entries:** rules are OR-ed. A patch matching ANY
  rule qualifies.
- **`ApproveAfterDays` vs `ApproveUntilDate`:** at most one may be set per
  rule. `ApproveAfterDays: N` approves N days after vendor release.
  `ApproveUntilDate: "2026-09-01"` approves patches released before that
  date — useful for change-freeze windows.
- **`EnableNonSecurity`:** when `true`, non-Security updates (Bugfix,
  Enhancement) on the same package versions as approved Security patches
  are also installed. Default `false`. Misuse pulls in unexpected
  major-version bumps.
- **`ComplianceLevel`:** the severity reported in
  `list-compliance-items` when this rule's patches are missing. Set
  independently of the upstream CVE severity — operators can declare
  "any Security missing = CRITICAL" by setting `ComplianceLevel: CRITICAL`
  on a rule with `Severity=[Critical, Important, Medium, Low]`.
- **`RejectedPatches` + `RejectedPatchesAction`:** `BLOCK` (default)
  refuses to install the patch even if another rule would. `ALLOW_AS_DEPENDENCY`
  lets the package in only if another approved patch requires it.

### Global filters vs rule-level filters

- `GlobalFilters.PatchFilters[]` are applied to EVERY rule in the baseline.
  Use for cross-cutting constraints (architecture, repo).
- Rule-level `PatchFilterGroup` is scoped to that rule only.

## OS-by-OS product and classification taxonomy

| Operating system (API enum) | `Product` values | `CLASSIFICATION` values | Notes |
|---|---|---|---|
| `AMAZON_LINUX_2` | `AmazonLinux2`, `AmazonLinux2Extras` | `Security`, `Bugfix`, `Enhancement`, `Recommended`, `Newpackage` | Extras repo enabled separately |
| `AMAZON_LINUX_2023` | `AmazonLinux2023` | `Security`, `Bugfix`, `Enhancement`, `Newpackage` | dnf-based; `Recommended` not supported |
| `UBUNTU_20_04` / `UBUNTU_22_04` / `UBUNTU_24_04` | `Ubuntu20.04`, `Ubuntu22.04`, `Ubuntu24.04` | `Security`, `Recommended`, `Newpackage` | snap holds via `Snapshot Ids` |
| `REDHAT_ENTERPRISE_LINUX_7` / `_8` / `_9` | `RedhatEnterpriseLinux7` etc. | `Security`, `Bugfix`, `Enhancement`, `Recommended`, `Newpackage` | RHEL 9 uses dnf |
| `SUSE_15` | `Suse15` | `Security`, `Recommended`, `Newpackage`, `Other` | zypper-based |
| `WINDOWS_SERVER_2012` / `_2012R2` / `_2016` / `_2019` / `_2022` | `WindowsServer2012R2` etc. | `Security`, `CriticalUpdates`, `UpdateRollups`, `ServicePacks`, `Updates`, `DefinitionUpdates`, `Drivers`, `FeaturePacks` | MS Office & .NET are separate Products |
| `MACOS` | `macOS12.5`, `macOS13`, `macOS14` | `Security`, `Recommended`, `Newpackage`, `Other` | softwareupdate-based |

The API enum is **case-sensitive and underscore-bearing** (`AMAZON_LINUX_2`,
not `AmazonLinux2`). Product values use dotted versions
(`Ubuntu22.04`). Mis-matching the enum creates a baseline that validates
but does not match any patch.

## Patch Group targeting model

```text
[ EC2 / mi-* instance ]
        |
        | tag: "Patch Group" = "prod-linux-critical"
        v
[ describe-patch-baselines: Name == "prod-linux-critical" ]
        |
        v
[ that baseline governs Scan / Install for this instance ]
```

Rules:

- The tag key MUST be exactly `Patch Group` (space, capital G).
- The tag value MUST equal the baseline's `Name` field (NOT its `BaselineId`
  and NOT its alias).
- The match is exact and case-sensitive.
- If multiple baselines in the same region/OS share a Name, the lexicographically-
  first BaselineId wins. Avoid duplicate names.
- If no `Patch Group` tag matches AND no custom baseline is set as regional
  default, the AWS-owned default for that OS applies.

## Setting a baseline as regional default

```bash
aws ssm set-default-patch-baseline \
  --baseline-id pb-0aaa1234abcdef \
  --operating-system AMAZON_LINUX_2
```

- This REPLACES the AWS-managed default for that OS in that region. The
  AWS default (`AWS-AmazonLinux2DefaultPatchBaseline`) is preserved as a
  baseline object but is no longer the default.
- Blast radius: every instance of that OS in the region without a
  `Patch Group` tag immediately switches to this baseline. Surface this
  to the operator as a pre-check finding.
- To revert: `set-default-patch-baseline --baseline-id
  arn:aws:ssm:<region>::patchbaseline/<AWS-default-arn>` for that OS.

## Maintenance window task invocation contract

```text
register-task-with-maintenance-window
  --window-id mw-0bbb
  --targets "Key=tag:Patch Group,Values=prod-linux-critical"
  --task-arn "AWS-RunPatchBaseline"
  --task-type RUN_COMMAND
  --service-role-arn arn:aws:iam::<acct>:role/service-role/AmazonSSMAutomationRole
  --task-invocation-parameters '{
    "RunCommand": {
      "DocumentVersion": "$DEFAULT",
      "Parameters": {
        "Operation": ["Install"],
        "SnapshotIds": [""],
        "RebootOption": ["NoReboot"],
        "AssociationIds": [""],
        "BaselineOverride": ["arn:aws:ssm:<region>:<acct>:patchbaseline/pb-0aaa1234"]
      },
      "CloudWatchOutputEnabled": true,
      "CloudWatchLogGroupName": "/aws/ssm/patch-install",
      "S3BucketName": "audit-ssm-output",
      "S3KeyPrefix": "patch-install/<window-id>/<execution-id>"
    }
  }'
  --max-concurrency "10%"
  --max-errors 0
  --priority 1
  --name "Install-Security-Patches"
```

### Important parameters

- `--service-role-arn` MUST trust `ssm.amazonaws.com` and have
  `AmazonSSMAutomationRole` or equivalent. The instance role is separate
  (the instance's own profile runs the document).
- `--max-concurrency "10%"` and `--max-errors 0` are the safe defaults.
  Hardcode these; never inherit the legacy default of unbounded.
- `BaselineOverride` lets the task run against a baseline that differs
  from the instance's effective baseline — useful for "test new baseline
  on the same fleet without retagging."
- `CloudWatchOutputEnabled` + `CloudWatchLogGroupName` route command
  output to CloudWatch Logs for centralized audit. Pair with KMS
  encryption on the log group for compliance frameworks.

## Compliance reporting sources (and their eventual consistency)

| Source | API | What it reports | Lag |
|---|---|---|---|
| Last scan summary | `describe-patch-states --instance-ids <id>` | Per-instance `InstalledPendingCount`, `MissingCount`, `FailedCount`, `OperationEndTime` | Updates within ~30 s of Scan completion |
| Per-patch compliance items | `list-compliance-items --resource-ids <id>` | Per-patch rows with `Status` (COMPLIANT / NON_COMPLIANT / INSTALLED_PENDING) and `Severity` | ~30 s – 2 min |
| Baseline-wide summary | `describe-patch-group-states --patch-groups <name>` | Aggregate counts for a `Patch Group` | ~1 min |
| AWS Config aggregator | `AWS::SSM::PatchCompliance` resource type | Cross-account / cross-region aggregation | Config's normal 5-10 min lag |

Never report a fresh "compliance OK" based on a single fetch — re-poll
once after 2 minutes to confirm convergence.

## Common failure modes (root-cause cheat sheet)

| Symptom | Likely root cause | Diagnostic |
|---|---|---|
| Scan returns 0 findings on a host you know is stale | Wrong effective baseline (no `Patch Group` tag, AWS default in effect) | `get-patch-baseline-for-instance` |
| Association `Success` but compliance still `NON_COMPLIANT` | Association runs `Operation=Scan` not `Install` | `describe-association --association-id <id>` |
| Install completes, compliance still `NON_COMPLIANT` | Patches installed but `InstalledPending` (Windows), or kernel patch needs reboot (Linux) | `list-compliance-items` look for `INSTALLED_PENDING` |
| `TargetNotConnected` on `send-command` | Instance offline, agent stopped, or per-instance concurrency reached (1 default) | `describe-instance-information`, `list-commands --filters Status=InProgress` |
| Patch baseline `create-patch-baseline` succeeds but does nothing | Not set as default AND no `Patch Group` tag matches the baseline Name | `get-patch-baseline-for-instance` |
| Install runs but does not reboot despite kernel update | `NoReboot=true` was passed (or association default) | `describe-association` `RebootOption` |
| Fleet-wide Install took down all hosts concurrently | Missing `--max-concurrency` / `--max-errors` | Always set rate-control on `send-command` and on MW task |
| `InvalidPermission` on `send-command` | Caller role lacks `ssm:SendCommand` on the document or instance ARN | IAM policy simulator |
| Maintenance window no-ops | `--targets` resolves to empty at execution time | `describe-maintenance-window-targets --window-id <id>` |
| Custom baseline `ApprovalRules` produce "no patches approved" | Filter combination (AND-ed) excludes everything; or `Product` value mistyped | `describe-patch-baseline` + dry-run Scan on a single instance |
| AL2 baseline applied to AL2023 instance | OS enum mismatch (AL2 rules don't match AL2023 products) | `get-patch-baseline-for-instance` shows `AMAZON_LINUX_2023` baseline expected |
