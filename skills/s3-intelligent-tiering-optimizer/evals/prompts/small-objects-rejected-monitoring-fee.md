# Eval prompt: small-objects-rejected-monitoring-fee

Optimise the following S3 bucket for Intelligent-Tiering eligibility and
emit the standard VERDICT block (BUCKET, VERDICT, REASON, RECOMMENDATION,
SAVINGS, IMPLEMENTATION). Address the operator's proposed plan explicitly.

Bucket: app-config-state
Region: us-east-1

Operator asks: "Should I move this bucket to Intelligent-Tiering?"

```json
{
  "Versioning": "Suspended",
  "ObjectLock": "not configured",
  "IntelligentTieringConfiguration": null,
  "Workload": "small JSON config state files",
  "StorageLens": {
    "window": "last 30 days",
    "object_count": 8200000,
    "average_object_size_bytes": 4200,
    "total_storage_bytes": 34400000000,
    "object_size_distribution": {
      "less_than_128KB": 100
    },
    "access_pattern": {
      "description": "GET every ~10 days uniformly across all objects"
    }
  }
}
```
