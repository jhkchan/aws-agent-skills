---
name: eventbridge-pipe-deployer
description: Provisions production-grade Amazon EventBridge Pipes connecting sources (DynamoDB Streams, Kinesis, SQS, MSK, Amazon MQ, self-managed Kafka) to targets (Lambda, Step Functions, EventBridge bus, SQS, SNS, ECS, API Gateway, API Destination, Redshift, SageMaker, AWS Batch) with optional filter patterns, optional enrichment (Lambda, Step Functions, API Gateway, API Destination), batch windowing, dead-letter queue, and correct IAM roles. Emits READY_TO_DEPLOY with an ordered CLI plan or PREREQUISITES_MISSING with the specific gap. Use when wiring a streaming source to a downstream target via Pipes, configuring batch windows and DLQs, adding enrichment transformations, or routing Kafka/MSK topics to Step Functions.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan generation. Live deployment uses aws pipes create-pipe, update-pipe, start-pipe, describe-pipe, tag-resource, aws iam create-role, attach-role-policy, aws sqs create-queue, get-queue-attributes, aws dynamodbstreams describe-stream, aws kinesis describe-stream, aws kafka describe-cluster, aws mq describe-broker, and aws lambda add-permission (AWS CLI v2, SSO or key-based...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a new EventBridge Pipe from a streaming or polling source to a downstream target, configuring batch windowing and concurrency, attaching a dead-letter queue for failed events, inserting an enrichment step (Lambda, Step Functions, API Gateway, API Destination), wiring an AWS Batch or Redshift or SageMaker target, configuring a filter pattern to pre-filter source records, or sourcing from MSK / Amazon MQ / self-managed Kafka.
  activation_triggers: create EventBridge Pipe, deploy EventBridge Pipe, DynamoDB Streams to Lambda pipe, Kinesis to Step Functions pipe, SQS to Lambda pipe, MSK source pipe, Amazon MQ source pipe, self-managed Kafka pipe, pipe enrichment Lambda, pipe enrichment Step Functions, pipe filter pattern, pipe batch window, MaximumBatchingWindowInSeconds, pipe DLQ, EventBridge Pipe IAM role, pipe to EventBridge bus, pipe to ECS task, pipe to API Destination, pipe to Redshift, pipe to SageMaker, pipe to AWS Batch
  invocation_schema: 'Input (one of): (a) a deployment spec — source (DynamoDB Streams / Kinesis / SQS / MSK / Amazon MQ / self-managed Kafka), optional filter pattern, optional enrichment (Lambda / Step Functions / API Gateway / API Destination), target (Lambda / Step Functions / EventBridge bus / SQS / SNS / ECS / API Gateway / API Destination / Redshift / SageMaker / Batch), batch window and batch size, DLQ ARN, IAM role configuration; (b) a partial spec for interactive refinement; (c) an existing pipe ARN for review against the well-architected checklist. Output: PIPE_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS — where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: EventBridge Pipes, pipe deploy, DynamoDB Streams source, Kinesis source, SQS source, MSK source, Amazon MQ source, self-managed Kafka, Lambda target, Step Functions target, EventBridge bus target, SQS target, SNS target, ECS task target, API Gateway target, API Destination target, Redshift target, SageMaker target, AWS Batch target, enrichment Lambda, enrichment Step Functions, filter pattern, batch window, MaximumBatchingWindowInSeconds, MaximumBatchSize, dead-letter queue, DLQ, pipe IAM role, enrichment transformation
  tags: eventbridge, pipes, app-integration, event-driven, deploy, streaming, dlq, batch-window, enrichment
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

Mindset prose (pipe as point-to-point stream processor, pipe-as-poller, source-dependent batch windows, separate enrichment/target stages) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand framing a Pipe deployment.

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

Live-account pre-flight verification commands (IAM rights, source/target/enrichment state, DLQ policy, MSK AuthType, MQ credentials secret) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand running pre-checks against a live account.

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

Step 0 expert-knowledge bullets (pipe-as-poller, two independent permissions, SQS batch-window exception, DLQ behaviour by source type, enrichment on the batched payload, consumer groups, filter placement, OnPartialBatchItemFailure) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand a plan depends on a non-obvious Pipe behaviour.

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

Step 7 IAM trust-policy JSON plus the per-source and per-enrichment/target permission matrices moved verbatim to [references/iam-and-dlq-guide.md](references/iam-and-dlq-guide.md).
Load on demand generating the pipe role trust and permissions policies.

## Common patterns

Common Pipe patterns (DDB Streams→Lambda, Kinesis→Step Functions, SQS→Lambda, MSK→Batch, DDB Streams→enrichment→Step Functions) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand selecting a boilerplate pattern.

## Output format

The PIPE_SPEC/ARCHITECTURE/CHECKLIST/FINDINGS/DEPLOY_COMMANDS output template moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand formatting the architecture summary block.

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

The enrichment-vs-inline-target decision table and rules moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand choosing where transformation logic belongs.

## Recent AWS features (2024-2026)

Recent AWS features (Batch target, enrichment transformations, AUTOMATIC_BISECT, self-managed Kafka, Amazon MQ, Redshift/SageMaker targets, API Destination) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand checking whether a newer AWS feature changes the plan.

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

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — the common Pipe patterns and the PIPE_SPEC output-format template, moved from SKILL.md.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live-account pre-flight verification commands (IAM, source/target/enrichment state, DLQ policy, MSK auth, MQ credentials), moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset, Step 0 expert knowledge, the enrichment-vs-inline-target heuristic, and recent AWS features, moved from SKILL.md.
- [references/iam-and-dlq-guide.md](references/iam-and-dlq-guide.md) — pipe role permission templates, plus the Step 7 trust-policy JSON and per-source/per-target permission matrices moved from SKILL.md.
- [references/sources-and-targets.md](references/sources-and-targets.md) — source/target matrices, batch behavior, filter pattern rules, MSK/MQ guides.
