# Eval prompt: already-optimal-compliance-bucket

Audit the following S3 compliance archive bucket for cost-optimisation
opportunities and emit the standard VERDICT block (BUCKET, VERDICT, REASON,
RECOMMENDATION, SAVINGS, IMPLEMENTATION).

Bucket: regulated-archive-final
Region: us-east-1

```json
{
  "Versioning": "Enabled",
  "ObjectLock": {
    "Status": "Enabled",
    "Mode": "COMPLIANCE",
    "DefaultRetentionDays": 2555
  },
  "LifecycleConfiguration": {
    "Rules": [
      {
        "ID": "archive-to-deep-archive",
        "Status": "Enabled",
        "Filter": {"Prefix": "archive/"},
        "Transitions": [
          {"Days": 90, "StorageClass": "GLACIER_DEEP_ARCHIVE"}
        ]
      },
      {
        "ID": "abort-incomplete-mpu",
        "Status": "Enabled",
        "Filter": {},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}
      }
    ]
  },
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 20000000000000,
    "noncurrent_bytes": 0,
    "storage_class_distribution": {
      "Standard": 5,
      "Glacier Deep Archive": 95
    },
    "incomplete_multipart_uploads": 0
  }
}
```
