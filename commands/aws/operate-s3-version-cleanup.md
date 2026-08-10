---
description: Operate S3 version cleanup for cost optimization and compliance — NoncurrentVersionExpiration, NoncurrentVersionTransition, NewerNoncurrentVersions, AbortIncompleteMultipartUpload lifecycle rules (with read-merge-PUT pattern to avoid silent replacement), S3 Batch Operations for immediate version delete, Object Lock Compliance/Governance mode and per-object legal-hold handling, S3 Storage Lens impact estimation, and post-apply verification.
nl_triggers:
  - "clean up S3 versions"
  - "S3 noncurrent versions cost"
  - "configure S3 lifecycle NoncurrentVersionExpiration"
  - "S3 version cleanup"
  - "S3 Object Lock retention"
  - "S3 legal hold"
  - "S3 Batch Operations delete versions"
  - "S3 cost optimization versions"
  - "S3 Storage Lens noncurrent"
  - "abort multipart upload S3"
  - "S3 NewerNoncurrentVersions"
  - "versioned bucket cleanup"
  - "S3 lifecycle configuration"
  - "Glacier Instant Retrieval noncurrent"
routes_to: s3-version-cleanup-operator
---

# /aws:operate-s3-version-cleanup

Activate the `s3-version-cleanup-operator` skill and plan/execute an S3
version cleanup operation with deterministic pre-checks, CONFIRM gate,
and post-verification including the read-merge-PUT pattern.

## What it does

Reads a bucket configuration plus the intended operation and applies
the priority-ordered pre-check sequence:

1. Pre-flight bucket metadata gate — versioning state (Enabled vs
   Suspended vs NeverEnabled), MFADelete flag, Object Lock mode
   (Compliance vs Governance), per-object legal holds.
2. Pre-check gate — BLOCKED if any check fails (Object Lock Compliance
   retention blocks delete, legal hold ON objects in scope, versioning
   never enabled, MFADelete required, lifecycle rule conflict).
3. READY — emit the exact CLI/JSON sequence with all flags populated,
   the read-merge-PUT pattern for lifecycle changes, the S3 Batch
   Operations manifest spec, and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state for rollback,
   execute the CLI (lifecycle PUT or Batch Operations create-job),
   poll until the operation completes.
5. Post-verification — lifecycle config preserved + new rules applied;
   Storage Lens NoncurrentVersionCount and
   NoncurrentVersionStorageBytes dropping; Cost Explorer trend down;
   Object Lock retention respected; COMPLETED only if ALL post-
   verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <configure-lifecycle | batch-delete-versions | estimate-savings | audit-versions>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <bucket-name>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait/poll command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ESTIMATED_SAVINGS: <$X/month>
NOTES: <compliance caveats, Object Lock implications, cleanup timeline>
```

## When to invoke

Paste a bucket configuration plus the intended operation, or just
describe the scenario and ask any of:

- "clean up noncurrent versions on this bucket"
- "configure lifecycle to expire old versions"
- "how much can I save with version cleanup?"
- "set up NoncurrentVersionExpiration"
- "is Object Lock blocking my cleanup?"
- "delete 2M versions via Batch Operations"

A bare bucket name + any cleanup verb ("clean up this versioned
bucket", "audit noncurrent versions") also routes here via the
orchestrator.

## Inputs

- Bucket configuration (`get-bucket-versioning`,
  `get-bucket-lifecycle-configuration`,
  `get-object-lock-configuration`, `get-bucket-encryption` JSON).
- S3 Storage Lens dimensions: `NoncurrentVersionCount`,
  `NoncurrentVersionStorageBytes`, `BucketSizeBytes` by storage class.
- The intended operation: `configure-lifecycle`,
  `batch-delete-versions`, `estimate-savings`, `audit-versions`.
- For configure-lifecycle: the new rule pattern (Pattern 1: 3-rule
  cleanup with history; Pattern 2: hard expire; Pattern 3: Object
  Lock tier-after-retention; Pattern 4: abort multipart; Pattern 5:
  Intelligent-Tiering).
- For batch-delete-versions: S3 Inventory manifest ARN + prefix, or
  `list-object-versions` output for small buckets.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI/JSON sequence (with the read-merge-PUT
  pattern for lifecycle changes), expected timeline, estimated
  monthly savings, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the
  observed Storage Lens delta, Cost Explorer trend, and the
  preserved-rules confirmation.
- For BLOCKED: the specific failure reason (Object Lock Compliance
  retention, legal hold ON objects, versioning state, MFADelete,
  lifecycle rule conflict) and the alternative path (lifecycle
  transition for Compliance-mode buckets; release legal hold for
  held objects).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for S3 version cleanup).
- `/aws:audit-s3-bucket-policy` for the broader bucket security
  posture — bucket policies, Block Public Access, KMS encryption.
- `/aws:audit-backup-plan` for the AWS Backup plan side — AWS Backup
  complements S3 version cleanup with cross-region vault copies for
  DR.
