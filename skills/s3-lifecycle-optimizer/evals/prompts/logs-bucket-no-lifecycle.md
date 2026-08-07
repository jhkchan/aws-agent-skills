# Eval prompt: logs-bucket-no-lifecycle

Audit the following S3 bucket for cost-optimisation opportunities and emit the
standard VERDICT block (BUCKET, VERDICT, REASON, RECOMMENDATION, SAVINGS,
IMPLEMENTATION).

Bucket: app-logs-prod
Region: us-east-1

```json
{
  "Versioning": "Enabled",
  "ObjectLock": "not configured",
  "LifecycleConfiguration": null,
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 20000000000000,
    "noncurrent_bytes": 8000000000000,
    "noncurrent_pct": 40,
    "storage_class_distribution": {
      "Standard": 100,
      "Standard-IA": 0,
      "Glacier": 0
    },
    "average_object_age_days": 95
  },
  "KeyPrefixLayout": ["logs/", "application/", "archive/"],
  "IncompleteMultipartUploads": {
    "older_than_7d": 14
  }
}
```
