# Eval prompt: object-lock-compliance-blocked

Plan the following S3 Batch Operations immediate cleanup and emit the
standard VERDICT block. The bucket has Object Lock in COMPLIANCE mode
with 5-year default retention.

Operation: batch-delete-versions
Bucket: compliance-archive-bucket
Region: us-east-1
Account: 111111111111
Manifest: 10,000 noncurrent versions from S3 Inventory snapshot
2026-08-08. 4,287 of these are within the 5-year retention window.

```json
{
  "BucketVersioning": {"Status": "Enabled"},
  "ObjectLockConfiguration": {
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Years": 5
      }
    }
  },
  "ExistingLifecycle": {"Rules": []},
  "ManifestSummary": {
    "TotalNoncurrentVersions": 10000,
    "InRetentionVersions": 4287,
    "PastRetentionVersions": 5713
  },
  "IamPermissions": "Caller has s3control:CreateJob, s3:DeleteObjectVersion, iam:PassRole"
}
```
