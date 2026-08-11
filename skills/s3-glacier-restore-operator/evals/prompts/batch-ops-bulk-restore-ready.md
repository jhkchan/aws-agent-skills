# Eval prompt: batch-ops-bulk-restore-ready

Plan a bulk restore of 10000 objects via S3 Batch Operations using
the Bulk tier. Manifest, IAM role, and report bucket are configured.
RTO is 24 hr (accommodates the Bulk SLA of 5-12 hr). Emit the
standard VERDICT block.

Operation: bulk-restore
Bucket: prod-archive-bucket
Manifest: s3://batch-ops-manifests/restore-2025-Q1.csv (10000 keys)
Source storage class: Glacier Flexible Retrieval
Tier: Bulk
Days: 30
RTO: 24 hours
Report bucket: s3://batch-ops-reports/

```json
{
  "BatchOpsState": {
    "manifest": {
      "bucket": "batch-ops-manifests",
      "key": "restore-2025-Q1.csv",
      "format": "S3BatchOperations_CSV_20180820",
      "key_count": 10000,
      "sample_verified": {"checked": 5, "all_archive_access": true}
    },
    "iam_role": {
      "name": "S3BatchRestoreRole",
      "permissions": ["s3:RestoreObject on prod-archive-bucket/*", "s3:PutObject on batch-ops-reports/*"]
    },
    "caller_iam": {
      "role": "S3RestoreOperatorRole",
      "permissions": ["iam:PassRole on S3BatchRestoreRole", "s3control:CreateJob"]
    },
    "report_bucket": {
      "name": "batch-ops-reports",
      "region": "us-east-1",
      "exists": true
    }
  }
}
```
