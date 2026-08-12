# Baseline (no-skill) — max-concurrency-tuning

> This is the response a model produces **without** the skill
> definition. It provides a Map definition but uses Iterator instead of
> ItemProcessor (cannot do Distributed), omits ToleratedFailureCount,
> does not compute child execution count for quota verification, and
> misses the MaxConcurrency ceiling difference (Inline max 40 vs
> Distributed max 1000). Generated for with-skill-vs-baseline comparison.

---

Create a Map state with high concurrency:

```json
{
  "HighThroughputProcess": {
    "Type": "Map",
    "MaxConcurrency": 1000,
    "Iterator": {
      "StartAt": "BatchHandler",
      "States": {
        "BatchHandler": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:batch-handler",
          "End": true
        }
      }
    }
  }
}
```

MaxConcurrency 1000 should be fine.
