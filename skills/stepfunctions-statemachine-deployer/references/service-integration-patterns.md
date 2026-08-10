# Step Functions Service Integration Patterns

Supplementary reference for the Step Functions State Machine Deployer skill.
Exhaustive Resource ARN catalog with integration semantics (bare, `.sync`,
`.waitForTaskToken`), required IAM actions per integration, and per-service
gotchas.

## Resource ARN suffix semantics

The Resource ARN's suffix selects the integration semantics. The bare ARN
suffix determines the request/response behavior; the IAM action and
service-specific behavior depend on the integration target.

| Suffix | Behavior | Typical use |
|---|---|---|
| (bare, e.g., `arn:aws:states:::lambda:invoke`) | Fire-and-forget if the service is async-launch; synchronous return if the service is sync | Lambda, SQS SendMessage, SNS Publish, DynamoDB single-item ops |
| `.sync` | Wait for the launched job to complete; Task result is the job's final output | ECS task, Glue job, Athena query, SageMaker training/transform, Batch job, nested Step Functions execution |
| `.waitForTaskToken` | Pause the workflow indefinitely (1yr Standard / 5min Express); resume on external `SendTaskSuccess` / `SendTaskFailure` | Human approval, async worker pattern via SQS/SNS/Lambda/EventBridge |

## Per-service integration catalog

### Lambda

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::lambda:invoke` | Sync (Lambda is inherently sync) | `lambda:InvokeFunction` on the function ARN |
| `arn:aws:states:::lambda:invoke.waitForTaskToken` | Pause for callback; pass `$$Task.Token` in the Payload | `lambda:InvokeFunction` on the function ARN |

**Gotchas:**
- Lambda is inherently synchronous. There is NO `.sync` suffix for Lambda
  — `arn:aws:states:::lambda:invoke.sync` is INVALID.
- The Lambda function's own `Timeout` (max 15 min) is INDEPENDENT of the
  Task's `TimeoutSeconds`. Set the Task timeout GREATER THAN the function
  timeout, or Step Functions kills the Task while Lambda keeps running.
- For `.waitForTaskToken`, the function MUST call
  `SendTaskSuccess(taskToken, output)` or `SendTaskFailure(taskToken,
  error, cause)` — typically via the SDK. The function's own return value
  is discarded.

### DynamoDB

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::dynamodb:getItem` | Sync direct API | `dynamodb:GetItem` on table ARN |
| `arn:aws:states:::dynamodb:putItem` | Sync direct API | `dynamodb:PutItem` on table ARN |
| `arn:aws:states:::dynamodb:updateItem` | Sync direct API | `dynamodb:UpdateItem` on table ARN |
| `arn:aws:states:::dynamodb:deleteItem` | Sync direct API | `dynamodb:DeleteItem` on table ARN |
| `arn:aws:states:::aws-sdk:dynamodb:query` | Direct SDK Query | `dynamodb:Query` on table ARN |
| `arn:aws:states:::aws-sdk:dynamodb:scan` | Direct SDK Scan | `dynamodb:Scan` on table ARN |

**Gotchas:**
- Direct integrations (no Lambda glue) are preferred for single-item CRUD.
- For Query/Scan, prefer the AWS SDK integration
  (`arn:aws:states:::aws-sdk:dynamodb:query`) — it accepts the full Query
  API parameter set.
- DynamoDB ARN format: `arn:aws:dynamodb:<region>:<account>:table/<name>`.
  Global Secondary Indexes use `:<indexName>` suffix on the ARN.

### SQS

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::sqs:sendMessage` | Sync (already sync) | `sqs:SendMessage` on queue URL |
| `arn:aws:states:::sqs:sendMessage.waitForTaskToken` | Pause for worker | `sqs:SendMessage` on queue URL |

**Gotchas:**
- The SQS Resource uses the queue URL (not ARN) in `Parameters.QueueUrl`.
- For `.waitForTaskToken`, the worker reads the message (which includes
  the Task Token), processes, then calls `SendTaskSuccess`. The message
  body must include the Token.
- FIFO queue deduplication: Express at-least-once may produce duplicate
  messages. Use a FIFO queue with `MessageDeduplicationId` for idempotency.

### SNS

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::sns:publish` | Sync (already sync) | `sns:Publish` on topic ARN |
| `arn:aws:states:::sns:publish.waitForTaskToken` | Pause for subscriber response | `sns:Publish` on topic ARN |

**Gotchas:**
- For `.waitForTaskToken`, the message includes the Token. The subscriber
  (Lambda, HTTP endpoint, etc.) must call `SendTaskSuccess` to resume.
- SNS messages are JSON-encoded; the Token must be extracted by the
  subscriber from the message body.

### ECS

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::ecs:runTask` | Fire-and-forget (Task launches) | `ecs:RunTask` on cluster ARN |
| `arn:aws:states:::ecs:runTask.sync` | Wait for task completion | `ecs:RunTask`, `ecs:DescribeTasks`, `ecs:StopTask` on cluster ARN |
| `arn:aws:states:::ecs:runTask.waitForTaskToken` | Pause for external signal | `ecs:RunTask`, `ecs:DescribeTasks`, `ecs:StopTask` |

**Gotchas:**
- `iam:PassRole` is REQUIRED for `runTask` — both the task role and task
  execution role. Scope to specific role ARNs.
- For Fargate, `LaunchType: FARGATE` and `NetworkConfiguration` are
  required in Parameters.
- For `.sync`, the Task waits until the ECS task reaches STOPPED status.
  Set `TimeoutSeconds` GREATER THAN the ECS task's expected runtime.

### AWS Batch

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::batch:submitJob.sync` | Wait for job completion | `batch:SubmitJob`, `batch:DescribeJobs`, `batch:TerminateJob` on queue + job ARNs |

**Gotchas:** Similar to ECS — needs `iam:PassRole` for the execution role.

### Glue

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::glue:startJobRun.sync` | Wait for Glue job completion | `glue:StartJobRun`, `glue:GetJobRun`, `glue:GetJobRuns`, `glue:BatchStopJobRun` on job ARN |

**Gotchas:**
- Glue jobs can run for hours. The Task's `TimeoutSeconds` must exceed
  the job's `MaxCapacity` runtime. Express workflows CANNOT use this
  pattern (5-min cap).

### Athena

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::athena:startQueryExecution.sync` | Wait for query completion | `athena:StartQueryExecution`, `athena:GetQueryExecution`, `athena:StopQueryExecution` on workgroup |
| `arn:aws:states:::athena:getQueryResults` | Fetch results (after sync) | `athena:GetQueryResults` on workgroup |

**Gotchas:**
- Two-step pattern: `startQueryExecution.sync` to wait, then
  `getQueryResults` to fetch. Often chained via `Next`.
- Result location (S3) must be writable by Athena — verify the workgroup
  config.

### SageMaker

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::sagemaker:createTrainingJob.sync` | Wait for training | `sagemaker:CreateTrainingJob`, `sagemaker:DescribeTrainingJob`, `sagemaker:StopTrainingJob` |
| `arn:aws:states:::sagemaker:createTransformJob.sync` | Wait for batch transform | `sagemaker:CreateTransformJob`, `sagemaker:DescribeTransformJob`, `sagemaker:StopTransformJob` |
| `arn:aws:states:::sagemaker:createEndpoint` | Sync (already sync) | `sagemaker:CreateEndpoint` |

**Gotchas:** `iam:PassRole` required for the training/transform execution role.

### Step Functions (nested)

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::states:startExecution` | Fire-and-forget (launch child) | `states:StartExecution` on target state machine ARN |
| `arn:aws:states:::states:startExecution.sync` | Wait for child execution to complete | `states:StartExecution`, `states:DescribeExecution`, `states:StopExecution` on target |
| `arn:aws:states:::states:startExecution.waitForTaskToken` | Pause for child to call back | `states:StartExecution`, `states:SendTaskSuccess`, `states:SendTaskFailure` |

**Gotchas:**
- `states:StartExecution` on `Resource: "*"` is a chaining/escalation
  vector. Scope to specific target state machine ARNs.
- `.sync` on nested Standard executions bills BOTH parent and child.
- Express cannot be the target of a nested execution's `.sync` pattern
  (Express executions cannot be polled via DescribeExecution after 5-60 min).

### Bedrock

| Resource | Semantics | Required IAM |
|---|---|---|
| `arn:aws:states:::bedrock:invokeModel` | Sync model invocation | `bedrock:InvokeModel` on model ARN |
| `arn:aws:states:::bedrock:invokeModel.sync` | Async (Standard only) | `bedrock:InvokeModel` on model ARN |

**Gotchas:**
- First-class integration for GenAI orchestration (RAG pipelines,
  multi-step LLM flows).
- The model ARN format:
  `arn:aws:bedrock:<region>::foundation-model/<modelId>` or
  `arn:aws:bedrock:<region>:<account>:custom-model/<customModelId>`.
- For Guardrails, add `bedrock:InvokeModelWithResponseStream` and
  reference the Guardrail in Parameters.

### AWS SDK integrations (direct API calls, no Lambda)

Resource pattern: `arn:aws:states:::aws-sdk:<service>:<action>`.

Examples:
- `arn:aws:states:::aws-sdk:secretsmanager:GetSecretValue`
- `arn:aws:states:::aws-sdk:ssm:GetParameter`
- `arn:aws:states:::aws-sdk:kms:Decrypt`
- `arn:aws:states:::aws-sdk:cloudwatch:PutMetricData`
- `arn:aws:states:::aws-sdk:s3:GetObject`
- `arn:aws:states:::aws-sdk:s3:PutObject`
- `arn:aws:states:::aws-sdk:eventbridge:PutEvents`

**Why prefer AWS SDK integrations over Lambda glue code:**
- Lower cost (no Lambda invocation billing).
- Lower latency (no Lambda cold start).
- Simpler IAM (the execution role's permissions cover the call directly).
- Less code to maintain.

**Gotchas:**
- The integration calls the underlying API; the Parameters mirror the
  SDK request shape (PascalCase). e.g., for `secretsmanager:GetSecretValue`,
  `Parameters: { "SecretId": "my-secret" }`.
- The result is the SDK response shape (also PascalCase).
- Some services have API-specific quirks (e.g., S3 GetObject returns a
  streaming body — use `aws-sdk-s3:getObject` followed by a Lambda to
  parse if needed).

## Per-pattern required IAM (cheat sheet)

| Integration pattern | Identity policy actions on execution role |
|---|---|
| `lambda:invoke` | `lambda:InvokeFunction` on function ARN |
| `lambda:invoke.waitForTaskToken` | Same + worker needs `states:SendTaskSuccess/Failure/Heartbeat` |
| `dynamodb:getItem/putItem/updateItem/deleteItem` | Respective `dynamodb:` action on table ARN |
| `aws-sdk:dynamodb:query` | `dynamodb:Query` on table ARN |
| `sqs:sendMessage` | `sqs:SendMessage` on queue URL |
| `sns:publish` | `sns:Publish` on topic ARN |
| `ecs:runTask` | `ecs:RunTask` on cluster ARN + `iam:PassRole` on task roles |
| `ecs:runTask.sync` | Add `ecs:DescribeTasks`, `ecs:StopTask` |
| `glue:startJobRun.sync` | `glue:StartJobRun`, `glue:GetJobRun`, `glue:GetJobRuns`, `glue:BatchStopJobRun` |
| `athena:startQueryExecution.sync` | `athena:StartQueryExecution`, `athena:GetQueryExecution`, `athena:StopQueryExecution` on workgroup |
| `sagemaker:createTrainingJob.sync` | `sagemaker:CreateTrainingJob`, `sagemaker:DescribeTrainingJob`, `sagemaker:StopTrainingJob` + `iam:PassRole` |
| `states:startExecution.sync` | `states:StartExecution`, `states:DescribeExecution`, `states:StopExecution` on target state machine ARN |
| `states:startExecution.waitForTaskToken` | `states:StartExecution`, `states:SendTaskSuccess`, `states:SendTaskFailure` |
| `bedrock:invokeModel` | `bedrock:InvokeModel` on model ARN |
| `aws-sdk:<svc>:<action>` | Respective action (e.g., `secretsmanager:GetSecretValue` on secret ARN) |
| Standard with X-Ray | Add `xray:PutTraceSegments`, `xray:PutTelemetryRecords` |
| Any with CloudWatch Logs | Add `logs:CreateLogDelivery`, `logs:PutLogEvents`, `logs:DescribeLogGroups`, `logs:GetLogDelivery`, `logs:UpdateLogDelivery` |

## Choosing between bare / .sync / .waitForTaskToken

Decision tree:

```
Does the service's API return immediately (already sync)?
├── Yes (Lambda, DynamoDB, SQS, SNS) → bare ARN. .sync is invalid or no-op.
└── No (ECS, Glue, Athena, SageMaker, nested SFN)
    ├── Need to wait for completion in this Task? → .sync
    └── Need to pause for an external signal/approval? → .waitForTaskToken

Need to pause the workflow for human approval, async worker, or external
system that will signal back later? → .waitForTaskToken (Standard only
for > 5min waits; Express caps at 5min)
```

## Common pitfalls

- **Lambda `.sync` does not exist.** Using it produces `InvalidDefinition`.
  Lambda is already synchronous.
- **`iam:PassRole` missing for ECS/Glue/SageMaker/Batch.** These services
  accept a runtime/execution role; passing it requires `iam:PassRole` on
  the role ARN with `iam:PassedToService: <service>.amazonaws.com`
  condition.
- **`states:StartExecution` on `*`.** Scope to specific state machine
  ARNs to prevent the chaining/escalation vector.
- **Mismatched region.** Resource ARNs must match the state machine's
  region (cross-region calls require explicit region in Parameters).
- **Missing `logs:*` permissions.** Express workflows with
  `LoggingConfiguration` require `logs:CreateLogDelivery`,
  `logs:PutLogEvents`, `logs:DescribeLogGroups`, `logs:GetLogDelivery`,
  `logs:UpdateLogDelivery` on the role, or logging silently fails.
