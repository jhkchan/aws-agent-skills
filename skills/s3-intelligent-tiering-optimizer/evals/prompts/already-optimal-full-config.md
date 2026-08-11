# Eval prompt: already-optimal-full-config

Optimise the following S3 bucket's Intelligent-Tiering configuration and
emit the standard VERDICT block (BUCKET, VERDICT, REASON, RECOMMENDATION,
SAVINGS, IMPLEMENTATION).

Bucket: analytics-warehouse
Region: us-east-1

```json
{
  "Versioning": "Enabled",
  "IntelligentTieringConfiguration": {
    "Id": "Config",
    "Status": "Enabled",
    "Filter": {"Prefix": "warehouse/"},
    "Tierings": [
      {"AccessTier": "ARCHIVE_ACCESS", "Days": 90},
      {"AccessTier": "DEEP_ARCHIVE_ACCESS", "Days": 180}
    ]
  },
  "StorageLens": {
    "window": "last 30 days",
    "total_storage_bytes": 200000000000000,
    "object_count": 60000000,
    "average_object_size_bytes": 3300000,
    "tier_distribution": {
      "Frequent_Access": 22,
      "Infrequent_Access": 45,
      "Archive_Access": 23,
      "Deep_Archive_Access": 10
    },
    "access_pattern": {
      "daily": 22,
      "monthly": 45,
      "quarterly": 23,
      "yearly": 10
    },
    "average_object_age_days": 120
  }
}
```
