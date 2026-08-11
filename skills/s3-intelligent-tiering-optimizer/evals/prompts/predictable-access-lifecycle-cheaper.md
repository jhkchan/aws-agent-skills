# Eval prompt: predictable-access-lifecycle-cheaper

Optimise the following S3 bucket for Intelligent-Tiering eligibility and
emit the standard VERDICT block (BUCKET, VERDICT, REASON, RECOMMENDATION,
SAVINGS, IMPLEMENTATION).

Bucket: media-thumbnails
Region: us-east-1

Operator asks: "Should I enable Intelligent-Tiering to save cost?"

```json
{
  "Versioning": "Suspended",
  "IntelligentTieringConfiguration": null,
  "Workload": "media thumbnail images served to a web app via CDN",
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 12000000000000,
    "object_count": 80000000,
    "average_object_size_bytes": 150000,
    "object_size_distribution": {
      "less_than_128KB": 35,
      "128KB_to_1MB": 65
    },
    "access_pattern": {
      "every_object_accessed_within_7_days": 100,
      "description": "CDN-backed; daily access is guaranteed for all objects"
    },
    "average_object_age_days": 30
  }
}
```
