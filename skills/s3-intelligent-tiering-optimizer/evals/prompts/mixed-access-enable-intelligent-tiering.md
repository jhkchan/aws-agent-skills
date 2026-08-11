# Eval prompt: mixed-access-enable-intelligent-tiering

Optimise the following S3 bucket for Intelligent-Tiering eligibility and
emit the standard VERDICT block (BUCKET, VERDICT, REASON, RECOMMENDATION,
SAVINGS, IMPLEMENTATION).

Bucket: app-data-mixed
Region: us-east-1

```json
{
  "Versioning": "Enabled",
  "ObjectLock": "not configured",
  "IntelligentTieringConfiguration": null,
  "LifecycleConfiguration": null,
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 56000000000000,
    "object_count": 30000000,
    "average_object_size_bytes": 1800000,
    "object_size_distribution": {
      "less_than_128KB": 3,
      "128KB_to_1MB": 27,
      "1MB_to_128MB": 70
    },
    "access_pattern": {
      "daily": 18,
      "monthly_1_to_3x": 40,
      "quarterly": 20,
      "yearly_or_less": 22
    },
    "average_object_age_days": 95
  }
}
```
