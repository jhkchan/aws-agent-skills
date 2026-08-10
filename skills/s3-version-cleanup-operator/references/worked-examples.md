# S3 Version Cleanup Worked Examples

Load this reference for full worked examples of each verdict shape. The
blocks below show the exact PRE_CHECKS, STEPS with CONFIRM gate, and
NOTES for each archetype. Copy the shape that matches the target
bucket's situation.

## READY — configure lifecycle (3-rule cleanup)

```text
OPERATION: configure-lifecycle
VERDICT: READY
TARGET: s3://prod-logs-bucket
PRE_CHECKS:
  - [PASS] Bucket exists in us-east-1 account 111111111111
  - [PASS] Versioning Status: Enabled
  - [PASS] MFADelete: Disabled (no MFA required)
  - [PASS] ObjectLockEnabled: Disabled (no Compliance/Governance retention)
  - [PASS] Existing lifecycle rules captured (3 rules: current-version
    transition, current-version expiration on logs/ prefix, abort-
    multipart-upload 7d)
  - [PASS] New rules MERGED into existing config (not replacing)
  - [PASS] BucketKeyEnabled: true (no KMS optimization gap)
  - [PASS] Caller has s3:PutLifecycleConfiguration
STEPS:
  1. CONFIRM: About to put-bucket-lifecycle-configuration on
     s3://prod-logs-bucket in account 111111111111 region us-east-1.
     This will ADD NoncurrentVersionExpiration (keep 3, expire rest
     after 90d) and NoncurrentVersionTransition (Standard-IA after 30d,
     Glacier Instant Retrieval after 90d) to the existing 3 rules.
     Existing rules preserved. Estimated monthly savings: $312/month
     (~13.5 TB noncurrent versions × $0.023/GB). Proceed? (yes/no)
  2. aws s3api put-bucket-lifecycle-configuration \
       --bucket prod-logs-bucket \
       --lifecycle-configuration file:///tmp/prod-logs-bucket-merged-lifecycle.json
  3. aws s3api get-bucket-lifecycle-configuration \
       --bucket prod-logs-bucket --output json
POST_VERIFY:
  - (pending execution)
ESTIMATED_SAVINGS: $312/month (13.5 TB noncurrent × $0.023/GB-month;
  after transition to IA + GIR: $95/month; net savings $217/month)
NOTES:
  - Lifecycle rules apply within 24 hours of eligibility. Allow 24-48
    hours for the first noncurrent versions to transition/expire.
  - The 3-rule pattern (NewerNoncurrentVersions=3 + Transition to IA
    at 30d + Transition to GIR at 90d) preserves 3 recent versions,
    moves mid-aged versions to cheaper storage, and expires old ones.
  - The existing 3 rules are PRESERVED in the merged config —
    verified by reading the post-PUT lifecycle configuration.
  - S3 Storage Lens will show NoncurrentVersionCount and
    NoncurrentVersionStorageBytes dropping over 1-2 weeks.
  - For immediate cleanup of versions already older than 90d, use
    S3 Batch Operations (separate operation).
```

## BLOCKED — Object Lock Compliance mode

```text
OPERATION: batch-delete-versions
VERDICT: BLOCKED
TARGET: s3://compliance-archive-bucket
PRE_CHECKS:
  - [PASS] Bucket exists in us-east-1 account 111111111111
  - [PASS] Versioning Status: Enabled
  - [PASS] Manifest generated (10,000 noncurrent versions via
    list-object-versions pagination)
  - [FAIL] ObjectLockEnabled: Enabled, DefaultRetention: Mode=COMPLIANCE,
    Years=5. Versions within retention CANNOT be deleted by anyone
    (including root). Manifest contains 4,287 in-retention versions
    that the Batch Operations job cannot delete.
  - [SKIP] Legal hold check skipped (Object Lock Compliance already
    blocks deletion)
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ESTIMATED_SAVINGS: $0 (Compliance retention overrides cleanup)
NOTES:
  - Compliance mode is irrevocable. No one can delete the in-retention
    versions until 2031-08-09.
  - Options:
    (a) Wait for retention to expire, then re-run Batch Operations.
    (b) Apply NoncurrentVersionTransition lifecycle rules — versions
        PAST retention will transition to IA/Glacier automatically.
        In-retention versions remain in Standard until retention
        expires, then transition.
    (c) For Governance-mode buckets (not this case), delete with
        s3:BypassGovernanceRetention permission.
  - Recommend: lifecycle NoncurrentVersionTransition (IA at 30d past
    retention, GIR at 90d past retention) as the only viable cleanup
    path for Compliance-mode buckets.
```

## READY — Batch Operations immediate cleanup

```text
OPERATION: batch-delete-versions
VERDICT: READY
TARGET: s3://staging-uploads-bucket
PRE_CHECKS:
  - [PASS] Bucket exists in us-east-1 account 111111111111
  - [PASS] Versioning Status: Enabled
  - [PASS] ObjectLockEnabled: Disabled
  - [PASS] Manifest generated: 2,500,000 noncurrent versions via
    S3 Inventory (2026-08-08 snapshot)
  - [PASS] No legal holds (sampled 1000 objects, all OFF)
  - [PASS] Caller has s3control:CreateJob + iam:PassRole
  - [PASS] Execution role has s3:DeleteObjectVersion on the bucket
STEPS:
  1. CONFIRM: About to create S3 Batch Operations job to delete
     2,500,000 noncurrent versions in s3://staging-uploads-bucket
     (account 111111111111, region us-east-1). Cost: ~$2.50 ($1.00
     per million objects). Estimated savings: $825/month (35 TB ×
     $0.023/GB). Proceed? (yes/no)
  2. aws s3control create-job \
       --account-id 111111111111 \
       --operation '{"S3DeleteObjectVersion": {}}' \
       --manifest '{"Spec": {"Format": "S3InventoryReports", "Bucket": "arn:aws:s3:::manifest-bucket", "Prefix": "staging-uploads-inventory/2026-08-08/"}, "Location": {"ObjectArn": "arn:aws:s3:::manifest-bucket/staging-uploads-inventory/2026-08-08/manifest.json"}}' \
       --report "{\"Bucket\":\"arn:aws:s3:::batch-ops-reports\",\"Prefix\":\"staging-uploads-cleanup-2026-08-09/\",\"Format\":\"Report_CSV_20180820\",\"Enabled\":true,\"ReportScope\":\"AllTasks\"}" \
       --priority 50 \
       --role-arn arn:aws:iam::111111111111:role/S3BatchOperationsDeleteRole \
       --client-request-token $(uuidgen)
  3. Poll: aws s3control describe-job --account-id 111111111111 \
       --job-id <returned-id>
     Wait for Status: Complete.
POST_VERIFY:
  - (pending execution)
ESTIMATED_SAVINGS: $825/month (35 TB × $0.023/GB-month)
NOTES:
  - Batch Operations runs in minutes-to-hours depending on object
    count. Monitor via describe-job.
  - The job reports per-object success/failure — review the report CSV
    in batch-ops-reports/staging-uploads-cleanup-2026-08-09/.
  - Object Lock Compliance-mode versions (if any) fail per-object; the
    job continues but reports failures.
  - Pair this immediate cleanup with a lifecycle rule to prevent
    future accumulation.
```
