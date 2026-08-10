# Eval prompt: sfn-retry-exhausted-dynamodb

Diagnose the following Step Functions execution failure. Walk the
retry-exhaustion decision tree and emit the standard VERDICT block.

## Scenario

A Standard Step Functions workflow in `us-east-1` is failing
terminally on the `WriteToDynamo` Task state. State machine ARN:
`arn:aws:states:us-east-1:111111111111:stateMachine:ingest-pipeline`.

## Known facts

- `describe-execution` shows:
  - `status: FAILED`
  - `error: "States.TaskFailed"`
  - `cause: "{\"message\":\"Rate of requests exceeds the allowed
    throughput\",\"code\":\"ProvisionedThroughputExceededException\"}"`
  - `startDate: 2026-08-10T14:00:00Z`, `stopDate: 2026-08-10T14:00:14Z`
- `get-execution-history` shows 4 `TaskFailed` events for
  `WriteToDynamo` at relative offsets 0s, 2s, 6s, 14s — i.e., initial
  attempt + 3 retries with backoff `2 + 4 + 8 = 14s` of waiting.
- `describe-state-machine` for the `WriteToDynamo` state shows:
  ```json
  {
    "Type": "Task",
    "Resource": "arn:aws:states:::dynamodb:putItem",
    "Parameters": {
      "TableName": "events-table",
      "Item.$": "$.event"
    },
    "Retry": [
      {
        "ErrorEquals": ["States.TaskFailed"],
        "IntervalSeconds": 2,
        "MaxAttempts": 3,
        "BackoffRate": 2.0
      }
    ],
    "Next": "NotifySuccess"
  }
  ```
- The state has NO `Catch` block.
- The DynamoDB table `events-table` is provisioned at 50 WCU and the
  workload is bursting past 50 WCU sustained.

## Symptom

`WriteToDynamo` exhausts its 3 retries in 14 seconds and the execution
fails terminally. The DynamoDB table is the bottleneck.
