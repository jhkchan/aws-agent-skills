# End-to-end usage scenario: s3-glacier-restore-operator

A walkthrough showing the skill operating a multi-stage Glacier
restore workflow: an Expedited single-object restore for an urgent
audit pull, a Batch Operations bulk restore for compliance export,
and a copy-to-tier promotion to permanently move a restored object
out of archive.

## Input (user prompt)

> We need to (1) urgently restore
> `s3://prod-archive-bucket/quarterly-report-2025-Q1.parquet` for an
> audit — RTO 5 min, (2) bulk-restore the entire
> `s3://prod-archive-bucket/reports/2025/` prefix (10,000 objects)
> for compliance export within 24 hr, and (3) permanently promote
> the urgent restore to STANDARD so it does not expire. Emit the
> standard VERDICT block per operation.

## Skill output — single-object Expedited restore

```text
OPERATION: restore-object
VERDICT: READY
TARGET: prod-archive-bucket/quarterly-report-2025-Q1.parquet
PRE_CHECKS:
  - [PASS] head-object StorageClass: GLACIER (Flexible Retrieval)
  - [PASS] ArchiveStatus: ARCHIVE_ACCESS (restore required)
  - [PASS] Restore field absent (no in-progress restore)
  - [PASS] Caller IAM role holds s3:RestoreObject, s3:GetObject
  - [PASS] Provisioned capacity: 1 unit in us-east-1
  - [PASS] RTO 5 min accommodated by Expedited (1-5 min SLA)
STEPS:
  1. CONFIRM: About to restore-object prod-archive-bucket/
     quarterly-report-2025-Q1.parquet via Expedited tier (1-5 min
     SLA). Restore window: 7 days. Provisioned capacity: 1 unit.
     Proceed? (yes/no)
  2. aws s3api restore-object --bucket prod-archive-bucket
     --key quarterly-report-2025-Q1.parquet
     --restore-request '{"Days":7,"GlacierJobParameters":{"Tier":"Expedited"}}'
  3. aws s3api wait object-restored --bucket prod-archive-bucket
     --key quarterly-report-2025-Q1.parquet
POST_VERIFY:
  - [PASS] head-object Restore.ongoing-request: false
  - [PASS] head-object Restore.expiry-date populated
STATE: restored — lease expires 2026-08-17T00:00:00Z
NOTES:
  - Restore is a temporary lease. Object reverts to Glacier Flexible
    Retrieval on expiry-date. For permanent promotion, use the
    copy-to-tier operation below.
```

## Skill output — bulk restore via Batch Operations

```text
OPERATION: bulk-restore
VERDICT: READY
TARGET: batch-ops job (to be created on confirmation)
PRE_CHECKS:
  - [PASS] Manifest s3://batch-ops-manifests/restore-2025.csv
    (10000 keys) — sample 5 of 5 verified ARCHIVE_ACCESS
  - [PASS] IAM role S3BatchRestoreRole has s3:RestoreObject on
    prod-archive-bucket/* and s3:PutObject on batch-ops-reports/*
  - [PASS] Caller holds iam:PassRole on S3BatchRestoreRole
  - [PASS] Report bucket batch-ops-reports exists in us-east-1
  - [PASS] RTO 24 hr accommodated by Bulk SLA (5-12 hr)
STEPS:
  1. CONFIRM: About to create Batch Operations job for 10000 keys
     from prod-archive-bucket via Bulk tier (5-12 hr SLA). Days: 30.
     Estimated cost: ~$0.0025/GB * total-GB. Proceed? (yes/no)
  2. aws s3control create-job --account-id 111111111111 --priority 1
     --role-arn arn:aws:iam::111111111111:role/S3BatchRestoreRole
     --operation '{"S3RestoreObject":{"Days":30,"GlacierJobParameters":{"Tier":"Bulk"}}}'
     --manifest '{"Spec":{"Format":"S3BatchOperations_CSV_20180820"},"Location":{"ObjectArn":"arn:aws:s3:::batch-ops-manifests/restore-2025.csv","ETag":"<etag>"}}'
     --report "{\"Bucket\":\"arn:aws:s3:::batch-ops-reports\",\"Prefix\":\"restore-2025/\",\"Format\":\"Report_CSV_20180820\",\"ReportScope\":\"AllTasks\",\"Enabled\":true}"
  3. aws s3control describe-job --account-id 111111111111
     --job-id <JobId> (poll until Status: Complete)
POST_VERIFY:
  - [PASS] Job Status: Complete
  - [PASS] ProgressSummary.NumberSucceeded: 10000 (or near-100%)
  - [PASS] Report CSV in s3://batch-ops-reports/restore-2025/ exists
STATE: pending — job creation requested
NOTES:
  - Bulk tier SLA 5-12 hr. Schedule follow-up check at T+8 hr.
  - Restored objects revert to archive after 30 days.
  - Review report CSV for NoSuchKey failures and re-run filtered
    manifest as needed.
```

## Skill output — copy-to-tier promotion

```text
OPERATION: copy-to-tier
VERDICT: READY
TARGET: prod-archive-bucket/quarterly-report-2025-Q1.parquet ->
        prod-hot-bucket/quarterly-report-2025-Q1.parquet (STANDARD)
PRE_CHECKS:
  - [PASS] Source object Restore.ongoing-request: false (readable)
  - [PASS] Target bucket prod-hot-bucket exists
  - [PASS] Lifecycle rule on prod-hot-bucket does NOT transition
    promoted/ prefix to Glacier (verified)
  - [PASS] Caller IAM role holds s3:GetObject on source,
    s3:PutObject on target
STEPS:
  1. CONFIRM: About to copy-object prod-archive-bucket/
     quarterly-report-2025-Q1.parquet to prod-hot-bucket/quarterly-report-2025-Q1.parquet
     with StorageClass=STANDARD. Permanent promotion. Proceed? (yes/no)
  2. aws s3api copy-object --bucket prod-hot-bucket
     --key quarterly-report-2025-Q1.parquet
     --copy-source prod-archive-bucket/quarterly-report-2025-Q1.parquet
     --storage-class STANDARD
  3. aws s3api head-object --bucket prod-hot-bucket
     --key quarterly-report-2025-Q1.parquet --query 'StorageClass'
POST_VERIFY:
  - [PASS] head-object StorageClass: STANDARD on target
STATE: promoted — copy in prod-hot-bucket/quarterly-report-2025-Q1.parquet
NOTES:
  - Promotion is permanent — the target copy is not subject to the
    Glacier lifecycle rule on the source bucket.
  - The source object remains in Glacier Flexible Retrieval; its
    restore lease still expires on 2026-08-17. Update the source
    lifecycle policy if permanent deletion from archive is desired.
```

## What the skill adds over a generic assistant

- Tier-vs-source-class compatibility check (Deep Archive + Expedited
  rejected with explanation, not blindly attempted).
- GIR recognition (no wasted restore-object call on a directly
  readable object).
- Restore-in-place vs copy-to-tier decision tree (lease vs permanent
  promotion).
- Batch Operations manifest + IAM role + report bucket validation
  before `create-job`.
- RTO reconciliation (BLOCK when the tier SLA exceeds the RTO
  budget).
- Lifecycle integration (warns when a lifecycle rule will re-archive
  promoted objects).
- Mandatory CONFIRM gate with documented lease expiration.
