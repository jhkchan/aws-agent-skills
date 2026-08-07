# Eval prompt: small-objects-intelligent-tiering-trap

The operator has proposed moving the following S3 bucket to Intelligent-Tiering.
Audit the bucket and the proposed plan; emit the standard VERDICT block (BUCKET,
VERDICT, REASON, RECOMMENDATION, SAVINGS, IMPLEMENTATION). Address the proposed
Intelligent-Tiering plan explicitly — explain why it does or does not make
sense for this workload.

Bucket: app-config-state
Region: us-east-1

```json
{
  "Versioning": "Suspended",
  "ObjectLock": "not configured",
  "LifecycleConfiguration": null,
  "Workload": "small JSON config state files",
  "StorageLens": {
    "window": "last 30 days",
    "total_objects": 8200000,
    "average_object_size_kb": 4.2,
    "total_storage_bytes": 34400000000,
    "storage_class_distribution": {
      "Standard": 100
    },
    "access_frequency": "GET every ~10 days (uniform)"
  },
  "ProposedPlan": "move to Intelligent-Tiering"
}
```
