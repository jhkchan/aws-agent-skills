# Baseline (no-skill) — distributed-map-s3-csv

> This is the response a model produces **without** the skill
> definition. It provides a basic Map state definition but misses
> ItemBatchSize for batch processing (uses default 1 item per child),
> omits ToleratedFailurePercentage (single batch failure fails entire
> Map), forgets the s3:GetObject IAM permission, uses the legacy
> Iterator field instead of ItemProcessor, and does not emit the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create a Map state that reads from S3:

```json
{
  "ProcessRecords": {
    "Type": "Map",
    "Iterator": {
      "StartAt": "ProcessRow",
      "States": {
        "ProcessRow": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-row",
          "End": true
        }
      }
    },
    "ItemsPath": "$.items"
  }
}
```

Then point it at S3 somehow.
