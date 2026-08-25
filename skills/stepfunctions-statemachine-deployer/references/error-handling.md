# Step Functions State Machine Deployer - error handling: Retry and Catch (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Step 6 - Error handling: Retry and Catch

ASL does NOT auto-retry. Production Tasks require explicit `Retry` (transient
errors) AND `Catch` (terminal fallback).

**Retry block fields:**
- `ErrorEquals` (array of strings): which errors trigger retry. Common
  patterns: `["Lambda.ServiceException", "Lambda.TooManyRequestsException"]`,
  `["States.TaskFailed"]`, `["States.ALL"]`.
- `IntervalSeconds` (number, default 1): wait before first retry.
- `MaxAttempts` (number, default 3): max retry count. After this, the
  `Retry` is exhausted and the error propagates to `Catch` (or fails the
  execution if no `Catch`).
- `BackoffRate` (number, default 2.0): multiplier applied to
  `IntervalSeconds` after each retry. e.g., IntervalSeconds=2,
  BackoffRate=2.0 → waits 2s, 4s, 8s.

**Catch block fields:**
- `ErrorEquals` (array of strings): which errors route to this handler.
- `Next` (string): state to route to on match.
- `ResultPath` (string, optional): where to insert the error data in the
  input. Common: `"$.error"` — preserves original input alongside the
  error context.

**Standard Retry/Catch shape for a Lambda Task:**
```json
"Task": {
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "Parameters": { "FunctionName": "MyFn", "Payload.$": "$" },
  "TimeoutSeconds": 60,
  "HeartbeatSeconds": 30,
  "Retry": [
    {
      "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException", "Lambda.AWSLambdaException"],
      "IntervalSeconds": 2,
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    },
    {
      "ErrorEquals": ["States.Timeout", "States.TaskFailed"],
      "IntervalSeconds": 5,
      "MaxAttempts": 2,
      "BackoffRate": 3.0
    }
  ],
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "Next": "ErrorHandler",
      "ResultPath": "$.error"
    }
  ],
  "Next": "Success"
}
```

**`States.ALL` does NOT match `States.Timeout` on state machines created
before November 2022.** Always add `"States.Timeout"` explicitly in the
`Catch` for long-running workflows.

