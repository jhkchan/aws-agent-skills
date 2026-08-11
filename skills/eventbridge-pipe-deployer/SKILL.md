---
name: eventbridge-pipe-deployer
description: >-
  Provisions production-grade Amazon EventBridge Pipes connecting sources
  (DynamoDB Streams, Kinesis, SQS, MSK, Amazon MQ, self-managed Kafka)
  to targets (Lambda, Step Functions, EventBridge bus, SQS, SNS, ECS,
  API Gateway, API Destination, Redshift, SageMaker, AWS Batch) with
  optional filter patterns, optional enrichment (Lambda, Step Functions,
  API Gateway, API Destination), batch windowing, dead-letter queue,
  and correct IAM roles. Emits READY_TO_DEPLOY with an ordered CLI plan
  or PREREQUISITES_MISSING with the specific gap. Use when wiring a
  streaming source to a downstream target via Pipes, configuring batch
  windows and DLQs, adding enrichment transformations, or routing
  Kafka/MSK topics to Step Functions.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). No AWS CLI required for offline plan generation.
  Live deployment uses aws pipes create-pipe, update-pipe,
  start-pipe, describe-pipe, tag-resource, aws iam create-role,
  attach-role-policy, aws sqs create-queue, get-queue-attributes,
  aws dynamodbstreams describe-stream, aws kinesis describe-stream,
  aws kafka describe-cluster, aws mq describe-broker, and
  aws lambda add-permission (AWS CLI v2, SSO or key-based credentials).
keywords:
  - EventBridge Pipes
  - pipe deploy
  - DynamoDB Streams source
  - Kinesis source
  - SQS source
  - MSK source
  - Amazon MQ source
  - self-managed Kafka
  - Lambda target
  - Step Functions target
  - EventBridge bus target
  - SQS target
  - SNS target
  - ECS task target
  - API Gateway target
  - API Destination target
  - Redshift target
  - SageMaker target
  - AWS Batch target
  - enrichment Lambda
  - enrichment Step Functions
  - filter pattern
  - batch window
  - MaximumBatchingWindowInSeconds
  - MaximumBatchSize
  - dead-letter queue
  - DLQ
  - pipe IAM role
  - enrichment transformation
tags: [eventbridge, pipes, app-integration, event-driven, deploy, streaming, dlq, batch-window, enrichment]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Provisioning a new EventBridge Pipe from a streaming or polling
    source to a downstream target, configuring batch windowing and
    concurrency, attaching a dead-letter queue for failed events,
    inserting an enrichment step (Lambda, Step Functions, API Gateway,
    API Destination), wiring an AWS Batch or Redshift or SageMaker
    target, configuring a filter pattern to pre-filter source records,
    or sourcing from MSK / Amazon MQ / self-managed Kafka.
  activation_triggers:
    - "create EventBridge Pipe"
    - "deploy EventBridge Pipe"
    - "DynamoDB Streams to Lambda pipe"
    - "Kinesis to Step Functions pipe"
    - "SQS to Lambda pipe"
    - "MSK source pipe"
    - "Amazon MQ source pipe"
    - "self-managed Kafka pipe"
    - "pipe enrichment Lambda"
    - "pipe enrichment Step Functions"
    - "pipe filter pattern"
    - "pipe batch window"
    - "MaximumBatchingWindowInSeconds"
    - "pipe DLQ"
    - "EventBridge Pipe IAM role"
    - "pipe to EventBridge bus"
    - "pipe to ECS task"
    - "pipe to API Destination"
    - "pipe to Redshift"
    - "pipe to SageMaker"
    - "pipe to AWS Batch"
  invocation_schema: >-
    Input (one of): (a) a deployment spec — source (DynamoDB Streams /
    Kinesis / SQS / MSK / Amazon MQ / self-managed Kafka), optional
    filter pattern, optional enrichment (Lambda / Step Functions / API
    Gateway / API Destination), target (Lambda / Step Functions /
    EventBridge bus / SQS / SNS / ECS / API Gateway / API Destination /
    Redshift / SageMaker / Batch), batch window and batch size, DLQ
    ARN, IAM role configuration; (b) a partial spec for interactive
    refinement; (c) an existing pipe ARN for review against the
    well-architected checklist. Output: PIPE_SPEC, VERDICT,
    ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS — where
    VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.
---

# EventBridge Pipe Deployer

## What this skill does

Provisions production-grade Amazon EventBridge Pipes connecting a
streaming or polling source to a downstream target with secure
defaults: source selection (DynamoDB Streams, Kinesis, SQS, MSK,
Amazon MQ, self-managed Kafka), optional filter pattern, optional
enrichment (Lambda, Step Functions, API Gateway, API Destination),
target selection (Lambda, Step Functions, EventBridge bus, SQS, SNS,
ECS, API Gateway, API Destination, Redshift, SageMaker, Batch),
batch windowing with DLQ, and correct least-privilege IAM roles.
Emits a deployment plan with a READY_TO_DEPLOY checklist.

## Mindset

**One-line takeaway:** an EventBridge Pipe is a **point-to-point
stream processor** — one source, one target, optional filter +
enrichment in between. Unlike an EventBridge rule (which is a fan-out
dispatcher from a bus), a Pipe pulls records from a source on the
Pipe's own concurrency, optionally transforms them, and delivers them
to exactly one target. Pipes own the polling, batching, retry, and DLQ.

Three facts make Pipe provisioning different from "trigger Lambda on
stream events":

- **The Pipe is the poller — not the target.** For DynamoDB Streams
  and Kinesis sources, you do NOT attach the Lambda trigger directly.
  The Pipe's IAM role reads from the stream; the Pipe delivers batches
  to the target. Two independent permissions are required: the Pipe
  role reads the source, the target resource policy allows the Pipe
  role to invoke it. Skipping the target resource policy is the most
  common failure.

- **Batch window behavior is source-dependent.** For streaming sources
  (DynamoDB Streams, Kinesis, MSK, MQ, self-managed Kafka),
  `MaximumBatchingWindowInSeconds` (0-300s) controls how long the Pipe
  waits to assemble a batch before invoking the target. For SQS sources
  the window is ignored — SQS already has its own `VisibilityTimeout`
  and `ReceiveMessage` semantics. Set `MaximumBatchSize` (1-10000,
  source-specific cap) and `MaximumRecordAgeInSeconds` (60-86400s) to
  bound batch behavior.

- **Enrichment and target are separate stages with separate
  permissions.** The enrichment step (Lambda, Step Functions, API
  Gateway, API Destination) transforms the batched payload before it
  reaches the target. The Pipe role needs `lambda:InvokeFunction` (or
  equivalent) on the enrichment AND a separate grant on the target.
  Each stage has its own retry policy; enrichment failures do NOT
  automatically replay to the DLQ unless the Pipe's `OnPartialBatchItemFailure`
  is configured for SQS/Kinesis sources.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + checklist matrix + Pipe limits | Before any operation |
| **Pre-flight** | Source/target ARN gate, IAM, DLQ, batch window | Before executing any CLI |
| **Process** | Per-step: source, filter, enrichment, target, batch window, DLQ, IAM | When choosing each step |
| **Common patterns** | DDB Streams → Lambda / Kinesis → Step Functions / SQS → Batch | Boilerplate lookup |
| **STRICT output contract** | Required PIPE/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block | Formatting the response |
| **NEVER (top 5)** | Hard rules preventing common insecure patterns | Review before deploy |
| **Expert heuristic** | When to use enrichment vs. inline target Lambda | Choosing architecture |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `PREREQUISITES_MISSING` | Any pre-check failed (source ARN not in `ACTIVE`/`ENABLED` state, target ARN unresolvable, source type unsupported in region, DLQ missing or wrong type, IAM permission missing on source or target or enrichment, batch window out of range, MSK unauthenticated cluster without SASL/IAM auth, Amazon MQ broker `PENDING`/`REBOOTING`, self-managed Kafka without `AuthType` set, filter pattern malformed JSON, enrichment ARN type mismatch) | List failures, do NOT execute |
| `READY_TO_DEPLOY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence with full pipe config, wait for operator yes |

**Deployment checklist (every dimension must pass):**

| Dimension | Requirement | Step |
|---|---|---|
| Source type | DynamoDB Streams, Kinesis, SQS, MSK, Amazon MQ, or self-managed Kafka | Step 1 |
| Source state | `ACTIVE`/`ENABLED` (streams), `ACTIVE` (broker), `ACTIVE`/`CREATING` (MSK) | Step 1 |
| Source ARN region | Must match Pipe region (cross-region source not supported) | Step 1 |
| Filter pattern | Valid JSON matching source record schema (optional) | Step 2 |
| Enrichment | Lambda / Step Functions / API Gateway / API Destination (optional) | Step 3 |
| Target type | Lambda, Step Functions, EventBridge bus, SQS, SNS, ECS, API Gateway, API Destination, Redshift, SageMaker, Batch | Step 4 |
| Target resource policy | Allows `pipes.amazonaws.com` (or pipe role) to invoke | Step 4 |
| Batch window | `MaximumBatchingWindowInSeconds` 0-300 (ignored for SQS source) | Step 5 |
| Batch size | `MaximumBatchSize` 1-10000, source-specific cap | Step 5 |
| Record age | `MaximumRecordAgeInSeconds` 60-86400 (streaming sources) | Step 5 |
| Retry attempts | `MaximumRetryAttempts` 0-185 (target) | Step 5 |
| DLQ | SQS queue ARN in same region; pipe role `sqs:SendMessage` on DLQ | Step 6 |
| IAM role | Pipe role: source read, enrichment invoke, target invoke, DLQ send | Step 7 |

**EventBridge Pipes limits (2026):**

- Pipes per account per region (default): 100 (soft limit).
- Pipes per source (default): 1 — a single source can attach to one Pipe only (use EventBridge rules or fan-out via SNS for multiple consumers).
- `MaximumBatchingWindowInSeconds`: 0-300 (0 = invoke immediately on first record).
- `MaximumBatchSize`: 1-10000 (DDB Streams cap 1000, Kinesis cap 10000, SQS cap 10000, MSK/MQ cap 10000).
- `MaximumRecordAgeInSeconds`: 60-86400 (streaming sources only).
- `MaximumRetryAttempts`: 0-185 (target; 185 = ~6 hours backoff).
- `MaximumRecordAgeInSeconds` and DLQ require streaming source (DDB Streams, Kinesis, MSK, MQ, self-managed Kafka). SQS source does not use either — the source queue's own DLQ handles failures.
- Filter pattern: max 4096 chars JSON.
- Concurrent pipe executions per region (default): dynamic, scales with account quota.
- MSK / self-managed Kafka: requires `ConsumerGroupID`, `StartingPosition` (`LATEST`, `TRIM_HORIZON`, `AT_TIMESTAMP`).

## Pre-flight: deployment specification gate (run before architecture output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid
spec produces a non-functional or insecure Pipe.

**Live-account pre-flight checks (skip if doing offline architecture plan):**

1. Verify IAM permissions: `pipes:CreatePipe`, `StartPipe`,
   `UpdatePipe`, `DescribePipe`, plus source/target/enrichment rights
   (e.g., `dynamodbstreams:GetRecords`, `lambda:InvokeFunction`,
   `sqs:ReceiveMessage`, `kafka-cluster:ReadData`).
2. Verify source ARN resolves and region matches Pipe region:
   - DynamoDB Streams: `aws dynamodbstreams describe-stream --stream-arn <arn>` returns `StreamStatus=ENABLED`.
   - Kinesis: `aws kinesis describe-stream --stream-arn <arn>` returns `StreamStatus=ACTIVE`.
   - SQS: `aws sqs get-queue-attributes --queue-url <url>` returns `QueueArn`.
   - MSK: `aws kafka describe-cluster --cluster-arn <arn>` returns `State=ACTIVE`.
   - Amazon MQ: `aws mq describe-broker --broker-id <id>` returns `BrokerState=RUNNING`.
3. Verify target ARN resolves and resource policy grants invoke to
   `pipes.amazonaws.com` (Lambda, Step Functions, API Gateway) or the
   pipe role ARN (SQS, SNS, ECS task).
4. Verify DLQ (if configured): SQS queue exists in same region, queue
   policy allows the pipe role to `sqs:SendMessage`.
5. Verify enrichment (if configured): Lambda function state `Active`,
   Step Functions state machine state `ACTIVE`, API Gateway stage
   deployed, API Destination with active connection.
6. For MSK / self-managed Kafka: verify `AuthType` (`SASL_SCRAM_512_AUTH`,
   `SASL_SCRAM_256_AUTH`, `IAM`, `MTLS`, `NONE` — `NONE` rejected for
   non-local clusters) and `ConsumerGroupID` is unique.
7. For Amazon MQ: verify `Credentials` secret in Secrets Manager with
   `username`/`password` keys, broker state `RUNNING`.

| Attribute | Value | Effect on plan |
|---|---|---|
| Source = DynamoDB Streams | Polls stream on Pipe's concurrency | Requires `dynamodbstreams:GetShardIterator`, `GetRecords`, `DescribeStream`. Source queue/stream NOT attached directly to target. |
| Source = SQS | Pipe consumes via `ReceiveMessage`, hides visibility timeout | DLQ on the SQS queue itself handles poison pills. Pipe-level DLQ ignored. |
| Source = MSK / Amazon MQ / self-managed Kafka | Requires `ConsumerGroupID`, `StartingPosition`, `AuthType` | Pipe maintains Kafka consumer offsets. |
| Enrichment = Lambda | Transforms batched payload before target | Pipe role needs `lambda:InvokeFunction` on enrichment function. |
| Target = AWS Batch | Submits a job to a job queue | Pipe role needs `batch:SubmitJob`. |
| Target = API Destination | HTTPS POST to external endpoint | Requires API Destination + Connection resources pre-created. |
| DLQ | SQS queue in same region | Pipe role needs `sqs:SendMessage` on DLQ ARN. Streaming sources only. |

**If the deployment spec is incomplete** (missing source ARN, target
ARN, or source type), output:

```text
PIPE_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a Pipe plan without <field> — the resulting deployment
would be non-functional or insecure.
REQUIRED:
  - source_type (DynamoDB Streams, Kinesis, SQS, MSK, Amazon MQ, self-managed Kafka)
  - source_arn (stream/queue/cluster/broker ARN, region must match Pipe region)
  - target_type (Lambda, Step Functions, EventBridge bus, SQS, SNS, ECS, API Gateway, API Destination, Redshift, SageMaker, Batch)
  - target_arn
  - pipe_role_arn (or accept default least-privilege generated by this skill)
  - batch_window_seconds (0-300, ignored for SQS source)
```

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious Pipe behaviors that change the plan

- **The Pipe is the poller — the target's trigger config is NOT used.**
  For DynamoDB Streams → Lambda, you do NOT call
  `lambda create-event-source-mapping`. The Pipe role reads the stream
  and invokes Lambda. The Lambda does NOT have a direct AWS::Lambda::EventSourceMapping.

- **Two independent permissions are required per pipe.** (a) The pipe
  role reads from the source (`dynamodbstreams:GetRecords` or
  `sqs:ReceiveMessage` or `kinesis:GetRecords` or `kafka-cluster:ReadData`).
  (b) The target resource policy allows the pipe role (or
  `pipes.amazonaws.com`) to invoke. Lambda / Step Functions / API
  Gateway targets accept resource-based policies; SQS / SNS / ECS
  require the pipe role to have the action in its identity-based policy.

- **`MaximumBatchingWindowInSeconds` is ignored for SQS sources.** SQS
  already controls visibility and receipt semantics. For SQS source,
  set the source queue's `VisibilityTimeout` to at least 6x the target
  Lambda timeout (standard Lambda event-source mapping rule). For
  streaming sources, the batching window controls how long the Pipe
  waits to gather records before invoking.

- **DLQ behavior differs by source type.** For DynamoDB Streams,
  Kinesis, MSK, Amazon MQ, and self-managed Kafka: the pipe DLQ receives
  records that exceed retry or record-age limits. For SQS source: the
  DLQ is on the **source queue** (configured via `RedrivePolicy`); the
  pipe-level `DeadLetterConfig` is ignored for SQS. Configure both
  correctly or your poison-pill messages disappear.

- **Enrichment runs on the BATCHED payload, not individual records.**
  The enrichment Lambda receives the full batch in one invocation. If
  it throws, the entire batch is retried. Use enrichment for batch
  transformations (e.g., join records, schema reshape, enrichment
  lookup) — NOT for per-record validation (use the target Lambda for that).

- **MSK / self-managed Kafka require explicit `ConsumerGroupID`.** Two
  pipes sharing a consumer group split partitions between them. Two
  pipes with different consumer groups both receive all records. Pick
  the consumer group deliberately — wrong choice silently halves or
  duplicates throughput.

- **Filter pattern runs on the source's raw payload, BEFORE enrichment.**
  For DynamoDB Streams the filter matches the `dynamodb.NewImage` /
  `OldImage` fields. For SQS it matches the `body` (JSON-parsed). For
  Kinesis it matches the decoded record. Malformed patterns silently
  filter everything — always validate with `test-event-pattern` style
  dry-run before deploying.

- **`OnPartialBatchItemFailure` controls partial failure behavior for
  SQS and Kinesis/DDB sources (2024+).** `AUTOMATIC_BISECT` splits the
  batch in half on failure (helps isolate poison records). Set this
  when working with large batches where one bad record should not
  reprocess the whole batch.

### Step 1: Source — type, ARN, region, state

```bash
aws pipes create-pipe \
  --name prod-ddb-pipe \
  --role-arn arn:aws:iam::111111111111:role/service-role/EventBridgePipesRole \
  --source "arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01T00:00:00.000" \
  --source-parameters '{"DynamoDBStreamParameters":{"StartingPosition":"LATEST","BatchSize":100,"MaximumBatchingWindowInSeconds":5,"MaximumRecordAgeInSeconds":3600,"DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq"},"OnPartialBatchItemFailure":"AUTOMATIC_BISECT"}}'
```

| Source type | Required source parameters | Notes |
|---|---|---|
| DynamoDB Streams | `StartingPosition` (LATEST/TRIM_HORIZON/LATEST), `BatchSize`, `MaximumBatchingWindowInSeconds`, `MaximumRecordAgeInSeconds`, `DeadLetterConfig`, `OnPartialBatchItemFailure` | Stream must be `ENABLED`. |
| Kinesis | `StartingPosition`, `BatchSize`, `MaximumBatchingWindowInSeconds`, `MaximumRecordAgeInSeconds`, `DeadLetterConfig`, `OnPartialBatchItemFailure` | Stream must be `ACTIVE`. |
| SQS | `QueueUrl` or `QueueArn`, `BatchSize` | VisibilityTimeout >= 6x target timeout. DLQ on source queue, NOT pipe-level. |
| MSK | `TopicName`, `ConsumerGroupID`, `StartingPosition`, `BatchSize`, `AuthType`, `MaximumRecordAgeInSeconds`, `DeadLetterConfig` | Cluster `ACTIVE`. AuthType from `SASL_SCRAM_512_AUTH`/`IAM`/`MTLS`. |
| Amazon MQ | `QueueName`, `Credentials` (Secrets Manager), `BatchSize`, `MaximumBatchingWindowInSeconds` | Broker `RUNNING`. Pulsar or ActiveMQ. |
| Self-managed Kafka | `TopicName`, `ConsumerGroupID`, `StartingPosition`, `BatchSize`, `AuthType`, `ServerRootCA` (optional), `VpcSubnets/SecurityGroups` (for VPC-restricted brokers) | Requires VPC config for private clusters. |

### Step 2: Filter pattern (optional)

```bash
--filter-criteria '{"Filters":[{"Pattern":"{\"dynamodb\":{\"NewImage\":{\"status\":{\"S\":\"CONFIRMED\"}}}}"}]}'
```

Filter patterns match the **source's raw record schema**:

- DynamoDB Streams: matches `dynamodb.NewImage` / `OldImage` JSON
- Kinesis: matches decoded record JSON
- SQS: matches `body` JSON (if `body` is JSON; otherwise no match)
- Kafka (MSK/MQ/self-managed): matches decoded record value JSON

**Validation:** a filter pattern that doesn't match any field silently
filters everything. Validate the pattern shape against a sample source
record before deploying. Maximum 4096 chars per pattern.

### Step 3: Enrichment (optional — Lambda, Step Functions, API Gateway, API Destination)

```bash
--enrichment "arn:aws:lambda:us-east-1:111111111111:function:orders-enrich" \
--enrichment-parameters '{"LambdaParameters":{"InvocationType":"REQUEST_RESPONSE"}}'
```

| Enrichment type | ARN | Notes |
|---|---|---|
| Lambda | `arn:aws:lambda:<region>:<acct>:function:<name>` | Receives the full batched payload, returns transformed batch. `InvocationType` REQUEST_RESPONSE (sync) required. |
| Step Functions | `arn:aws:states:<region>:<acct>:stateMachine:<name>` | Runs a synchronous Express Workflow (Synchronous Express required; Standard not supported for enrichment). |
| API Gateway | `arn:aws:apigateway:<region>::/restapis/<id>/stages/<stage>/POST/<path>` | REST or HTTP API; called synchronously per batch. |
| API Destination | `arn:aws:events:<region>:<acct>:api-destination/<name>` | HTTPS POST to external endpoint. Requires Connection resource. |

**Enrichment IAM:** the pipe role needs `lambda:InvokeFunction` /
`states:StartSyncExecution` / `apigateway:POST` /
`events:InvokeApiDestination on the enrichment ARN.

**Anti-pattern:** NEVER use enrichment for per-record validation. The
enrichment receives the entire batch — a single bad record throws and
retries the whole batch. Use enrichment for batch transformations only.

### Step 4: Target — type, ARN, resource policy

```bash
--target "arn:aws:lambda:us-east-1:111111111111:function:orders-processor" \
--target-parameters '{"LambdaParameters":{"InvocationType":"REQUEST_RESPONSE"}}'
```

| Target type | ARN shape | Resource policy / IAM |
|---|---|---|
| Lambda | `arn:aws:lambda:<region>:<acct>:function:<name>` | `lambda:AllowInvoke` from `pipes.amazonaws.com` OR pipe role. |
| Step Functions | `arn:aws:states:<region>:<acct>:stateMachine:<name>` | Standard or Express supported. Pipe role: `states:StartExecution`. |
| EventBridge bus | `arn:aws:events:<region>:<acct>:event-bus/<name>` | Pipe role: `events:PutEvents`. |
| SQS | `arn:aws:sqs:<region>:<acct>:<name>` | Pipe role: `sqs:SendMessage`. |
| SNS | `arn:aws:sns:<region>:<acct>:<name>` | Pipe role: `sns:Publish`. |
| ECS task | `arn:aws:ecs:<region>:<acct>:cluster/<cluster>` + `TaskDefinitionArn` | Pipe role: `ecs:RunTask`, `iam:PassRole` on task role. |
| API Gateway | `arn:aws:apigateway:<region>::/restapis/<id>/stages/<stage>/POST/<path>` | Pipe role: `apigateway:POST`. |
| API Destination | `arn:aws:events:<region>:<acct>:api-destination/<name>` | Pipe role: `events:InvokeApiDestination`. |
| Redshift | `arn:aws:redshift-serverless:<region>::workgroup/<id>` or `arn:aws:redshift:<region>:<acct>:cluster:<name>` | Pipe role: `redshift-serverless:GetCredentials`, `redshift-data:ExecuteStatement`. |
| SageMaker Pipeline | `arn:aws:sagemaker:<region>:<acct>:pipeline/<name>` | Pipe role: `sagemaker:StartPipelineExecution`. |
| AWS Batch | `arn:aws:batch:<region>:<acct>:job-queue/<queue>` + `JobDefinition` | Pipe role: `batch:SubmitJob`. |

**Two-rule check:** (1) target ARN resolves in target account; (2)
target resource policy OR pipe role grants the invoke. Emit both as
PRE_CHECKS rows.

### Step 5: Batch windowing, retry, record age

```bash
# Streaming sources: full batch config
--source-parameters '{
  "DynamoDBStreamParameters": {
    "StartingPosition": "LATEST",
    "BatchSize": 100,
    "MaximumBatchingWindowInSeconds": 5,
    "MaximumRecordAgeInSeconds": 3600,
    "MaximumRetryAttempts": 3,
    "OnPartialBatchItemFailure": "AUTOMATIC_BISECT",
    "DeadLetterConfig": {"Arn":"arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq"}
  }
}'

# SQS source: pipe-level retry only (DLQ on source queue)
--source-parameters '{"SQSQueueParameters":{"BatchSize":10}}'
--target-parameters '{"LambdaParameters":{"InvocationType":"REQUEST_RESPONSE"}}'
```

| Field | Range | Applies to |
|---|---|---|
| `MaximumBatchingWindowInSeconds` | 0-300 | Streaming sources only (ignored for SQS) |
| `BatchSize` / `MaximumBatchSize` | 1-1000 DDB / 1-10000 Kinesis / 1-10000 SQS / 1-10000 Kafka | All sources |
| `MaximumRecordAgeInSeconds` | 60-86400 | Streaming sources only |
| `MaximumRetryAttempts` | 0-185 | Target (per-batch retry) |
| `OnPartialBatchItemFailure` | `AUTOMATIC_BISECT` | DDB Streams, Kinesis, SQS (2024+) |

### Step 6: Dead-letter queue

```bash
# Create DLQ (one-time)
aws sqs create-queue --queue-name prod-pipe-dlq
# Attach to pipe via source-parameters DeadLetterConfig.Arn (streaming sources)
```

**Two-DLQ rule:**

- **Streaming sources (DDB Streams, Kinesis, MSK, MQ, self-managed Kafka):** DLQ lives on the pipe (`DeadLetterConfig.Arn` inside the source-parameters block). Records that exceed retry or record-age land here.
- **SQS sources:** DLQ lives on the **source SQS queue** via `RedrivePolicy`. The pipe-level `DeadLetterConfig` is ignored. Configure `maxReceiveCount` on the source queue's redrive policy.

Pipe role needs `sqs:SendMessage` on the DLQ ARN (or on the source
queue's DLQ for the SQS case — the SQS service uses the queue's own
permissions, not the pipe role's).

### Step 7: IAM role — least-privilege trust + permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "pipes.amazonaws.com"},
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {"aws:SourceAccount": "111111111111"},
        "ArnEquals": {"aws:SourceArn": "arn:aws:pipes:us-east-1:111111111111:pipe/prod-ddb-pipe"}
      }
    }
  ]
}
```

**Required permissions on the pipe role:**

| Source | Permissions |
|---|---|
| DynamoDB Streams | `dynamodbstreams:DescribeStream`, `GetShardIterator`, `GetRecords`; `dynamodb:DescribeTable` |
| Kinesis | `kinesis:DescribeStream`, `GetShardIterator`, `GetRecords`, `ListShards` |
| SQS | `sqs:ReceiveMessage`, `DeleteMessage`, `GetQueueAttributes` |
| MSK | `kafka-cluster:Connect`, `ReadData`, `DescribeTopic`, `DescribeGroup`, `AlterGroup` |
| Amazon MQ | Secrets Manager `secretsmanager:GetSecretValue` on broker credentials; STS for credential exchange |
| Self-managed Kafka | (Same as MSK) + MSK-style VPC config |

| Enrichment / Target | Permissions |
|---|---|
| Lambda enrichment/target | `lambda:InvokeFunction` on enrichment ARN + target ARN |
| Step Functions target | `states:StartExecution` (Standard) or `StartSyncExecution` (Express enrichment) |
| EventBridge bus target | `events:PutEvents` |
| SQS target | `sqs:SendMessage` |
| SNS target | `sns:Publish` |
| ECS target | `ecs:RunTask`, `iam:PassRole` on task execution + task roles |
| API Gateway / API Destination target | `apigateway:POST` / `events:InvokeApiDestination` |
| Redshift target | `redshift-serverless:GetCredentials` / `redshift-data:ExecuteStatement` |
| SageMaker target | `sagemaker:StartPipelineExecution` |
| AWS Batch target | `batch:SubmitJob` |
| DLQ | `sqs:SendMessage` on DLQ ARN |

## Common patterns

- **DynamoDB Streams → Lambda with filter + DLQ.** Filter pattern
  matches `dynamodb.NewImage.status.S = CONFIRMED`. Pipe role reads
  stream and invokes Lambda. DLQ catches records exceeding 3 retries
  or 1-hour age. Most common Pipe pattern.

- **Kinesis → Step Functions with batch windowing.** `MaximumBatchingWindowInSeconds=30`
  collects up to 100 records per invocation. Step Functions Express
  Workflow runs sync; failures retry up to 185 times. Use for
  stream-triggered orchestration.

- **SQS → Lambda without pipe-level DLQ.** Source SQS queue has its
  own DLQ via `RedrivePolicy` with `maxReceiveCount=5`. Pipe-level
  `DeadLetterConfig` ignored. The pipe just connects the queue to
  Lambda with batching.

- **MSK → AWS Batch target.** Kafka consumer group `pipe-batch-consumer`
  reads from `orders-events` topic; pipe submits a Batch job per batch
  for offline processing. Enables event-driven batch processing without
  a separate consumer service.

- **DynamoDB Streams → Lambda enrichment → Step Functions target.**
  Enrichment Lambda joins with customer data, returns transformed
  batch; Step Functions runs orchestration. Two permission grants
  needed: enrichment Lambda + target state machine.

## Output format

```text
PIPE_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Source: <type> <arn> (region <region>, state <ACTIVE|ENABLED|RUNNING>)
  Filter pattern: <none | JSON pattern>
  Enrichment: <none | Lambda/Step Functions/API Gateway/API Destination arn>
  Target: <type> <arn>
  Batch window: <seconds> seconds (ignored for SQS source)
  Batch size: <records>
  Record age: <seconds> (streaming sources only)
  Retry attempts: <count>
  DLQ: <arn> (pipe-level for streaming / source-queue-level for SQS)
CHECKLIST:
  [x] Source ARN resolves in region matching pipe
  [x] Source state ACTIVE / ENABLED / RUNNING
  [x] Filter pattern valid JSON (if specified)
  [x] Enrichment ARN resolves and grants pipe role invoke (if specified)
  [x] Target ARN resolves and grants pipe role invoke
  [x] Batch window 0-300 (ignored for SQS)
  [x] Batch size within source-specific cap
  [x] Record age 60-86400 (streaming sources only)
  [x] DLQ policy grants pipe role sqs:SendMessage
  [x] IAM role trust policy scoped to pipes.amazonaws.com with SourceAccount/SourceArn condition
FINDINGS:
  - [INFO] Estimated monthly cost: $0.50 base + $0.50 per million invocations + source throughput
  - [WARN] SQS source configured with pipe-level DeadLetterConfig — ignored, configure RedrivePolicy on source queue
DEPLOY_COMMANDS:
  <ordered list of aws pipes create-pipe commands and prerequisite IAM/DLQ setup>
```

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
PIPE: <pipe-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
TARGET: <pipe-name> (pipe-arn: <arn> for updates)
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. CONFIRM: About to <operation> pipe <name> in account <account>. This will <consequence>. Estimated monthly cost: <$X>. Proceed? (yes/no)
  2. <exact CLI command — no placeholders>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
SOURCE: <type> <arn> region <region>
FILTER: <none | JSON pattern>
ENRICHMENT: <none | type arn>
TARGET: <type> <arn>
BATCH: window <seconds> size <records> retry <count> age <seconds>
DLQ: <arn | source-queue redrive>
NOTES: <filter selectivity, retry behavior, cost posture>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll create…" — the VERDICT
  block is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING` (not `ready`, `prerequisites`).
- NEVER omit PRE_CHECKS — every pre-check run must appear with `[PASS]`
  or `[FAIL]` and a specific reason for each failure. An empty
  PRE_CHECKS block is non-compliant.
- NEVER emit a plan with placeholder values (e.g., `<source-arn>`,
  `<account-id>`) in a READY_TO_DEPLOY plan — every field must be
  populated with actual values from the input.
- NEVER omit the CONFIRM gate as the first STEPS entry for any
  state-changing operation.
- NEVER claim success without verifying the pipe is `RUNNING` via
  `describe-pipe` — a CREATED pipe that has not been started does not
  process events.
- NEVER silently allow SQS source with pipe-level `DeadLetterConfig` —
  call it out as a [WARN] in PRE_CHECKS and direct the user to
  configure `RedrivePolicy` on the source queue.
- NEVER allow MSK or self-managed Kafka source without an explicit
  `AuthType` — `NONE` is rejected for non-local clusters.

### Perfect example output

```text
PIPE: prod-orders-pipe
VERDICT: READY_TO_DEPLOY
TARGET: prod-orders-pipe
PRE_CHECKS:
  - [PASS] DynamoDB Streams arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01 resolves state=ENABLED
  - [PASS] Source region us-east-1 matches pipe region
  - [PASS] Filter pattern {"dynamodb":{"NewImage":{"status":{"S":"CONFIRMED"}}}} valid JSON
  - [PASS] Enrichment Lambda arn:aws:lambda:us-east-1:111111111111:function:orders-enrich resolves state=Active
  - [PASS] Enrichment resource policy grants lambda:InvokeFunction to pipes.amazonaws.com
  - [PASS] Target Lambda arn:aws:lambda:us-east-1:111111111111:function:orders-processor resolves state=Active
  - [PASS] Target resource policy grants lambda:InvokeFunction to pipes.amazonaws.com
  - [PASS] Batch window 5s in range 0-300
  - [PASS] Batch size 100 within DynamoDB Streams cap (1000)
  - [PASS] DLQ arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq policy grants sqs:SendMessage to pipe role
  - [PASS] Pipe role trust policy scoped to pipes.amazonaws.com with SourceAccount=111111111111
  - [PASS] IAM principal holds pipes:CreatePipe, StartPipe, DescribePipe
STEPS:
  1. CONFIRM: About to create-pipe prod-orders-pipe in account 111111111111. Reads DynamoDB Streams Orders table, filter CONFIRMED, Lambda enrichment, Lambda target, 5s batch window, DLQ prod-pipe-dlq. Estimated cost: $0.50/mo base + $0.50/million invocations. Proceed? (yes/no)
  2. aws iam create-role --role-name EventBridgePipes-prod-orders --assume-role-policy-document file://trust-policy.json
  3. aws iam put-role-policy --role-name EventBridgePipes-prod-orders --policy-name pipe-permissions --policy-document file://permissions.json
  4. aws sqs create-queue --queue-name prod-pipe-dlq
  5. aws pipes create-pipe --name prod-orders-pipe --role-arn arn:aws:iam::111111111111:role/EventBridgePipes-prod-orders --source "arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01T00:00:00.000" --source-parameters '{"DynamoDBStreamParameters":{"StartingPosition":"LATEST","BatchSize":100,"MaximumBatchingWindowInSeconds":5,"MaximumRecordAgeInSeconds":3600,"MaximumRetryAttempts":3,"OnPartialBatchItemFailure":"AUTOMATIC_BISECT","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq"}}}' --filter-criteria '{"Filters":[{"Pattern":"{\"dynamodb\":{\"NewImage\":{\"status\":{\"S\":\"CONFIRMED\"}}}}"}]}' --enrichment "arn:aws:lambda:us-east-1:111111111111:function:orders-enrich" --target "arn:aws:lambda:us-east-1:111111111111:function:orders-processor" --target-parameters '{"LambdaParameters":{"InvocationType":"REQUEST_RESPONSE"}}'
  6. aws pipes start-pipe --name prod-orders-pipe
POST_VERIFY:
  - (pending execution)
  - describe-pipe returns CurrentState=RUNNING
  - Sample order with status=CONFIRMED triggers orders-enrich then orders-processor within 10s
  - Sample order with status=PENDING is filtered out (no target invocation)
  - DLQ prod-pipe-dlq receives no messages under normal operation; inject poison record to verify DLQ
SOURCE: DynamoDB Streams arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01 region us-east-1
FILTER: {"dynamodb":{"NewImage":{"status":{"S":"CONFIRMED"}}}}
ENRICHMENT: Lambda arn:aws:lambda:us-east-1:111111111111:function:orders-enrich
TARGET: Lambda arn:aws:lambda:us-east-1:111111111111:function:orders-processor
BATCH: window 5s size 100 retry 3 age 3600s
DLQ: arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq (pipe-level)
NOTES:
  - Filter selectivity ~30% (only CONFIRMED orders reach enrichment). Estimate target invocations = source records x 0.30.
  - Enrichment runs on full batch of up to 100 records; throws on any record -> entire batch retried.
  - OnPartialBatchItemFailure=AUTOMATIC_BISECT: poison record isolated via bisection within 3-4 retries.
  - Cost: $0.50/mo per pipe base + $0.50 per million invocations (DDB Streams throughput-priced separately).
```

## NEVER (top 5)

These are the highest-impact, most-frequent failure modes in
EventBridge Pipes deployments. Violating any one of these is a
correctness or security regression.

1. **NEVER rely on target's own event-source mapping.** A Pipe from
   DynamoDB Streams → Lambda does NOT use Lambda's
   `create-event-source-mapping`. The Pipe's own role reads the stream
   and invokes the target. Configuring both a Pipe AND a Lambda
   event-source mapping on the same stream double-delivers records.

2. **NEVER configure a pipe-level `DeadLetterConfig` for an SQS source
   and expect it to catch poison messages.** For SQS sources, the DLQ
   is on the **source queue** via `RedrivePolicy` — the pipe-level
   `DeadLetterConfig` is silently ignored. Always configure the source
   queue's `RedrivePolicy` with `maxReceiveCount` for SQS-sourced pipes.

3. **NEVER deploy without verifying the target resource policy grants
   invoke to `pipes.amazonaws.com` (or the pipe role ARN).** For Lambda,
   Step Functions, API Gateway targets, a missing resource-based policy
   causes silent invocation failures (visible only in CloudWatch metrics
   for the pipe). The IAM role alone is NOT sufficient for
   resource-based policy targets.

4. **NEVER set `MaximumBatchingWindowInSeconds` > 0 for latency-critical
   SQS workloads without measuring.** For SQS sources the batching
   window IS applied (despite general guidance that "SQS ignores it") —
   the higher the window, the longer the end-to-end latency. For SQS,
   prefer `BatchSize` alone with window=0 unless you specifically need
   batch coalescing.

5. **NEVER deploy an MSK or self-managed Kafka source without an
   explicit `ConsumerGroupID`.** Two pipes sharing a consumer group
   split partitions between them (throughput halved per pipe); two
   pipes with different consumer groups each receive all records
   (duplicate processing). Pick the consumer group deliberately based
   on fan-out semantics.

## Expert heuristic: when to use enrichment vs. inline target Lambda

The enrichment stage is optional. The heuristic below resolves whether
to put transformation logic in an enrichment Lambda or in the target
Lambda itself.

| Signal | Choose |
|---|---|
| Transformation reuses the same lookup/join across multiple pipes | Enrichment Lambda (DRY, one function reused) |
| Transformation is per-record validation with selective drop | Target Lambda (enrichment can't drop individual records) |
| Transformation is schema reshape for a Step Functions target | Enrichment Lambda (Step Functions input must be shaped correctly) |
| Transformation is a synchronous external API call | API Destination enrichment (no code) or API Gateway enrichment (existing endpoint) |
| Transformation + business logic are coupled in one function | Target Lambda (skip enrichment, keep it simple) |
| Multiple stages needed (e.g., lookup + transform + validate) | Step Functions enrichment (Express Workflow for sync) |
| Cost optimization: large batches vs. fine-grained invocations | Enrichment reduces target invocations when multiple records can be coalesced into one target call |

**Decision rules:**

- Default: target Lambda only. Add enrichment when (a) the same
  transformation is used across 2+ pipes, OR (b) the target is Step
  Functions / Batch / Redshift / SageMaker and needs pre-shaped input.
- Enrichment Lambda runs on the **batched payload** — it can drop
  records only by returning a smaller batch, not by selectively
  filtering per record across retry boundaries.
- For API Gateway / API Destination enrichment, the external endpoint
  must return within the pipe's batch window or the batch fails.
- Enrichment failures retry the ENTIRE batch — keep enrichment logic
  idempotent.

ALWAYS emit the enrichment decision as a PRE_CHECKS row naming the
enrichment ARN, target ARN, and the rationale (DRY, schema-reshape,
cost).

## Recent AWS features (2024-2026)

- **AWS Batch target (2024-2025):** EventBridge Pipes supports AWS Batch
  job queues as a target. Pipe submits a Batch job per batched payload
  — enables event-driven batch processing without a separate consumer
  Lambda. Pipe role requires `batch:SubmitJob` plus `iam:PassRole` on
  the job role.

- **Enrichment transformations (2024-2025):** documented patterns for
  enrichment Lambda returning a transformed batch payload. Useful for
  fan-in (joining customer data before target invocation), schema
  reshape (CSV → JSON for Step Functions), or coalescing (multiple
  records → one target call to reduce invocations).

- **OnPartialBatchItemFailure `AUTOMATIC_BISECT` (2024):** for DynamoDB
  Streams, Kinesis, and SQS sources, the pipe automatically bisects a
  failing batch to isolate poison records — prevents one bad record
  from blocking the whole batch.

- **Self-managed Kafka source (2024):** Pipes can consume from
  self-managed Kafka clusters (including MSK Serverless, Confluent
  Cloud, on-prem clusters via VPC). Requires `ServerRootCA`,
  `VpcSubnets`, `SecurityGroups`, and `AuthType`.

- **Amazon MQ source (2023-2024):** Pipes consume from Amazon MQ
  ActiveMQ and RabbitMQ brokers. Requires Secrets Manager credentials
  secret with `username`/`password` keys.

- **Redshift and SageMaker targets (2024):** Pipes can write directly
  to Redshift (Serverless or Provisioned) via the Redshift Data API
  and trigger SageMaker Pipelines. Enables event-driven ML inference
  and data ingestion without Lambda glue.

- **API Destination target and enrichment (2024):** Pipes can invoke
  API Destinations as enrichment (pre-transform via external HTTPS) or
  as target (fan-out to external webhook). Requires Connection resource
  with auth config.

## AWS documentation

- **AWS EventBridge Pipes User Guide** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes.html
- **EventBridge Pipes sources** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes-event-source.html
- **EventBridge Pipes targets** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipe-targets.html
- **EventBridge Pipes enrichment** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes-enrichment.html
- **Amazon MSK as a Pipe source** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes-msk.html
- **Amazon MQ as a Pipe source** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes-mq.html
- **Self-managed Kafka as a Pipe source** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes-self-managed-kafka.html
- **EventBridge Pipes IAM** — https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-pipes-permissions.html
- **EventBridge Pipes API Reference** — https://docs.aws.amazon.com/eventbridge/latest/APIReference/API_Operations_Amazon_EventBridge_Pipes.html
