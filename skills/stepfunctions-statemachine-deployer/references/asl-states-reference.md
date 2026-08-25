# Amazon States Language (ASL) — State Catalog

Supplementary reference for the Step Functions State Machine Deployer skill.
Field requirements, valid transitions, and worked examples for each ASL
state type. Use this when constructing or auditing an ASL definition.

## State types at a glance

| Type | Purpose | Required fields | Optional fields |
|---|---|---|---|
| `Task` | Invoke a service integration | `Resource`, `Next` or `End: true` | `Parameters`, `TimeoutSeconds`, `HeartbeatSeconds`, `Retry`, `Catch`, `InputPath`, `ResultPath`, `ResultSelector`, `OutputPath` |
| `Choice` | Branch on input data | `Choices[]`, `Default` | `InputPath`, `OutputPath` |
| `Parallel` | Run branches concurrently | `Branches[]`, `Next` or `End: true` | `Retry`, `Catch`, `InputPath`, `ResultPath`, `OutputPath` |
| `Map` | Iterate over a collection | `Iterator`, `Next` or `End: true` | `ItemsPath`, `MaxConcurrency`, `ItemReader` (Distributed), `ItemBatcher` (Distributed), `ToleratedFailurePercentage`, `ToleratedFailureCount`, `Retry`, `Catch`, `InputPath`, `ResultPath`, `OutputPath` |
| `Wait` | Pause for time | One of `Seconds`, `SecondsPath`, `Timestamp`, `TimestampPath` | `Next` |
| `Pass` | Transform input, no integration | `Next` or `End: true` | `Result`, `ResultPath`, `InputPath`, `OutputPath`, `Parameters` |
| `Fail` | Terminal failure | `Error`, `Cause` | (none) |
| `Succeed` | Terminal success | (none) | (none) |

## Task state

### Required fields

- `Resource` — the service integration ARN. Suffix determines semantics
  (bare, `.sync`, `.waitForTaskToken`).
- One of `Next` (string, transition to next state) or `End: true` (terminal).

### Strongly recommended fields

- `TimeoutSeconds` — explicit per-Task. Default is 60s, which silently
  kills Lambda functions configured for longer runtimes.
- `HeartbeatSeconds` — REQUIRED for Activity-based Tasks
  (`arn:aws:states:*:activity:*`). Must be strictly less than
  `TimeoutSeconds`.
- `Retry` — array of retry rules. Required for any fallible Resource.
- `Catch` — array of catch rules. Required for any fallible Resource to
  prevent execution-level failure on retry exhaustion.

### Worked example — Lambda Task with full error handling

```json
"ChargePayment": {
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "Parameters": {
    "FunctionName": "ChargePaymentFn",
    "Payload.$": "$.payment"
  },
  "TimeoutSeconds": 30,
  "HeartbeatSeconds": 15,
  "Retry": [
    {
      "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException", "Lambda.AWSLambdaException"],
      "IntervalSeconds": 2,
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    }
  ],
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "Next": "PaymentErrorHandler",
      "ResultPath": "$.error"
    }
  ],
  "ResultPath": "$.chargeResult",
  "Next": "ReserveInventory"
}
```

### Worked example — ECS runTask.sync (wait for completion)

```json
"RunBatchJob": {
  "Type": "Task",
  "Resource": "arn:aws:states:::ecs:runTask.sync",
  "Parameters": {
    "Cluster": "arn:aws:ecs:us-east-1:111111111111:cluster/batch-cluster",
    "TaskDefinition": "batch-job:12",
    "LaunchType": "FARGATE",
    "NetworkConfiguration": {
      "AwsvpcConfiguration": {
        "Subnets": ["subnet-abc123", "subnet-def456"],
        "SecurityGroups": ["sg-batch"],
        "AssignPublicIp": "DISABLED"
      }
    }
  },
  "TimeoutSeconds": 3600,
  "Retry": [
    {
      "ErrorEquals": ["ECS.AmazonECSException"],
      "IntervalSeconds": 10,
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    }
  ],
  "Catch": [
    { "ErrorEquals": ["States.ALL"], "Next": "BatchJobFailed" }
  ],
  "Next": "JobComplete"
}
```

## Choice state

### Required fields

- `Choices` — array of choice rules. Each rule has a variable (`$.path`),
  a comparison operator (`StringEquals`, `NumericLessThan`,
  `BooleanEquals`, `TimestampLessThan`, `IsNull`, `IsPresent`, `IsString`,
  `IsNumber`, `IsBoolean`, `IsNull`), and a `Next` state.
- `Default` — the state to transition to if no choice matches. The API
  rejects a Choice without `Default`; Terraform/CloudFormation may accept
  the template and fail at apply-time.

### Worked example

```json
"RouteByAmount": {
  "Type": "Choice",
  "InputPath": "$.order",
  "Choices": [
    { "Variable": "$.amount", "NumericGreaterThanEquals": 1000, "Next": "ManualReview" },
    { "Variable": "$.amount", "NumericLessThan": 100, "Next": "AutoApprove" },
    { "And": [
      { "Variable": "$.amount", "NumericGreaterThanEquals": 100 },
      { "Variable": "$.currency", "StringEquals": "USD" }
    ], "Next": "StandardApproval" }
  ],
  "Default": "ManualReview"
}
```

### Pitfalls

- `StringEquals` is case-sensitive — `"USD"` ≠ `"usd"`. Use
  `StringEqualsIgnoreCase` for case-insensitive matching (newer ASL only).
- The `Variable` path MUST exist in the input. If absent, the rule
  evaluates false (not error). Use `IsPresent` to gate on field presence.

## Parallel state

### Required fields

- `Branches` — array of independent ASL sub-state-machines. Each branch
  runs concurrently. All must complete for the Parallel state to advance.
- One of `Next` or `End: true`.

### Worked example

```json
"FanOutParallel": {
  "Type": "Parallel",
  "Branches": [
    {
      "StartAt": "SendEmail",
      "States": {
        "SendEmail": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": { "FunctionName": "SendEmailFn", "Payload.$": "$" },
          "TimeoutSeconds": 30,
          "End": true
        }
      }
    },
    {
      "StartAt": "UpdateCRM",
      "States": {
        "UpdateCRM": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": { "FunctionName": "UpdateCRMFn", "Payload.$": "$" },
          "TimeoutSeconds": 30,
          "End": true
        }
      }
    }
  ],
  "Retry": [
    { "ErrorEquals": ["States.ALL"], "IntervalSeconds": 2, "MaxAttempts": 2, "BackoffRate": 2.0 }
  ],
  "Catch": [
    { "ErrorEquals": ["States.ALL"], "Next": "ParallelErrorHandler", "ResultPath": "$.error" }
  ],
  "ResultPath": "$.fanOutResults",
  "Next": "Aggregate"
}
```

### Pitfalls

- A failure in ANY branch fails the entire Parallel state. Each branch
  should have its own error handling if independent completion is required.
- Branches receive the SAME input (the Parallel state's input). They do
  NOT receive each other's output.

## Map state

### Inline Map

```json
"ProcessItems": {
  "Type": "Map",
  "ItemsPath": "$.items",
  "MaxConcurrency": 10,
  "Iterator": {
    "StartAt": "ProcessOne",
    "States": {
      "ProcessOne": {
        "Type": "Task",
        "Resource": "arn:aws:states:::lambda:invoke",
        "Parameters": { "FunctionName": "ProcessOneFn", "Payload.$": "$" },
        "TimeoutSeconds": 30,
        "End": true
      }
    }
  },
  "ResultPath": "$.processed",
  "Next": "Done"
}
```

- Caps: 40 concurrent iterations, 256KB total payload, single Region.
- Use for: <1000 items, simple transform, no fault tolerance needed.

### Distributed Map

```json
"ProcessLargeDataset": {
  "Type": "Map",
  "MaxConcurrency": 1000,
  "ToleratedFailurePercentage": 0.5,
  "ItemReader": {
    "Resource": "arn:aws:states:::s3:getObject",
    "ReaderConfig": { "InputType": "CSV", "CSVHeaderLocation": "FIRST_ROW" },
    "Parameters": { "Bucket": "my-data", "Key": "input.csv" }
  },
  "ItemBatcher": {
    "MaxItemsPerBatch": 500,
    "BatchInput": { "pipeline": "2026-q3" }
  },
  "Iterator": { /* ... */ },
  "Next": "Summarize"
}
```

- Caps: 10,000+ concurrent iterations, multi-Region via child executions.
- Item sources: S3 (CSV, JSON, JSON Lines), DynamoDB (Scan, Query), or
  workflow payload.
- Use for: large datasets, fault-tolerant batches (ToleratedFailurePercentage),
  expensive per-item processing (ItemBatcher reduces integration count).

## Wait state

```json
"WaitOneHour": {
  "Type": "Wait",
  "Seconds": 3600,
  "Next": "CheckStatus"
}
```

Variants:
- `Seconds` — fixed wait.
- `SecondsPath` — wait read from a JSONPath in the input.
- `Timestamp` — wait until an absolute timestamp.
- `TimestampPath` — timestamp read from a JSONPath in the input.

On Express, total workflow capped at 5 min — Wait is rarely useful. On
Standard, Wait is the cheapest way to implement a long-running poll loop.

## Pass state

```json
"EnrichInput": {
  "Type": "Pass",
  "Parameters": {
    "orderId.$": "$.id",
    "processedAt.$": "$$.State.EnteredTime",
    "source": "step-functions-pipeline"
  },
  "Next": "NextTask"
}
```

Use Pass for:
- Constructing static/derived parameters for a downstream Task.
- Adding context fields (e.g., `$$Execution.Id`, `$$State.EnteredTime`).
- Scaffolding during development.

## Fail state

```json
"TerminalFailure": {
  "Type": "Fail",
  "Error": "OrderValidationFailed",
  "Cause": "Order payload failed schema validation"
}
```

`Cause` is a static string. For dynamic error context, use a Pass state
with `ResultPath` BEFORE the Fail to enrich the visible execution input.

## Succeed state

```json
"Done": { "Type": "Succeed" }
```

Terminal success. No fields beyond `Type`.

## Context object (`$$`)

ASL provides `$$` for the context object — meta-information about the
execution and state, NOT the workflow input. Useful values:

- `$$Execution.Id` — unique execution ARN.
- `$$Execution.Name` — execution name (if provided at StartExecution).
- `$$Execution.Input` — the original execution input.
- `$$State.Name` — current state's name.
- `$$State.EnteredTime` — ISO 8601 timestamp the state was entered.
- `$$Task.Token` — the Task Token for `.waitForTaskToken` Tasks (REQUIRED
  parameter to pass to the external worker).
- `$$StateMachine.Id` — state machine ARN.
- `$$Map.Item.Value` — current item in a Map iteration (inside the
  Iterator).
- `$$Map.Item.Index` — current item index (Inline Map only).

## Validation checklist (apply to any definition before deployment)

- [ ] `StartAt` exists in `States`.
- [ ] Every `Next` target exists in `States`.
- [ ] Every `Default` (in Choice) exists in `States`.
- [ ] Every `Catch.Next` target exists in `States`.
- [ ] Every `Branches[].StartAt` chain reaches a terminal state.
- [ ] Every `Iterator.StartAt` chain reaches a terminal state.
- [ ] No unreachable states (every state is reachable from `StartAt`).
- [ ] No infinite cycles (cycles have a `Retry`/`Catch`/`Choice` exit).
- [ ] Every `Task` has explicit `TimeoutSeconds`.
- [ ] Every `Task` with an Activity Resource has `HeartbeatSeconds`.
- [ ] Every fallible `Task` has at least one `Retry` AND at least one `Catch`.
- [ ] Every `Map` has explicit `MaxConcurrency` (not the default 0).
- [ ] Total payload (input + each state I/O) is < 256KB.
- [ ] Choice `Default` is set on every `Choice` state.

## Step 5 - Map state design (Inline vs Distributed) (moved from SKILL.md)

| Dimension | Inline Map | Distributed Map |
|---|---|---|
| Max concurrent iterations | 40 | 10,000+ |
| Total payload size | 256KB | Run under a child execution (no parent-payload cap) |
| Item source | Items in workflow payload (`ItemsPath`) | S3 CSV/JSON, DynamoDB Scan/Query, or payload (`ItemReader`) |
| Batching | Manual (one Task per item) | `ItemBatcher` (batch N items per Task — reduces integration count) |
| Failure tolerance | Whole Map fails on first uncaught iteration error | `ToleratedFailurePercentage` / `ToleratedFailureCount` — continue past failures |
| Per-iteration billing | Standard: one transition per iteration; Express: one invocation per iteration | Distributed Map runs as a child execution — separate billing |
| Ideal use | <1000 items, small payload, simple transform | >1000 items, large datasets, fault-tolerant batch processing |

**Inline Map example:**
```json
"ProcessOrders": {
  "Type": "Map",
  "ItemsPath": "$.orders",
  "MaxConcurrency": 10,
  "Iterator": {
    "StartAt": "ChargeOrder",
    "States": {
      "ChargeOrder": {
        "Type": "Task",
        "Resource": "arn:aws:states:::lambda:invoke",
        "Parameters": {
          "FunctionName": "ChargeOrderFn",
          "Payload.$": "$"
        },
        "TimeoutSeconds": 30,
        "Retry": [{
          "ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }],
        "Catch": [{
          "ErrorEquals": ["States.ALL"],
          "Next": "ChargeFailed",
          "ResultPath": "$.error"
        }],
        "End": true
      },
      "ChargeFailed": {
        "Type": "Fail",
        "Error": "ChargeFailed",
        "Cause": "Order charge failed after retries"
      }
    }
  },
  "Next": "NotifyComplete"
}
```

**Distributed Map example with S3 ItemReader and ItemBatcher:**
```json
"ProcessLargeDataset": {
  "Type": "Map",
  "MaxConcurrency": 1000,
  "ItemReader": {
    "Resource": "arn:aws:states:::s3:getObject",
    "ReaderConfig": {
      "InputType": "CSV",
      "CSVHeaderLocation": "FIRST_ROW"
    },
    "Parameters": {
      "Bucket": "my-dataset-bucket",
      "Key": "input/2026-08.csv"
    }
  },
  "ItemBatcher": {
    "BatchInput": { "batchMetadata": "created-by-state-machine" },
    "MaxItemsPerBatch": 100,
    "MaxItemsPerBatchPath": "$.batchSize"
  },
  "ToleratedFailurePercentage": 0,
  "Iterator": {
    "StartAt": "ProcessBatch",
    "States": {
      "ProcessBatch": {
        "Type": "Task",
        "Resource": "arn:aws:states:::lambda:invoke",
        "Parameters": {
          "FunctionName": "ProcessBatchFn",
          "Payload.$": "$"
        },
        "TimeoutSeconds": 300,
        "Retry": [{
          "ErrorEquals": ["Lambda.ServiceException"],
          "IntervalSeconds": 5,
          "MaxAttempts": 5,
          "BackoffRate": 2.0
        }],
        "Catch": [{
          "ErrorEquals": ["States.ALL"],
          "Next": "BatchFail"
        }],
        "End": true
      },
      "BatchFail": {
        "Type": "Fail",
        "Error": "BatchProcessingFailed",
        "Cause": "Batch failed after retries"
      }
    }
  },
  "Next": "Summarize"
}
```
