# Eval prompt: multipart-upload-leak-only

Audit the following S3 bucket for cost-optimisation opportunities and emit the
standard VERDICT block (BUCKET, VERDICT, REASON, RECOMMENDATION, SAVINGS,
IMPLEMENTATION).

Bucket: data-lake-curated
Region: us-east-1

```json
{
  "Versioning": "Enabled",
  "ObjectLock": "not configured",
  "LifecycleConfiguration": {
    "Rules": [
      {
        "ID": "tier-to-ia",
        "Status": "Enabled",
        "Filter": {"Prefix": "ingest/"},
        "Transitions": [
          {"Days": 30, "StorageClass": "STANDARD_IA"},
          {"Days": 90, "StorageClass": "GLACIER_IR"}
        ],
        "Expiration": {"Days": 365}
      },
      {
        "ID": "noncurrent-cleanup",
        "Status": "Enabled",
        "Filter": {},
        "NoncurrentVersionExpiration": {"NoncurrentDays": 90}
      }
    ]
  },
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 800000000000,
    "noncurrent_bytes": 12000000000,
    "noncurrent_pct": 1.5,
    "storage_class_distribution": {
      "Standard": 30,
      "Standard-IA": 50,
      "Glacier IR": 20
    }
  },
  "ListMultipartUploadsOutput": {
    "uploads_older_than_30d": 23
  }
}
```
