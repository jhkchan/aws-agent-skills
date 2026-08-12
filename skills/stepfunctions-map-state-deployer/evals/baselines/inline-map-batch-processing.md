# Baseline (no-skill) — inline-map-batch-processing

> This is the response a model produces **without** the skill
> definition. It lists a basic Map state but uses the legacy Iterator
> field, omits ItemsPath, does not specify ProcessorConfig Mode, and
> misses the 5000-item Inline limit note. Generated for with-skill-vs-
> baseline comparison.

---

Create a Map state:

```json
{
  "ProcessItems": {
    "Type": "Map",
    "Iterator": {
      "StartAt": "ProcessItem",
      "States": {
        "ProcessItem": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-item",
          "End": true
        }
      }
    }
  }
}
```

Set MaxConcurrency to 40 and you should be good.
