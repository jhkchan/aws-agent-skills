# Eval prompt: sfn-task-timeout-lambda-sync

Diagnose the following Step Functions execution failure. Walk the
States.Timeout decision tree and emit the standard VERDICT block.

## Scenario

A Standard Step Functions workflow in `us-east-1` is failing on the
`InvokeTransform` Task state with `States.Timeout`. State machine ARN:
`arn:aws:states:us-east-1:111111111111:stateMachine:etl-pipeline`.

## Known facts

- `describe-execution` for the failing execution shows:
  - `status: FAILED`
  - `error: "States.Timeout"`
  - `cause: "Task timed out at 2026-08-10T14:03:00Z"`
  - `startDate: 2026-08-10T14:00:00Z`, `stopDate: 2026-08-10T14:03:00Z`
    (failed after exactly 3 minutes — but the state ran for 60s of
    that)
- `get-execution-history` shows the `InvokeTransform` state entered at
  `14:02:00Z` and failed at `14:03:00Z` (60 seconds).
- `describe-state-machine` for the `InvokeTransform` state shows:
  ```json
  {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "FunctionName": "transform-fn",
      "Payload.$": "$"
    },
    "TimeoutSeconds": 60,
    "Next": "PersistResults"
  }
  ```
- The state has no `Retry` block.
- `aws lambda get-function-configuration --function-name transform-fn`
  shows `Timeout: 120` and `MemorySize: 256`.
- CloudWatch Logs for `transform-fn` show recent invocations averaging
  85-95 seconds, with p99 around 110 seconds. No errors in the logs.

## Symptom

`InvokeTransform` consistently times out at exactly 60 seconds.
