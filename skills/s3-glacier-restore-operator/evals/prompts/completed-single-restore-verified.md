# Eval prompt: completed-single-restore-verified

A previously-issued restore-object has completed. Verify the
post-restore state and emit the standard VERDICT block with
POST_VERIFY populated.

Operation: check-status
Bucket: prod-archive-bucket
Key: quarterly-report-2025-Q1.parquet
Previous restore: Tier=Expedited, Days=7, issued 2026-08-10

```json
{
  "ObjectState": {
    "head-object.prod-archive-bucket/quarterly-report-2025-Q1.parquet": {
      "StorageClass": "GLACIER",
      "Restore": {
        "ongoing-request": false,
        "expiry-date": "Tue, 18 Aug 2026 00:00:00 GMT"
      }
    },
    "get-object.prod-archive-bucket/quarterly-report-2025-Q1.parquet": {
      "HTTPStatusCode": 200,
      "ContentLength": 42000000
    }
  }
}
```
