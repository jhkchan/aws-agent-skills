# Baseline (no-skill) — distributed-map-10k-items

> This is the response a model produces **without** the skill
> definition. It creates a Map state but uses Iterator (Inline only,
> 5000-item limit — would fail at runtime for 10000 items), omits
> ItemBatchSize, MaxItems, ToleratedFailurePercentage, and does not
> flag the 10000-item limit as requiring Distributed Map. Generated
> for with-skill-vs-baseline comparison.

---

Create a Map state for 10000 items:

```json
{
  "ProcessLargeDataset": {
    "Type": "Map",
    "Iterator": {
      "StartAt": "ProcessBatch",
      "States": {
        "ProcessBatch": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-batch",
          "End": true
        }
      }
    },
    "ItemsPath": "$.records",
    "MaxConcurrency": 50
  }
}
```

This should handle the items.
