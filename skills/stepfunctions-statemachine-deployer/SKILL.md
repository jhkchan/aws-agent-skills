---
name: stepfunctions-statemachine-deployer
description: Provisions production-grade AWS Step Functions state machines with correct type selection (Standard exactly-once up to 1 year vs Express at-least-once up to 5 min), Amazon States Language definitions (Task, Choice, Parallel, Map, Wait, Pass, Fail, Succeed), service integrations via Resource ARN patterns (Lambda, DynamoDB, SQS, SNS, ECS, SageMaker, Glue, Athena, Bedrock), sync (.sync) vs callback (.waitForTaskToken) invocation patterns, error handling (Retry with exponential backoff, Catch routing), Inline Map (40 concurrent) vs Distributed Map (10000+ concurrent with S3/DynamoDB ItemReader, ItemBatcher, toleratedFailurePercentage), IAM least-privilege execution role, input/output processing (InputPath, ResultPath, OutputPath, Parameters), Express sync (RequestResponse) vs async (Firehose logging) workflows, and AWS SDK service integrations for direct API calls without Lambda. Emits a READY_TO_DEPLOY checklist. Use when provisioning state machines, designing ASL workflows, configuring service.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline architecture planning. Live deployment uses aws stepfunctions create-state-machine, update-state-machine, describe-state-machine, validate-state-machine-definition, start-execution, and aws iam create-role / attach-role-policy (AWS CLI v2, SSO or key-based credentials).
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
  when_to_use: Provisioning a new Step Functions state machine, choosing between Standard and Express workflow types, designing an ASL definition with service integrations (Lambda, DynamoDB, SQS, ECS, Glue, Bedrock), configuring Retry/Catch error handling, building a Distributed Map for large-scale fan-out, scoping the IAM execution role to specific resource ARNs, choosing between sync (.sync) and callback (.waitForTaskToken) integration patterns, or hardening an Express workflow for production.
  activation_triggers: create a state machine, deploy Step Functions workflow, Standard vs Express workflow, write ASL definition, service integration Resource ARN, Retry and Catch blocks, Distributed Map state, waitForTaskToken callback, Step Functions execution role, Step Functions + Lambda orchestration, Step Functions + Bedrock, Express workflow synchronous
  invocation_schema: 'Input shape (one of): (a) a deployment specification including workflow name, type (STANDARD | EXPRESS), ASL definition (or requirements to derive one), service integrations, error-handling requirements, and execution role scope; (b) a partial spec for interactive refinement (e.g., "Express workflow invoking Lambda + DynamoDB, sync, 60s budget"); (c) an existing state machine ARN for architecture review against the well-architected checklist. Output shape: { STATE_MACHINE_SPEC, VERDICT, ARCHITECTURE, CHECKLIST[], FINDINGS[], DEPLOY_COMMANDS } where VERDICT ∈ { READY_TO_DEPLOY, PREREQUISITES_MISSING, ERROR }.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Step Functions, state machine, ASL, Amazon States Language, Standard workflow, Express workflow, Task state, Choice state, Parallel state, Map state, Distributed Map, Inline Map, Retry, Catch, error handling, service integration, Resource ARN, waitForTaskToken, sync integration, callback pattern, Task Token, IAM execution role, states:StartExecution, InputPath, ResultPath, OutputPath, Parameters, ItemReader, ItemBatcher, Bedrock invocation, AWS SDK integration, Step Functions Playground
  tags: stepfunctions, app-integration, deploy, state-machine, asl, express, standard, distributed-map, service-integration, iam, error-handling
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

> Full detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand.
> Summary: the complete Step 0 catalog of behaviors that change the deployment plan (billing, idempotency, history expiry, tracing no-op, timeouts, heartbeats, Retry/Catch, Map concurrency, .sync/.waitForTaskToken billing, definition-as-string, States.ALL gap, trust policy, SDK integrations, Bedrock, Redrive).

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

> Full detail moved verbatim to [references/service-integration-patterns.md](references/service-integration-patterns.md) - load on demand.
> Summary: the full Resource ARN pattern catalog and suffix decision tree.

### Step 4: Sync vs callback pattern selection

> Full detail moved verbatim to [references/service-integration-patterns.md](references/service-integration-patterns.md) - load on demand.
> Summary: the .sync vs .waitForTaskToken selection detail with anti-pattern.

### Step 5: Map state design (Inline vs Distributed)

> Full detail moved verbatim to [references/asl-states-reference.md](references/asl-states-reference.md) - load on demand.
> Summary: the Inline-vs-Distributed comparison and both full ASL templates.

### Step 6: Error handling — Retry and Catch

> Full detail moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand.
> Summary: the complete Retry/Catch field reference and standard JSON shape.

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

> Full detail moved verbatim to [references/iam-and-logging-templates.md](references/iam-and-logging-templates.md) - load on demand.
> Summary: the trust policy, identity-policy derivation, and per-integration permission templates.

### Step 9: Logging and tracing

> Full detail moved verbatim to [references/iam-and-logging-templates.md](references/iam-and-logging-templates.md) - load on demand.
> Summary: the Express logging and Standard tracing configuration templates.

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

> Full detail moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand.
> Summary: the full post-deployment verification CLI listing.

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

> Full detail moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand.
> Summary: the pre-deployment safety checklist and CLI listings.

## Recent AWS features (2024-2026)

> Full detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand.
> Summary: the 2024-2026 feature list (Redrive, Distributed Map enhancements, SDK integrations, Bedrock, resource policies, payload validation, JSONata).

## References

- `references/asl-states-reference.md` — complete ASL state catalog
  (Task, Choice, Parallel, Map, Wait, Pass, Fail, Succeed) with field
  requirements, valid transitions, and worked examples per state type.
- `references/service-integration-patterns.md` — exhaustive Resource ARN
  catalog (Lambda, DynamoDB, SQS, SNS, ECS, SageMaker, Glue, Athena,
  Bedrock, AWS SDK) with sync/callback variants, required IAM actions,
  and integration-specific gotchas.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) - Step 0 expert knowledge and recent AWS features
- [references/error-handling.md](references/error-handling.md) - Retry/Catch design deep dive
- [references/diagnostic-commands.md](references/diagnostic-commands.md) - post-deploy verification and pre-deploy safety CLI listings
- [references/iam-and-logging-templates.md](references/iam-and-logging-templates.md) - IAM trust/identity policy and logging/tracing templates
- [references/asl-states-reference.md](references/asl-states-reference.md) - (existing) ASL state catalog; now also holds Map design and I/O processing detail
- [references/service-integration-patterns.md](references/service-integration-patterns.md) - (existing) Resource ARN catalog; now also holds Steps 3-4 selection detail

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
