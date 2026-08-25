# S3 Version Cleanup Operator — Diagnostic and Pre-flight Commands

Pre-flight safety checks run before any remediation CLI, moved verbatim from SKILL.md.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-bucket-lifecycle-configuration`, `delete-objects`,
  `aws s3control create-job`, `put-bucket-versioning`), emit:
  `CONFIRM: About to <operation> on bucket <name> in account <account>
  region <region>. This will <consequence>. Estimated monthly savings:
  $<amount>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.

- **Capture pre-state for rollback.** Before any lifecycle change:
  `aws s3api get-bucket-lifecycle-configuration --bucket <name>
  --output json > /tmp/<name>-lifecycle-pre-$(date +%s).json`.
  Lifecycle state is not versioned — a wrong PUT silently replaces.

- **Verify versioning BEFORE cleanup.** `Status: Enabled` is the
  expected state. `Suspended` and never-enabled have different
  cleanup semantics.

- **Verify Object Lock BEFORE any delete.** `ObjectLockEnabled:
  Enabled` with `DefaultRetention.Mode: COMPLIANCE` blocks in-retention
  deletion irrevocably. Governance mode allows bypass with
  `s3:BypassGovernanceRetention`.

- **Verify legal holds BEFORE Batch Operations.** Sample the manifest
  with `get-object-legal-hold` to ensure no `LegalHold: ON` objects
  are in scope.

- **Verify existing lifecycle rules BEFORE PUT.** Read via
  `get-bucket-lifecycle-configuration`. Merge new rules into the
  existing config; never PUT new rules alone.

- **Plan the cleanup timeline BEFORE promising savings.** Lifecycle
  rules apply within 24 hours of eligibility. For immediate cleanup,
  use Batch Operations (separate operation, separate cost).

- **Verify the rule prefix BEFORE PUT.** A rule with `prefix: ""`
  applies to ALL objects in the bucket. A rule with `prefix: logs/`
  applies only to objects under `logs/`. Verify the prefix matches
  intent — too narrow misses versions, too broad affects unintended
  objects.

