# Eval prompt: archive-tiers-not-configured

Optimise the following S3 bucket's Intelligent-Tiering configuration and
emit the standard VERDICT block (BUCKET, VERDICT, REASON, RECOMMENDATION,
SAVINGS, IMPLEMENTATION).

Bucket: data-lake-curated
Region: us-east-1

```json
{
  "Versioning": "Enabled",
  "IntelligentTieringConfiguration": {
    "Id": "Config",
    "Status": "Enabled",
    "Tierings": []
  },
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 100000000000000,
    "object_count": 50000000,
    "average_object_size_bytes": 2000000,
    "object_size_distribution": {
      "less_than_128KB": 1,
      "128KB_to_1MB": 19,
      "1MB_to_128MB": 80
    },
    "tier_distribution": {
      "Frequent_Access": 25,
      "Infrequent_Access": 35,
      "Archive_Access": 0,
      "Deep_Archive_Access": 0
    },
    "access_pattern": {
      "daily": 15,
      "monthly": 25,
      "no_access_90_plus_days": 40,
      "no_access_180_plus_days": 20
    },
    "average_object_age_days": 145
  }
}
```
