# Diagnostic Commands — s3-lifecycle-optimizer

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Pre-flight: bucket metadata gate

**Pagination:** `list-objects-v2` paginates at 1,000 keys/page. For a full
inventory use S3 Inventory (daily export) or `list-objects-v2 --page-size 1000
--starting-token` drained to completion. For large buckets, **do not** iterate
all keys live — pull Storage Lens metrics instead (`get-storage-lens-configuration`
plus the daily CSV/Parquet export).

**Live-account pre-flight (skip if offline audit):**
1. `aws s3api get-bucket-versioning` — if `Status != Enabled`, noncurrent-version
   rules are no-ops; skip that dimension.
2. `aws s3api get-bucket-lifecycle-configuration` — capture current rules to
   compare against the recommendation.
3. `aws s3api list-multipart-uploads --bucket <name>` — pending uploads older
   than 7 days are a leak.
4. `aws s3control get-storage-lens-configuration --config-id default` —
   noncurrent-byte %, storage-class distribution, object-age histogram.
5. `aws s3api get-object-lock-configuration` — if Object Lock is enabled, any
   lifecycle rule MUST respect the retention period; violating it is a no-op.
6. `aws s3api list-buckets --query "Buckets[*].Name"` — sweep every bucket in
   every region; cross-region cost variance is material.
---

## Pre-flight safety checks (run before any remediation CLI)


- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`put-bucket-lifecycle-configuration`, `delete-bucket-lifecycle`,
  `create-job` for Batch Operations), emit: `CONFIRM: About to <action> on
  bucket <name> in account <account> region <region>. This affects
  <consequence>. Proceed? (yes/no)`. Do NOT execute until the operator
  confirms.

- **Capture current state for rollback.** Before applying:
  `aws s3api get-bucket-lifecycle-configuration --bucket <name> --output json >
  /tmp/<name>-lifecycle-backup-$(date +%s).json`. S3 lifecycle is not versioned
  — a put replaces the entire configuration atomically.

- **Verify Object Lock retention before expiration.** If the bucket has Object
  Lock, every proposed `ExpirationInDays` MUST be >= the longest retention
  period. Otherwise the rule is silently a no-op on locked objects — surface
  as a finding, not an error.

- **Verify versioning status before noncurrent rules.** If versioning is
  `Suspended`, `NoncurrentVersionTransitions` still applies to existing
  noncurrent versions. If versioning was never enabled, skip the dimension.

- **Filter scope check.** Before applying, verify the filter prefix matches the
  intended key layout. `Prefix: "logs/"` on a bucket with keys under
  `application/logs/` matches nothing.

- **Intelligent-Tiering Archive configuration check.** When recommending
  Intelligent-Tiering with custom Archive tiers, verify the
  `Tierings[].Days` values are valid (>= 90 for ARCHIVE_ACCESS, >= 180 for
  DEEP_ARCHIVE_ACCESS).

- **Batch Operations IAM check.** `s3control create-job` requires a role with
  `s3:ObjectLambda`/`s3:ReplicateObject` permissions depending on the
  operation. Verify the role exists before recommending Batch.
