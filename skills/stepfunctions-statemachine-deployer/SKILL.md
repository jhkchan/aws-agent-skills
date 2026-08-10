---
name: stepfunctions-statemachine-deployer
description: Provisions production-grade AWS Step Functions state machines with correct type selection (Standard exactly-once up to 1 year vs Express at-least-once up to 5 min), Amazon States Language definitions
  (Task, Choice, Parallel, Map, Wait, Pass, Fail, Succeed), service integrations via Resource ARN patterns (Lambda, DynamoDB, SQS, SNS, ECS, SageMaker, Glue, Athena, Bedrock), sync (.sync) vs callback (.waitForTaskToken)
  invocation patterns, error handling (Retry with exponential backoff, Catch routing), Inline Map (40 concurrent) vs Distributed Map (10000+ concurrent with S3/DynamoDB ItemReader, ItemBatcher, toleratedFailurePercentage),
  IAM least-privilege execution role, input/output processing (InputPath, ResultPath, OutputPath, Parameters), Express sync (RequestResponse) vs async (Firehose logging) workflows, and AWS SDK service integrations
  for direct API calls without Lambda. Emits a READY_TO_DEPLOY checklist. Use when provisioning state machines, designing ASL workflows, configuring service.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture planning. Live deployment uses aws stepfunctions create-state-machine,
  update-state-machine, describe-state-machine, validate-state-machine-definition, start-execution, and aws iam create-role / attach-role-policy (AWS CLI v2, SSO or key-based credentials).
keywords:
- Step Functions
- state machine
- ASL
- Amazon States Language
- Standard workflow
- Express workflow
- Task state
- Choice state
- Parallel state
- Map state
- Distributed Map
- Inline Map
- Retry
- Catch
- error handling
- service integration
- Resource ARN
- waitForTaskToken
- sync integration
- callback pattern
- Task Token
- IAM execution role
- states:StartExecution
- InputPath
- ResultPath
- OutputPath
- Parameters
- ItemReader
- ItemBatcher
- Bedrock invocation
- AWS SDK integration
- Step Functions Playground
tags:
- stepfunctions
- app-integration
- deploy
- state-machine
- asl
- express
- standard
- distributed-map
- service-integration
- iam
- error-handling
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
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Provisioning a new Step Functions state machine, choosing between Standard and Express workflow types, designing an ASL definition with service integrations (Lambda, DynamoDB, SQS, ECS, Glue,
    Bedrock), configuring Retry/Catch error handling, building a Distributed Map for large-scale fan-out, scoping the IAM execution role to specific resource ARNs, choosing between sync (.sync) and callback
    (.waitForTaskToken) integration patterns, or hardening an Express workflow for production.
  activation_triggers:
  - create a state machine
  - deploy Step Functions workflow
  - Standard vs Express workflow
  - write ASL definition
  - service integration Resource ARN
  - Retry and Catch blocks
  - Distributed Map state
  - waitForTaskToken callback
  - Step Functions execution role
  - Step Functions + Lambda orchestration
  - Step Functions + Bedrock
  - Express workflow synchronous
  invocation_schema: 'Input shape (one of): (a) a deployment specification including workflow name, type (STANDARD | EXPRESS), ASL definition (or requirements to derive one), service integrations, error-handling
    requirements, and execution role scope; (b) a partial spec for interactive refinement (e.g., "Express workflow invoking Lambda + DynamoDB, sync, 60s budget"); (c) an existing state machine ARN for architecture
    review against the well-architected checklist. Output shape: { STATE_MACHINE_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING,
    ERROR }.'
---

# Step Functions State Machine Deployer

## Mindset

**One-line takeaway:** a production state machine is not "a JSON definition
plus a role" — it is an **orchestration contract** where the workflow type,
the service integration pattern, the error-handling semantics, and the IAM
role scope must each be a deliberate decision. The ASL syntax is the least
interesting part; the **type semantics, integration pattern, and Retry/Catch
shape** determine cost, durability, and blast radius.

Three facts make Step Functions provisioning different from "write a JSON":

- **Workflow type is a durability + cost decision, not a syntax decision.**
  Standard workflows bill per state transition ($0.025 per 1,000); Express
  workflows bill per invocation + duration ($1.00 per million invocations).
  Standard guarantees exactly-once execution semantics and supports runs up
  to 1 year. Express is at-least-once and caps at 5 minutes. A high-volume
  event-driven workload on Standard can balloon cost 100x versus Express; a
  long-running compensation saga on Express is impossible — the 5-minute cap
  kills it. Type is decided FIRST, before any ASL is written.

- **The Resource ARN suffix selects the integration semantics, not the
  service.** `arn:aws:states:::lambda:invoke` fires-and-forgets;
  `arn:aws:states:::lambda:invoke.sync` does not exist (Lambda is already
  sync); `arn:aws:states:::ecs:runTask.sync` waits for the task to complete;
  `arn:aws:states:::sqs:sendMessage.waitForTaskToken` pauses the workflow
  until an external worker calls `SendTaskSuccess`. Getting the suffix wrong
  produces either silent fire-and-forget bugs or stuck executions.

- **A fallible Task without Retry AND Catch fails the entire execution on
  the first transient error.** ASL does NOT auto-retry. Lambda
  `ServiceException`, DynamoDB `ProvisionedThroughputExceededException`, and
  ECS `CapacityProviderInsufficientCapacity` are all transient — without an
  explicit `Retry` block, the workflow dies and must be re-run from the top
  (Standard) or lost entirely (Express async). Production Tasks require
  BOTH `Retry` (for transient errors) and `Catch` (for terminal fallback).

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Dimension → requirement table (type, ASL, integration, error handling, role, observability) | Identify which dimensions your spec touches |
| **§ Pre-flight** | Required inputs gate (role ARN, type, definition) — blocks on missing | Before producing any plan |
| **§ Process** | Ten-step architecture planning walk (type → ASL → integration → Map → error handling → I/O → role → logging → Express → verification) | Walk in order for every deployment |
| **§ Output format** | STATE_MACHINE_SPEC / VERDICT / ARCHITECTURE / CHECKLIST / FINDINGS / DEPLOY_COMMANDS template | Format the response |
| **§ Verification commands** | Post-deploy CLI checks (describe, start-execution, CloudWatch) | After `create-state-machine` returns |
| **§ Anti-Patterns** | NEVER list — common deployment mistakes (wildcard role, missing Retry, .sync on Lambda, Express > 5min) | Review before concluding READY_TO_DEPLOY |
| **§ References** | Deeper docs on ASL states and Resource ARN patterns | When you need the full integration catalog |

## Quick reference — deployment checklist

| Dimension | Requirement | Step |
|---|---|---|
| Workflow type | STANDARD (exactly-once, ≤1yr, $0.025/1k transitions) OR EXPRESS (at-least-once, ≤5min, $1.00/M invocations) — deliberate choice | Step 1 |
| ASL definition | Validated JSON; every Task has explicit `TimeoutSeconds`; StartAt chain reaches terminal state | Step 2 |
| Service integrations | Resource ARNs use correct suffix: bare (fire-and-forget), `.sync` (wait), `.waitForTaskToken` (callback) | Step 3 |
| Sync vs callback | `.sync` for run-to-completion (ECS, Glue, Athena); `.waitForTaskToken` for human/external approval | Step 4 |
| Map state | Inline (≤40 concurrent, ≤256KB input) OR Distributed (≤10000+ concurrent, S3/DynamoDB ItemReader, ItemBatcher) | Step 5 |
| Error handling | Every fallible Task has BOTH `Retry` (ErrorEquals, IntervalSeconds, MaxAttempts, BackoffRate) AND `Catch` (ErrorEquals, Next, ResultPath) | Step 6 |
| I/O processing | InputPath, ResultPath, OutputPath, Parameters used deliberately; payload < 256KB (Standard) / < 256KB (Express) | Step 7 |
| IAM role | Trust policy includes `states.amazonaws.com`; identity policy scoped to named actions on specific ARNs from the definition; no `Action: "*"` | Step 8 |
| Logging (Express) | `LoggingConfiguration.level: ALL` + `includeExecutionData: true` — the ONLY durable record for Express | Step 9 |
| Tracing (Standard) | `TracingConfiguration.enabled: true` + role grants `xray:PutTraceSegments` | Step 9 |
| Express invocation mode | `Synchronous` (RequestResponse — caller blocks ≤5min) vs `Asynchronous` (Firehose logging, caller gets exec ARN) | Step 10 |

## Pre-flight: deployment specification gate (run before architecture output)

Before producing the deployment plan, validate the input specification.
Several requirements **block deployment** — proceeding with an invalid spec
produces a non-functional or insecure state machine.

**Live-account pre-flight checks (skip if doing offline architecture plan):**
1. Verify the caller has `states:CreateStateMachine`,
   `states:ValidateStateMachineDefinition`, `iam:CreateRole`,
   `iam:AttachRolePolicy`, and `iam:PassRole` on the execution role ARN.
   Surface IAM gaps BEFORE emitting deployment commands.
2. Validate the ASL definition structure:
   `aws stepfunctions validate-state-machine-definition --definition file://def.json --type STANDARD`
   This catches syntax errors before the API reject at `create-state-machine`.
3. Verify the execution role's trust policy includes
   `Principal: { Service: "states.amazonaws.com" }` — `CreateStateMachine`
   accepts any role ARN without validating trust, but the workflow fails on
   first integration at runtime with `AccessDenied`.
4. Check service quotas: Standard has no per-account execution cap; Express
   has a soft account-level launch quota (default 100,000/sec, raisable).

| Attribute | Value | Effect on plan |
|---|---|---|
| `name` | Valid name (`[a-zA-Z0-9-_]{1,80}`) | Required — `CreateStateMachine` rejects others |
| `type` | `STANDARD` | Exactly-once, ≤1 year, per-transition billing. Default. |
| `type` | `EXPRESS` | At-least-once, ≤5 min, per-invocation billing. Required for high-throughput event-driven workloads. |
| `definition` | Stringified ASL JSON | API expects `"{\"StartAt\":...}"` — a STRING, not parsed object. Terraform/CloudFormation footgun. |
| `roleArn` | Existing role ARN with trust to `states.amazonaws.com` | Required. If absent, emit PREREQUISITES_MISSING. |
| `loggingConfiguration` | For Express: `level: ALL`, `includeExecutionData: true` | Mandatory for Express — execution history expires in minutes. |
| `tracingConfiguration` | For Standard: `enabled: true` | Recommended — X-Ray only honored on Standard. |

**If the deployment spec is incomplete** (missing role ARN, missing workflow
type, or missing definition), output:

```text
STATE_MACHINE_SPEC: <name-or-unknown>
VERDICT: PREREQUISITES_MISSING
REASON: Deployment specification is missing required fields (<list>).
Cannot produce a deployment plan without <field> — the resulting state
machine would be non-functional or insecure.
REQUIRED:
  - name (1-80 chars, [a-zA-Z0-9-_])
  - type (STANDARD or EXPRESS)
  - definition (ASL JSON, stringified for the API)
  - roleArn (existing role trusting states.amazonaws.com)
  - loggingConfiguration (for EXPRESS: level ALL + includeExecutionData)
```

## Process — Architecture planning (apply in order, produce deployment plan)

### Step 0: Expert knowledge — non-obvious Step Functions behaviors that change the plan

These behaviors are easy to misjudge without operational Step Functions
experience. Each changes the architecture if ignored:

- **Standard bills per state transition; Express bills per invocation +
  duration.** Standard: $0.025 per 1,000 transitions. A 10-state workflow
  running 1M times/day = 10M transitions = $250/day. The same workload on
  Express at 100ms average duration = $1.00 per 1M invocations + ~$0.5/M
  GB-sec = ~$1.50/day. For high-volume idiomatic workloads, Express is
  ~100x cheaper. For long-running sagas, Standard is the only option.

- **Express at-least-once means Tasks MUST be idempotent.** Express
  workflows can retry a Task on internal failure — the integration is
  invoked MORE THAN ONCE. A non-idempotent Task (e.g., `dynamodb:PutItem`
  without idempotency key, or SQS SendMessage without dedup) produces
  duplicates. Standard does not have this issue (exactly-once).

- **Express execution history expires in 5 minutes (sync) or 1 hour
  (async).** Without `LoggingConfiguration.level: ALL` +
  `includeExecutionData: true`, an Express execution is forensic-black-hole
  after 5-60 minutes. Standard retains 90 days via API/console. This is
  why logging is a CRITICAL severity finding on Express.

- **`TracingConfiguration.enabled: true` is a NO-OP on Express.** The API
  accepts the field silently; no X-Ray traces are produced. Express
  distributed visibility uses CloudWatch Logs ServiceLens (weaker). Standard
  honors the field and emits full X-Ray segments per state transition.

- **A Task without explicit `TimeoutSeconds` defaults to 60 seconds.**
  Lambda functions configured with timeout > 60s are silently killed by
  Step Functions at 60s — the Lambda invocation continues (and bills) but
  the state advances to `States.Timeout`. Always set `TimeoutSeconds`
  based on the integration's expected runtime.

- **`HeartbeatSeconds` is REQUIRED for Activity-based Tasks.** A Task with
  `Resource: arn:aws:states:<region>:<account>:activity:<name>` relies on
  an external worker calling `GetActivityTask` + `SendTaskHeartbeat`.
  Without `HeartbeatSeconds`, a dead worker is not detected until
  `TimeoutSeconds` (potentially hours).

- **`Retry` and `Catch` are NOT interchangeable.** `Retry` re-executes the
  SAME state (for transient errors). `Catch` routes to a DIFFERENT state
  (the error handler). `Retry` without `Catch` still fails the execution
  if retries exhaust. `Catch` without `Retry` does not retry transient
  errors. Production Tasks require BOTH.

- **Default `Retry` parameters (IntervalSeconds=1, MaxAttempts=3,
  BackoffRate=2.0) are reasonable but should be explicit.** A `Retry`
  block with only `ErrorEquals` and no other fields uses these defaults.
  Make them explicit so reviewers can audit the backoff curve.

- **`MaxConcurrency: 0` on a Map means UNBOUNDED.** The default is 0, which
  means Step Functions invokes iterations as fast as possible. For >100
  items, this overwhelms downstream services (Lambda concurrency,
  DynamoDB throttling). Always set an explicit `MaxConcurrency`.

- **Inline Map caps at 40 concurrent iterations and 256KB total payload.**
  Beyond that, use Distributed Map. Distributed Map supports up to 10,000+
  concurrent iterations and reads directly from S3 or DynamoDB via
  `ItemReader` without loading items into the workflow payload.

- **Distributed Map runs under a SEPARATE child execution.** Each
  Distributed Map iteration is its own Step Functions execution with its
  own execution history. The parent workflow's `MaxConcurrency` controls
  child-execution fan-out. The child executions bill separately.

- **`.sync` waits for the integration to complete; the workflow is billed
  for the wait.** `arn:aws:states:::ecs:runTask.sync` blocks the Task until
  the ECS task finishes — the state transition is "in progress" for the
  task duration. On Standard, this is one transition (cheap); on Express,
  this counts against the 5-minute cap. Long ECS/Glue jobs on Express
  are impossible.

- **`.waitForTaskToken` pauses indefinitely (up to 1 year on Standard).**
  The Task returns a Task Token; the workflow pauses until an external
  worker calls `SendTaskSuccess` or `SendTaskFailure`. The Token is valid
  for 1 year on Standard, 5 minutes on Express (essentially unusable on
  Express for human-approval patterns).

- **`definition` is a STRING in the API, not a JSON object.**
  `CreateStateMachine` expects `"definition": "{\"StartAt\": ...}"`
  (stringified ASL). Terraform's `jsonencode()` handles this; raw
  CloudFormation requires `!Sub` with JSON-string escape. Passing a parsed
  object fails with `InvalidDefinition`.

- **`States.ALL` does NOT match `States.Timeout` in older runtime
  versions.** State machines created before November 2022 with
  `Catch: [{"ErrorEquals": ["States.ALL"]}]` miss the timeout path. For
  long-running production workflows, list `States.Timeout` explicitly
  alongside `States.ALL`.

- **The execution role's trust policy MUST include
  `states.amazonaws.com`.** `CreateStateMachine` does NOT validate the
  trust policy — it accepts any role ARN. At runtime, the first service
  integration fails with `AccessDenied`. Always verify the trust policy
  separately.

- **AWS SDK integrations allow direct API calls without Lambda.**
  `arn:aws:states:::aws-sdk:dynamodb:query` invokes the DynamoDB Query
  API directly — no Lambda glue code needed. This is the modern pattern
  for single-API-call Tasks. Resource ARN format:
  `arn:aws:states:::aws-sdk:<service>:<action>`.

- **Bedrock model invocation is a first-class integration.**
  `arn:aws:states:::bedrock:invokeModel` synchronously invokes a Bedrock
  model from a Task. The role needs `bedrock:InvokeModel` on the model
  ARN. Async invocation uses
  `arn:aws:states:::bedrock:invokeModel.sync` (Standard only).

- **RedriveExecution (November 2024) changes the recovery calculus for
  failed Standard executions.** A failed Standard execution can be
  redriven from the point of failure after fixing the definition — without
  re-running already-succeeded states. Express does NOT support redrive.
  Build Catch blocks that route to a state which can be safely re-run on
  redrive.

### Step 1: Workflow type selection (STANDARD vs EXPRESS)

This is the single highest-leverage decision. Everything downstream
(error handling, logging, Map state, callback patterns) is constrained by
the type.

| Dimension | STANDARD | EXPRESS |
|---|---|---|
| Execution semantics | Exactly-once | At-least-once (Tasks MUST be idempotent) |
| Max duration | 1 year (31,536,000 seconds) | 5 minutes (300 seconds) |
| Billing | $0.025 per 1,000 state transitions | $1.00 per 1M invocations + GB-sec duration |
| Execution history | 90 days via API/console | 5 min (Synchronous) / 1 hour (Asynchronous) |
| X-Ray tracing | Honored via `TracingConfiguration` | NO-OP — use CloudWatch ServiceLens |
| Callback (`.waitForTaskToken`) | Supported, up to 1 year | Supported, but capped at 5 min — practical only for fast external systems |
| Distributed Map child executions | Billed per transition (parent + children) | Billed per child invocation |
| Ideal workload | Long saga, multi-step approval, batch with human steps | High-volume event-driven (Kinesis/IoT/EventBridge fan-in), API Gateway sync backend |

**Decision rule:**
- If any Task can take > 5 minutes (Glue, Athena, ECS long task, human approval) → STANDARD.
- If the workload is high-volume (>1000 executions/sec) and each run is < 5 min → EXPRESS.
- If Tasks are non-idempotent and cannot be made idempotent → STANDARD.
- If the workload needs X-Ray distributed tracing → STANDARD.
- If unsure, default STANDARD; Express is a deliberate optimization for cost/throughput.

### Step 2: ASL definition design

The Amazon States Language (ASL) defines the workflow as a JSON object
with `StartAt`, `States`, and terminal transitions. Each state has a
`Type` that determines its fields:

| State Type | Purpose | Required fields | Common pitfalls |
|---|---|---|---|
| `Task` | Invoke a service integration | `Resource`, `Next` (or `End: true`) | Missing `TimeoutSeconds` (defaults 60s); missing `Retry`/`Catch` on fallible Resources |
| `Choice` | Branch on input | `Choices[]`, `Default` | Missing `Default` is invalid ASL; `StringEquals` is case-sensitive |
| `Parallel` | Run branches concurrently | `Branches[]`, `Next` | Errors in any branch fail the whole state; needs per-branch Catch |
| `Map` | Iterate over a collection | `Iterator`, `ItemsPath`, `MaxConcurrency` | Inline Map caps 40 concurrent; Distributed Map needs `ItemReader` |
| `Wait` | Pause for time/absolute time | `Seconds`/`SecondsPath`/`Timestamp`/`TimestampPath` | Standard only meaningful; Express caps total at 5 min |
| `Pass` | Transform input, no integration | `Result`, `ResultPath`, `Next` | Useful for scaffolding/Parameters construction |
| `Fail` | Terminal failure | `Error`, `Cause` | `Cause` is a static string — use `Parameters`-driven Pass before Fail for dynamic error context |
| `Succeed` | Terminal success | (none) | Clean exit |

**Walk the definition before deploying:**
1. From `StartAt`, follow `Next` / `Default` / `Catch.Next` — every path
   must reach a terminal (`End: true` or a `Fail`/`Succeed`).
2. Flag any unreachable state (no inbound transition).
3. Flag any cycle with no exit (a `Task.Next` to itself with no
   `Retry`/`Catch` that can break out).
4. Verify every `Task` has an explicit `TimeoutSeconds` (no silent 60s
   default).
5. Verify every fallible `Task` has at least one `Retry` AND at least
   one `Catch`.

### Step 3: Service integrations — Resource ARN patterns

The `Resource` field of a `Task` state selects both the service AND the
integration semantics via the ARN suffix:

| Resource pattern | Semantics | Typical use |
|---|---|---|
| `arn:aws:states:::lambda:invoke` | Fire-and-forget (Lambda is already sync) | Function invocation |
| `arn:aws:states:::dynamodb:getItem` / `putItem` / `updateItem` / `deleteItem` | Direct DynamoDB API (no Lambda) | CRUD on a single item |
| `arn:aws:states:::dynamodb:query` / `scan` | Direct DynamoDB read API | Query by partition key |
| `arn:aws:states:::sqs:sendMessage` | Fire-and-forget | Decouple to a queue |
| `arn:aws:states:::sqs:sendMessage.sync` | (Not meaningful — SendMessage is already sync) | — |
| `arn:aws:states:::sns:publish` | Fire-and-forget | Fan-out notification |
| `arn:aws:states:::ecs:runTask` | Fire-and-forget | Launch a task and move on |
| `arn:aws:states:::ecs:runTask.sync` | Wait for task completion | Long-running batch, returns final result |
| `arn:aws:states:::glue:startJobRun.sync` | Wait for Glue job | ETL pipeline |
| `arn:aws:states:::athena:startQueryExecution.sync` | Wait for Athena query | Interactive analytics |
| `arn:aws:states:::sagemaker:createTrainingJob.sync` | Wait for training job | ML training |
| `arn:aws:states:::sagemaker:createTransformJob.sync` | Wait for batch transform | Batch inference |
| `arn:aws:states:::states:startExecution.sync` | Wait for nested execution (Standard only) | Compose workflows |
| `arn:aws:states:::states:startExecution.waitForTaskToken` | Nested execution with callback | Compose with external signal |
| `arn:aws:states:::sns:publish.waitForTaskToken` | Pause for human/external approval via SNS | Approval workflow |
| `arn:aws:states:::sqs:sendMessage.waitForTaskToken` | Pause for worker via SQS | Async worker pattern |
| `arn:aws:states:::lambda:invoke.waitForTaskToken` | Pause for Lambda-driven callback | External system integration |
| `arn:aws:states:::aws-sdk:<service>:<action>` | Direct AWS SDK call (no Lambda) | Single-API operations (e.g., `aws-sdk:secretsmanager:GetSecretValue`) |
| `arn:aws:states:::bedrock:invokeModel` | Synchronous Bedrock model call | GenAI inference |
| `arn:aws:states:::bedrock:invokeModel.sync` | Async Bedrock invocation (Standard only) | Long-running model |

**Decision tree for suffix:**
- Service call returns immediately (Lambda, SQS SendMessage, SNS Publish) → bare ARN.
- Service call runs to completion you need to wait for (ECS task, Glue job, Athena query, SageMaker training) → `.sync`.
- Workflow pauses pending external signal (human approval, async worker) → `.waitForTaskToken` (the Task receives a `TaskToken` field to pass along; Standard only for > 5min waits).
- Single AWS API call without Lambda glue → `arn:aws:states:::aws-sdk:<service>:<action>`.

### Step 4: Sync vs callback pattern selection

**`.sync` (run-to-completion):**
- The Task blocks until the integration returns a terminal state.
- Use for ECS tasks, Glue jobs, Athena queries, SageMaker training, Bedrock async.
- The Task's `TimeoutSeconds` must exceed the integration's max runtime.
- On Express, the `.sync` wait counts against the 5-min execution cap.

**`.waitForTaskToken` (callback):**
- The Task produces a `TaskToken` (string, ~256 chars). The workflow pauses.
- An external worker calls `SendTaskSuccess(taskToken, output)` or
  `SendTaskFailure(taskToken, error, cause)` to resume or fail the Task.
- Use for human approval, async external systems, long-poll patterns.
- On Standard, the Task can wait up to 1 year. On Express, capped at 5 min
  (effectively unusable for human-approval patterns — use Standard).
- The Token MUST be sent over a secure channel — it is a bearer credential
  for the workflow's state.

**Anti-pattern:** NEVER use `.waitForTaskToken` on Express for human
approval. The 5-min cap will fail the Task before any human responds.

### Step 5: Map state design (Inline vs Distributed)

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

### Step 6: Error handling — Retry and Catch

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

### Step 7: Input/output processing

ASL provides four fields on every state for input/output shaping:

| Field | Operates on | Direction | Common use |
|---|---|---|---|
| `InputPath` | The state's input JSON | Inbound — filters input before `Parameters` | Strip irrelevant fields before processing |
| `Parameters` | Static template + `.$` JSONPath values | Inbound — constructs the integration input | Build the integration's request body from the workflow input |
| `ResultPath` | The state's output JSON | Outbound — controls where the integration's result is merged | Preserve original input alongside result: `"$.result"` |
| `OutputPath` | The state's output JSON | Outbound — filters after `ResultPath` | Select a sub-field of the result to pass forward |

**Pipeline order (apply left-to-right):**
`stateInput → InputPath → Parameters → [integration] → ResultSelector → ResultPath → OutputPath → stateOutput`

**Common pattern: pass-through with enriched output:**
```json
"Task": {
  "Type": "Task",
  "Resource": "arn:aws:states:::lambda:invoke",
  "Parameters": {
    "FunctionName": "Enrich",
    "Payload.$": "$"
  },
  "ResultPath": "$.enriched",
  "OutputPath": "$",
  "Next": "NextState"
}
```

**Payload size limits:** 256KB for the workflow execution input AND each
state's input/output. For larger payloads, use S3 references (pass the S3
URI in the payload, fetch in the next Task) or use Distributed Map.

### Step 8: IAM execution role (least privilege)

The execution role is the identity under which EVERY service integration
runs. Its scope is the workflow's total blast radius.

**Trust policy (mandatory):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "states.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
```

**Identity policy derivation (per-Task audit):**
Walk each `Task` state's `Resource` ARN and grant the corresponding named
action on the specific resource ARN. Example for a workflow invoking two
Lambdas and one DynamoDB table:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "InvokeLambdas",
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:us-east-1:111111111111:function:ChargeOrderFn",
        "arn:aws:lambda:us-east-1:111111111111:function:NotifyCompleteFn"
      ]
    },
    {
      "Sid": "DynamoDBAccess",
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem"],
      "Resource": "arn:aws:dynamodb:us-east-1:111111111111:table/OrdersTable"
    }
  ]
}
```

**Special permissions by integration pattern:**
- `.sync` on ECS: needs `ecs:RunTask`, `ecs:DescribeTasks`, `ecs:StopTask`,
  and `iam:PassRole` (for the ECS task role).
- `.waitForTaskToken`: needs `states:SendTaskSuccess`,
  `states:SendTaskFailure`, `states:SendTaskHeartbeat` — usually granted
  to the external worker, not the execution role.
- Distributed Map reading from S3: needs `s3:GetObject` on the source
  bucket/key.
- Bedrock: needs `bedrock:InvokeModel` on the model ARN.
- Standard with X-Ray: needs `xray:PutTraceSegments` +
  `xray:PutTelemetryRecords`.
- Logging to CloudWatch: needs `logs:CreateLogDelivery`,
  `logs:PutLogEvents`, `logs:DescribeLogGroups`, `logs:GetLogDelivery`,
  `logs:UpdateLogDelivery`.

**NEVER use `Action: "*"` on the execution role.** This is
admin-equivalent — one compromised state machine = full account
compromise.

### Step 9: Logging and tracing

**Express workflows (logging is MANDATORY):**
```json
"LoggingConfiguration": {
  "Level": "ALL",
  "IncludeExecutionData": true,
  "Destinations": [{
    "CloudWatchLogsLogGroup": { "LogGroupArn": "arn:aws:logs:us-east-1:111111111111:log-group:/aws/states/myworkflow:*" }
  }]
}
```
- `Level: ALL` + `IncludeExecutionData: true` is the only meaningful config.
- `Level: OFF`/`ERROR`/absent → no durable record (Express history expires
  in 5-60 min).
- The log group's ARN MUST end with `:*` (the trailing wildcard is
  required by Step Functions).
- The role MUST grant `logs:CreateLogDelivery`, `logs:PutLogEvents`,
  `logs:DescribeLogGroups`, `logs:GetLogDelivery`, `logs:UpdateLogDelivery`.

**Standard workflows (tracing is recommended):**
```json
"TracingConfiguration": { "Enabled": true }
```
- Honored only on Standard — silently no-op on Express.
- Role MUST grant `xray:PutTraceSegments` + `xray:PutTelemetryRecords`.
- Standard logging is optional (90-day history via API is a fallback) but
  recommended for CloudWatch alarms and metric filters.

### Step 10: Express invocation mode

Express workflows have TWO invocation modes, set at `StartExecution` time:

| Mode | Caller experience | Use case |
|---|---|---|
| `Synchronous` (RequestResponse) | Caller blocks until completion or 5-min cap; response includes final output | API Gateway backend, real-time request/response |
| `Asynchronous` | Caller gets execution ARN immediately; result via CloudWatch Logs / EventBridge | High-volume fan-in (Kinesis, IoT, EventBridge) |

For Synchronous Express, `StartExecution` is called via the
`sync-execution` API endpoint. Errors in any state return directly to the
caller as the HTTP response. Set Express-Sync workflows' `StartAt` Task's
`TimeoutSeconds` well under 5 minutes — the 5-min cap is a hard wall.

For Asynchronous Express, configure EventBridge to emit on
`Step Functions Execution Status Change` for downstream alerting.

## Output format (per state machine deployment plan)

```text
STATE_MACHINE_SPEC: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
ARCHITECTURE:
  Name: <name>
  Type: STANDARD | EXPRESS
  Definition: <StartAt + state count + terminal states>
  Service integrations:
    - <Resource ARN pattern 1> — <integration semantics>
    - <Resource ARN pattern 2> — <integration semantics>
  Map states:
    - Inline: <count> (max concurrency <N>)
    - Distributed: <count> (max concurrency <N>, source <S3|DynamoDB|payload>)
  Error handling:
    - <N> Tasks with Retry + Catch
    - <N> Tasks without Retry (non-fallible or Pass states)
  IAM role:
    - Trust: states.amazonaws.com (verified)
    - Identity policy: <N> statements, scoped to <list of ARN patterns>
  Logging (Express): level=ALL, includeExecutionData=true → CloudWatch Logs
  Tracing (Standard): enabled=true → X-Ray
CHECKLIST:
  [x] Workflow type chosen deliberately (Standard vs Express)
  [x] ASL definition validated — every path reaches a terminal
  [x] Every fallible Task has Retry AND Catch
  [x] Every Task has explicit TimeoutSeconds
  [x] Resource ARN suffixes match desired semantics (bare / .sync / .waitForTaskToken)
  [x] Map MaxConcurrency is set (not default 0/unbounded)
  [x] IAM role scoped to named actions on specific ARNs
  [x] Trust policy includes states.amazonaws.com
  [x] Express: LoggingConfiguration level=ALL + includeExecutionData=true
  [x] Standard: TracingConfiguration enabled=true + role has xray:PutTraceSegments
FINDINGS:
  - [INFO] Estimated monthly cost: <breakdown>
  - [WARN] <any non-blocking concerns>
DEPLOY_COMMANDS:
  <ordered list of aws stepfunctions create-* and aws iam * commands>
```

### Worked example — Express sync Lambda + DynamoDB workflow

```text
STATE_MACHINE_SPEC: order-checkout-express
VERDICT: READY_TO_DEPLOY
ARCHITECTURE:
  Name: order-checkout-express
  Type: EXPRESS
  Definition: StartAt=ValidateCart, 5 states (ValidateCart, ChargePayment,
    ReserveInventory, UpdateOrderRecord, Succeed), 1 Catch handler
    (PaymentErrorHandler). All paths reach a terminal.
  Service integrations:
    - arn:aws:states:::lambda:invoke (ValidateCart, ChargePayment,
      ReserveInventory) — fire-and-forget Lambda
    - arn:aws:states:::aws-sdk:dynamodb:updateItem (UpdateOrderRecord) —
      direct DynamoDB UpdateItem, no Lambda
  Map states: none
  Error handling:
    - ChargePayment: Retry on Lambda.ServiceException (2s, 3 attempts,
      2.0 backoff) + Catch States.ALL → PaymentErrorHandler
    - ReserveInventory: Retry on Lambda.ServiceException (2s, 3 attempts,
      2.0 backoff)
    - UpdateOrderRecord: Retry on DynamoDB.ProvisionedThroughputExceededException
      (5s, 5 attempts, 2.0 backoff)
  IAM role:
    - Trust: states.amazonaws.com (verified)
    - Identity policy: lambda:InvokeFunction on 3 specific function ARNs;
      dynamodb:UpdateItem on OrdersTable ARN; logs:* on log group ARN
  Logging: level=ALL, includeExecutionData=true → CloudWatch Logs
    (/aws/states/order-checkout-express)
  Tracing: N/A (Express — TracingConfiguration is no-op; ServiceLens
    provides partial visibility)
CHECKLIST:
  [x] Workflow type: EXPRESS — high-volume API Gateway backend, <5min total
  [x] ASL definition validated — all paths reach Succeed or Fail
  [x] Every fallible Task has Retry AND Catch (ChargePayment, ReserveInventory,
      UpdateOrderRecord)
  [x] Every Task has explicit TimeoutSeconds (30, 60, 30 respectively)
  [x] Resource ARNs: bare lambda:invoke (already sync), aws-sdk dynamodb
  [x] IAM role scoped to 3 Lambda ARNs + 1 DynamoDB table
  [x] Trust policy: states.amazonaws.com verified
  [x] Express Logging: level=ALL + includeExecutionData=true
FINDINGS:
  - [INFO] Estimated cost at 10M invocations/day @ 100ms avg: $10/day
    invocation + ~$5/day GB-sec = ~$15/day (~$450/month)
  - [INFO] Idempotency: ChargePayment Lambda must be idempotent (Express
    at-least-once semantics) — verify the function uses an idempotency key
  - [WARN] Express sync via API Gateway: total workflow must complete in
    < 29s (API Gateway 30s timeout) — current longest path is ~10s
DEPLOY_COMMANDS:
  1. aws iam create-role --role-name order-checkout-sfn-role
       --assume-role-policy-document file://trust-policy.json
  2. aws iam put-role-policy --role-name order-checkout-sfn-role
       --policy-name Scoped --policy-document file://identity-policy.json
  3. aws stepfunctions validate-state-machine-definition
       --definition file://definition.json --type EXPRESS
  4. aws logs create-log-group --log-group-name /aws/states/order-checkout-express
  5. aws stepfunctions create-state-machine
       --name order-checkout-express --definition file://definition.json
       --type EXPRESS --role-arn arn:aws:iam::111111111111:role/order-checkout-sfn-role
       --logging-configuration level=ALL,includeExecutionData=true
       --log-configuration-destinations cloudWatchLogsLogGroupArn=arn:aws:logs:us-east-1:111111111111:log-group:/aws/states/order-checkout-express:*
```

## Verification commands (run after deployment)

```bash
# Verify the state machine was created with correct type
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-checkout-express \
  --query '[name,type,roleArn,loggingConfiguration,tracingConfiguration]' \
  --output json

# Validate the definition (catches structural errors only, NOT missing
# Retry/Catch or missing TimeoutSeconds — those are caught by this skill)
aws stepfunctions validate-state-machine-definition \
  --definition file://definition.json --type EXPRESS

# Start a test execution (Express Sync)
aws stepfunctions start-sync-execution \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-checkout-express \
  --input file://test-input.json

# Start a test execution (Standard or Express Async)
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline \
  --input file://test-input.json

# Check execution status (Standard — 90 day history)
aws stepfunctions describe-execution --execution-arn <arn>

# For Express Async, find executions in CloudWatch Logs
aws logs filter-log-events \
  --log-group-name /aws/states/order-checkout-express \
  --filter-pattern '"status":"FAILED"'

# List activity workers (if using Activities)
aws stepfunctions get-activity-task --activity-arn <arn>

# Verify the execution role's identity policy scope
aws iam list-attached-role-policies --role-name <role-name>
aws iam list-role-policies --role-name <role-name>
aws iam get-role-policy --role-name <role-name> --policy-name <inline>

# Verify the trust policy includes states.amazonaws.com
aws iam get-role --role-name <role-name> \
  --query 'Role.AssumeRolePolicyDocument.Statement[?Principal.Service==`states.amazonaws.com`]'

# Verify X-Ray tracing is producing traces (Standard only)
aws xray get-trace-summaries --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) --filter-expression 'service("states")'

# Redrive a failed Standard execution (November 2024+) instead of re-running
aws stepfunctions redrive-execution --execution-arn <arn>
```

## Anti-Patterns — NEVER

- NEVER choose Express for a workflow with any Task that can run > 5 min
  (Glue job, Athena query, ECS long task, human approval). Express caps
  total execution at 5 minutes — the Task will be killed mid-run.

- NEVER use `.waitForTaskToken` on Express for human approval. The 5-min
  cap fails the Task before any human responds. Use Standard for
  callback-driven approval flows.

- NEVER deploy a fallible Task (Lambda, DynamoDB, SQS, ECS, Glue) without
  BOTH `Retry` AND `Catch`. ASL does NOT auto-retry — the first transient
  error (`Lambda.ServiceException`,
  `DynamoDB.ProvisionedThroughputExceededException`) fails the entire
  execution.

- NEVER deploy a Task without an explicit `TimeoutSeconds`. The default
  is 60 seconds. Lambda functions configured for longer runtimes are
  silently killed at 60s — the Lambda continues executing (and billing)
  while Step Functions advances to `States.Timeout`.

- NEVER use `Action: "*"` on the execution role. This is
  admin-equivalent — one compromised state machine = full account
  compromise. Scope to named actions on specific ARNs derived from the
  definition.

- NEVER use `AdministratorAccess` or `AmazonStepFunctionsFullAccess` as
  the execution role's managed policy. These grant `states:*` on `*`,
  enabling the workflow to chain into any other state machine in the
  account (the Step Functions analogue of `sts:AssumeRole`).

- NEVER grant `states:StartExecution` on `Resource: "*"` unless you
  intend the workflow to chain into any sibling. This is the
  chaining/escalation vector — scope to specific state machine ARNs.

- NEVER forget the trust policy on the execution role.
  `CreateStateMachine` accepts any role ARN — the trust policy is NOT
  validated at creation. A role missing `states.amazonaws.com` fails
  silently at runtime on the first integration.

- NEVER use `MaxConcurrency: 0` (the default) on a Map iterating >100
  items. Zero means unbounded — Step Functions invokes iterations as
  fast as possible, overwhelming downstream services (Lambda concurrency,
  DynamoDB throttling).

- NEVER use an Inline Map for >1000 items or >256KB total payload. Use
  Distributed Map. Inline Map caps at 40 concurrent iterations and 256KB.

- NEVER assume `TracingConfiguration.enabled: true` produces X-Ray traces
  on an Express workflow. The field is silently accepted but produces no
  traces. Use Standard for X-Ray; use CloudWatch ServiceLens for Express.

- NEVER assume `States.ALL` catches `States.Timeout`. On state machines
  created before November 2022, `States.ALL` does NOT match
  `States.Timeout`. Always list `States.Timeout` explicitly in `Catch`
  for long-running workflows.

- NEVER pass a parsed JSON object as the `definition` to
  `CreateStateMachine`. The API expects a STRINGIFIED JSON
  (`"{\"StartAt\": ...}"`). Use `jsonencode()` in Terraform or proper
  string escaping in CloudFormation.

- NEVER use `.sync` on a Lambda integration. `arn:aws:states:::lambda:invoke`
  is already synchronous — the `.sync` suffix is only meaningful for
  async-launch services (ECS, Glue, Athena, SageMaker, Step Functions
  nested).

- NEVER build non-idempotent Tasks in an Express workflow. Express
  at-least-once semantics means Tasks can be invoked MORE THAN ONCE on
  internal failure. DynamoDB `PutItem` without a composite idempotency
  key, SQS SendMessage without dedup, Stripe charge without
  idempotency key — all produce duplicates on retry.

- NEVER recommend deleting a state machine as a remediation step without
  first verifying no in-flight executions exist. Standard executions can
  run for up to 1 year; deleting the state machine orphans them.

- NEVER forget that the execution role may be shared across multiple
  state machines. Tightening the role for one workflow may break another.
  Before `put-role-policy`, list dependents via
  `aws resourcegroupstaggingapi get-resources --resource-type-filters states:stateMachine`.

## Pre-flight safety checks (run before any deployment CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-state-machine`, `update-state-machine`,
  `delete-state-machine`), the deployer MUST emit:
  `CONFIRM: About to <action> on state machine <name> in account <account>
  region <region>. Estimated monthly cost: <$X>. This is a non-reversible
  deployment. Proceed? (yes/no)`

- **Validate the definition BEFORE `create-state-machine`:**
  `aws stepfunctions validate-state-machine-definition --definition file://def.json --type STANDARD`
  This catches structural errors before they reach production. It does NOT
  catch missing-Catch or missing-TimeoutSeconds — the deployer skill does.

- **Verify the execution role trust policy:**
  `aws iam get-role --role-name <role> --query 'Role.AssumeRolePolicyDocument'`
  Confirm `Principal.Service: states.amazonaws.com` and
  `Action: sts:AssumeRole`.

- **Verify the identity policy scope:**
  `aws iam list-attached-role-policies` + `list-role-policies` +
  `get-role-policy`. Confirm no `Action: "*"` and no
  `Resource: "*"` (except for the few list/describe actions that require
  account-level scope).

- **Definition changes are unversioned.** `UpdateStateMachine` replaces
  the entire definition atomically — there is no rollback. Capture the
  current definition first:
  `aws stepfunctions describe-state-machine --state-machine-arn <arn> --output json > /tmp/<name>-backup-$(date +%s).json`

- **Cost estimate is MANDATORY for Express.** The deployer MUST emit a
  monthly cost estimate before deployment:
  - Express: $1.00 per 1M invocations + $0.00001667 per GB-sec duration
  - Standard: $0.025 per 1,000 state transitions
  - Distributed Map child executions bill separately per above

- **Tag everything at creation.** Use `--tags` on
  `create-state-machine`. Tags are the primary cost-allocation mechanism.
  Required tags: `Name`, `Environment`, `Team`, `CostCenter`.

- **Prefer additive changes** (add a Catch block, add a Retry block) over
  destructive changes (rewriting the definition) — additive changes are
  reversible and lower-risk.

## Recent AWS features (2024-2026)

- **RedriveExecution (November 2024):** A failed Standard execution can
  be redriven from the point of failure after fixing the definition
  — without re-running already-succeeded states. Express does NOT support
  redrive. Build Catch blocks that route to states safe to re-run on
  redrive. `aws stepfunctions redrive-execution --execution-arn <arn>`.

- **Distributed Map enhancements (2024-2025):** Distributed Map now
  supports cross-account S3 sources, DynamoDB Scan/Query with filters,
  and `MaxItemsPerBatchPath` for dynamic batch sizing. Higher
  `MaxConcurrency` (10,000+) is now supported.

- **Step Functions Playground (2024-2025):** In-console ASL experimentation
  environment with live validation. Useful for prototyping, but production
  definitions should be deployed via IaC.

- **AWS SDK service integrations (2024-2025 expansion):** Direct API
  calls to ~140+ AWS services without Lambda glue code. Resource ARN:
  `arn:aws:states:::aws-sdk:<service>:<action>`. Modern preferred
  pattern for single-API Tasks (e.g.,
  `arn:aws:states:::aws-sdk:secretsmanager:GetSecretValue`).

- **Bedrock model invocation (2024-2025):** First-class integration via
  `arn:aws:states:::bedrock:invokeModel` (sync) and
  `arn:aws:states:::bedrock:invokeModel.sync` (Standard only, async).
  The role needs `bedrock:InvokeModel` on the model ARN. Enables GenAI
  orchestration (RAG pipelines, multi-step LLM flows) without Lambda.

- **Resource-based policies for state machines (2024-2025):** Cross-account
  state machine execution via resource-based policies. The deploying
  account can grant `states:StartExecution` to a cross-account principal.
  Verify such policies include `aws:SourceAccount` conditions.

- **Payload validation with JSON Schema (2024):** Step Functions accepts
  a JSON Schema for state-input validation. Add schemas on states
  receiving external input to prevent malformed data from propagating.

- **Variable policies and JSONata (Parsed 2024 features):** New ASL
  extensions for richer variable manipulation. Available on newly-created
  state machines; opt-in via the `StateMachineVersionName` field. Verify
  the runtime supports these features before depending on them.

## References

- `references/asl-states-reference.md` — complete ASL state catalog
  (Task, Choice, Parallel, Map, Wait, Pass, Fail, Succeed) with field
  requirements, valid transitions, and worked examples per state type.
- `references/service-integration-patterns.md` — exhaustive Resource ARN
  catalog (Lambda, DynamoDB, SQS, SNS, ECS, SageMaker, Glue, Athena,
  Bedrock, AWS SDK) with sync/callback variants, required IAM actions,
  and integration-specific gotchas.

## Domain

AWS CloudOps / Step Functions Orchestration Provisioning.

## AWS documentation

- **AWS Step Functions Developer Guide** — https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html
- **Amazon States Language spec** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-amazon-states-language.html
- **Service integrations** — https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-services.html
- **Distributed Map** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-asl-use-map-state-distributed.html
- **Step Functions API Reference** — https://docs.aws.amazon.com/step-functions/latest/apireference/
- **Step Functions CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/stepfunctions/
- **Standard vs Express** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-standard-vs-express.html
