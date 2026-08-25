# Step Functions Map State Deployer - error handling (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Step 8 - Retry/Catch per-iteration template

```json
{
  "ProcessItems": {
    "Type": "Map",
    "ItemProcessor": {
      "StartAt": "CallAPI",
      "States": {
        "CallAPI": {
          "Type": "Task",
          "Resource": "arn:aws:lambda:us-east-1:123456789012:function:api-call",
          "Retry": [
            {
              "ErrorEquals": ["States.TaskFailed"],
              "IntervalSeconds": 2,
              "MaxAttempts": 3,
              "BackoffRate": 2.0
            }
          ],
          "Catch": [
            {
              "ErrorEquals": ["States.ALL"],
              "Next": "HandleError",
              "ResultPath": "$.error"
            }
          ],
          "Next": "ProcessResult"
        },
        "ProcessResult": { "Type": "Succeed" },
        "HandleError": { "Type": "Fail" }
      }
    },
    "ToleratedFailurePercentage": 5
  }
}
```

## Runtime error triage (six failure modes)

### Map state fails with "Items exceed maximum allowed"
- For Inline Map: the input array exceeds 5000 items. Switch to
  Distributed Map.
- For Distributed Map: the input exceeds 10000 items. Reduce the input
  size or split the workflow into multiple runs.

### Distributed Map child execution throttling
- The account's concurrent execution quota is exhausted. Reduce
  MaxConcurrency or increase ItemBatchSize to reduce the number of
  child executions. Request a quota increase via Service Quotas.

### S3 input fails with "Access Denied"
- The state machine IAM role lacks `s3:GetObject` on the target bucket.
  Add the S3 read permission to the role's policy.

### ItemBatchSize silently ignored
- The Map type is Inline, not Distributed. ItemBatchSize only works on
  Distributed Map. Switch to Distributed Map or remove ItemBatchSize.

### Single batch failure fails entire Map state
- ToleratedFailureCount and ToleratedFailurePercentage are both at
  their default (0). Set at least one to allow partial failures.

### Iterator field conflicts with Distributed configuration
- The state machine uses the legacy `Iterator` field, which only
  supports Inline Map. Switch to `ItemProcessor` with
  `ProcessorConfig.Mode: DISTRIBUTED`.

