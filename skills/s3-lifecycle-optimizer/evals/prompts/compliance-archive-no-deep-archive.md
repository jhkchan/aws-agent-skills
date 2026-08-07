# Eval prompt: compliance-archive-no-deep-archive

Audit the following S3 compliance archive bucket for cost-optimisation
opportunities and emit the standard VERDICT block (BUCKET, VERDICT, REASON,
RECOMMENDATION, SAVINGS, IMPLEMENTATION).

Bucket: compliance-archive-7yr
Region: us-east-1

```json
{
  "Versioning": "Enabled",
  "ObjectLock": "not configured",
  "LifecycleConfiguration": null,
  "Workload": "write-once compliance archive, accessed < 1x/year",
  "RegulatoryRetentionDays": 2555,
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 5000000000000,
    "noncurrent_bytes": 0,
    "storage_class_distribution": {
      "Standard": 100
    },
    "average_object_age_days": 120
  }
}
```
