# Baseline (no-skill) — missing-tolerated-failures

> This is the response a model produces **without** the skill
> definition. It creates a Map state without flagging the missing
> ToleratedFailureCount/Percentage as a prerequisite gap for a fault-
> tolerant workflow. A single batch failure would fail the entire Map
> state. Generated for with-skill-vs-baseline comparison.

---

Create a Map state for the unreliable API calls:

```json
{
  "FaultTolerantProcess": {
    "Type": "Map",
    "Iterator": {
      "StartAt": "CallAPI",
      "States": {
        "CallAPI": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:unreliable-api",
          "End": true
        }
      }
    }
  }
}
```

Add a Retry on the Lambda for good measure.
