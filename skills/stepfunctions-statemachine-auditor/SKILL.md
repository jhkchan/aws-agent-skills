---
name: stepfunctions-statemachine-auditor
description: >-
  Audits AWS Step Functions state machines for execution logging coverage
  (level ALL + includeExecutionData), X-Ray tracing enablement (including
  the Express-workflow no-op trap), execution-role blast radius (wildcard
  actions, states:StartExecution chaining, iam:PassRole), and ASL
  definition validation (missing Catch/Retry on fallible Tasks, missing
  TimeoutSeconds, unreachable states, cyclic references without exit). Emits
  a deterministic verdict (NO_LOGGING | NO_TRACING | OVERPERMISSIVE_ROLE |
  CONFIG_GAP | OK) per state machine with enumerated findings and specific
  remediation. Use when reviewing Step Functions state machines, checking
  logging coverage, validating X-Ray tracing, auditing execution-role
  scope, validating ASL definitions, or hardening state machine
  observability and security posture before production deployment.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline state-machine classification.
  Live-account audits use aws stepfunctions describe-state-machine,
  aws stepfunctions describe-execution, aws iam get-role-policy, and
  aws stepfunctions validate-state-machine-definition (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - Step Functions
  - state machine
  - ASL
  - Amazon States Language
  - execution logging
  - CloudWatch Logs
  - X-Ray tracing
  - distributed tracing
  - Express workflow
  - Standard workflow
  - execution role
  - IAM blast radius
  - states:StartExecution
  - iam:PassRole
  - definition validation
  - circular states
  - unreachable states
  - Catch block
  - Retry block
  - TimeoutSeconds
  - HeartbeatSeconds
  - error handling
  - Task state
  - Choice state
  - Map state
  - Parallel state
  - state machine audit
tags: [stepfunctions, app-integration, security, observability, state-machine, asl, xray, logging, iam, audit]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  verdict_shape: "NO_LOGGING | NO_TRACING | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing a Step Functions state machine before production deployment,
    checking execution logging coverage, validating X-Ray tracing enablement,
    auditing the execution role's blast radius, validating ASL definition
    correctness (unreachable/cyclic states, missing error handling), or
    hardening state machine observability and security posture.
  activation_triggers:
    - "audit this state machine"
    - "check Step Functions logging"
    - "is X-Ray tracing enabled"
    - "state machine execution role too broad"
    - "validate ASL definition"
    - "missing Catch block"
    - "Express workflow tracing"
    - "state machine error handling"
    - "unreachable states in ASL"
    - "Step Functions blast radius"
  invocation_schema: >-
    Input: either (a) a Step Functions state machine configuration
    (definition + type + loggingConfiguration + tracingConfiguration +
    roleArn + role policy), OR (b) a state-machine ARN for live-account
    audit. Output: deterministic STATE_MACHINE/VERDICT/REASON/FINDINGS/
    REMEDIATION block per state machine, where VERDICT is one of NO_LOGGING,
    NO_TRACING, OVERPERMISSIVE_ROLE, CONFIG_GAP, OK, or ERROR.
---

# Step Functions State Machine Auditor

## Mindset

**One-line takeaway:** a state machine is audited across four orthogonal
dimensions — **execution logging**, **X-Ray tracing**, **execution-role
blast radius**, and **ASL definition correctness** — and the verdict is
always the **worst** finding, in the precedence
`OVERPERMISSIVE_ROLE > NO_LOGGING > NO_TRACING > CONFIG_GAP > OK`.

Step Functions is the orchestration layer for multi-service workflows. Its
blast radius is unusual because a single state machine can fan out to
Lambda, DynamoDB, SQS, SNS, ECS, Glue, S3, and other state machines — all
under one execution role. Three structural facts drive the audit:

- **The execution role is a service-chaining multiplier.** One role with
  `lambda:*` + `dynamodb:*` + `sqs:*` on `*` grants the state machine
  fan-out access to every resource of every integrated service. This is the
  IAM blast-radius pattern unique to Step Functions.
- **Execution logging at `level: OFF` is forensic blindness.** The Step
  Functions console shows execution history for 90 days (Standard) or
  minutes (Express), but only `LoggingConfiguration.level: ALL` plus
  `includeExecutionData: true` delivers a durable, queryable record to
  CloudWatch Logs. Without it, post-incident forensics rely on CloudTrail
  alone, which does not capture per-state input/output.
- **`TracingConfiguration.enabled: true` on an EXPRESS workflow is a
  no-op.** X-Ray tracing via the `TracingConfiguration` field is only
  honored on STANDARD workflows. An Express workflow with tracing
  "enabled" produces zero X-Ray traces — operators who check the box and
  move on have no distributed tracing at all.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Execution role: `Action: "*"` on `Resource: "*"` (admin-equivalent) | **OVERPERMISSIVE_ROLE** | Step 3 |
| Execution role: service wildcard (`lambda:*`, `dynamodb:*`, `s3:*`) on `Resource: "*"` | **OVERPERMISSIVE_ROLE** | Step 3 |
| Execution role: `states:StartExecution` on `*` (chaining/escalation) | **OVERPERMISSIVE_ROLE** | Step 3 |
| Execution role: `iam:PassRole` on `*` | **OVERPERMISSIVE_ROLE** | Step 3 |
| `LoggingConfiguration.level` is `OFF`, `ERROR`, or absent | **NO_LOGGING** | Step 1 |
| `LoggingConfiguration.includeExecutionData` is `false` or absent | **NO_LOGGING** | Step 1 |
| `TracingConfiguration.enabled` is `false` or absent on a STANDARD workflow | **NO_TRACING** | Step 2 |
| Workflow `type: EXPRESS` (X-Ray no-op regardless of `TracingConfiguration`) | **NO_TRACING** | Step 2 |
| `Task` state with a fallible `Resource` and NO `Catch` and NO `Retry` | **CONFIG_GAP** | Step 4 |
| `Task` state with no `TimeoutSeconds` (60-second default, silent kill) | **CONFIG_GAP** | Step 4 |
| `Choice` state with no `Default` branch | **CONFIG_GAP** | Step 4 |
| Unreachable state (no inbound `Next`/`Default`/`Catch.Next`) | **CONFIG_GAP** | Step 4 |
| All dimensions pass | **OK** | Step 5 |

When multiple findings apply, the verdict is the **worst** by precedence
(`OVERPERMISSIVE_ROLE > NO_LOGGING > NO_TRACING > CONFIG_GAP > OK`). All
individual findings still appear in the FINDINGS list regardless of the
aggregate verdict.

## Critical rules — read first (do NOT violate)

These are the high-frequency, high-impact mistakes. Each is expanded in
the NEVER list and Step 0 below — this block exists so an agent executing
under time pressure sees them before any classification logic:

1. **`includeExecutionData: false` is NO_LOGGING even at `level: ALL`.**
   State transitions are logged but NOT input/output payloads. For
   forensics, this is near-blind. Always check BOTH fields.
2. **`TracingConfiguration.enabled: true` on an EXPRESS workflow is a
   no-op.** The field is accepted silently; no X-Ray console traces are
   produced. Always emit NO_TRACING for Express regardless of the field.
3. **`Action: "*"` on `Resource: "*"` on the execution role is
   OVERPERMISSIVE_ROLE.** No exceptions — this is admin-equivalent; one
   compromised state machine = full account compromise.
4. **A fallible `Task` (Lambda, DynamoDB, SQS, etc.) with NO `Catch` and
   NO `Retry` is CONFIG_GAP.** Transient errors fail the entire execution
   on the first occurrence. Both blocks are expected on production Tasks.
5. **A `Task` without `TimeoutSeconds` silently uses 60 seconds.** Lambda
   functions configured for longer runtimes are killed at 60s while the
   Lambda continues executing and billing.
6. **NEVER recommend `AdministratorAccess` or `AmazonStepFunctionsFullAccess`
   as a remediation.** These grant `states:*` on `*`, reintroducing the
   over-permission being fixed. Always scope to named actions on specific
   ARNs derived from the definition's `Resource` fields.
7. **`states:StartExecution` on `Resource: "*"` is a chaining/escalation
   vector** — the Step Functions analogue of `sts:AssumeRole`. Scope to
   the specific state-machine ARNs the workflow is permitted to chain into.

## Pre-flight: state machine type gate (run before classification)

Step Functions operates two workflow types with materially different
observability models. Misclassifying the type produces false confidence in
tracing and logging coverage.

| `Type` | Execution history retention | X-Ray tracing via `TracingConfiguration` | Logging implication |
|---|---|---|---|
| `STANDARD` | 90 days via API/console | **Honored.** X-Ray console shows traces. | `LoggingConfiguration` delivers to CloudWatch Logs for structured queries/alerts. Execution history is a fallback. |
| `EXPRESS` | 5 minutes (Synchronous) / 1 hour (Asynchronous) via API | **No-op.** The field is accepted but produces no X-Ray console traces. | `LoggingConfiguration` is the ONLY durable record. `NO_LOGGING` on Express is catastrophic for forensics. |

**Type-specific audit behavior:**

- **EXPRESS workflow:** ALWAYS emit `NO_TRACING` as at least a secondary
  finding, regardless of `TracingConfiguration.enabled`. The operator may
  have set the field expecting X-Ray coverage — that expectation is not
  met. If logging is also missing, the verdict is `NO_LOGGING` (higher
  precedence), with `NO_TRACING` noted in FINDINGS.
- **STANDARD workflow:** Evaluate `TracingConfiguration.enabled` normally.
  `false` or absent → `NO_TRACING`.
- **Type absent from input:** Emit an ERROR note and assume STANDARD (the
  default at creation) for downstream evaluation, but flag the assumption.

**If the state machine configuration is malformed** (invalid JSON, missing
`Definition`, missing `RoleArn`), output:

```text
STATE_MACHINE: <arn-or-name>
VERDICT: ERROR
REASON: State machine configuration is not valid — missing or malformed required field.
REMEDIATION: Retrieve the canonical config with `aws stepfunctions describe-state-machine --state-machine-arn <arn> --output json` and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious Step Functions behaviors

These behaviors change the verdict if ignored. Each is a genuine
operational gotcha that a senior Step Functions engineer knows but a
generalist misses:

- **`includeExecutionData: false` is forensic blindness even at
  `level: ALL`.** The `LoggingConfiguration` has two independent fields:
  `level` (`OFF` | `ERROR` | `ALL`) and `includeExecutionData` (boolean).
  With `level: ALL` but `includeExecutionData: false`, CloudWatch Logs
  receives state-transition events (which state ran, when) but NOT the
  input/output JSON of each state. For post-incident forensics, this is
  nearly as bad as `OFF` — you know "Step3 ran" but not "with what payload"
  or "what it returned". Treat `includeExecutionData: false` or absent as
  `NO_LOGGING`.

- **Express workflows silently ignore `TracingConfiguration`.** The
  `CreateStateMachine` and `UpdateStateMachine` APIs accept the
  `tracingConfiguration.enabled` field for both Standard and Express
  workflows without error. But for Express workflows, no X-Ray traces are
  emitted to the X-Ray console. The operator sees a green checkbox in the
  console and assumes tracing is working. Always flag Express workflows as
  `NO_TRACING` regardless of the field value, and note in REMEDIATION that
  Express workflows must use CloudWatch Logs ServiceLens for distributed
  visibility (a weaker substitute).

- **Execution history retention is type-dependent and non-negotiable.**
  Standard workflows: 90 days via `describe-execution` / console. Express
  workflows: 5 minutes (Synchronous) or 1 hour (Asynchronous). After the
  window, the execution history is GONE — only CloudWatch Logs (if
  configured) has the data. This is why `NO_LOGGING` on Express is more
  severe than on Standard.

- **`states:StartExecution` is a chaining/escalation vector.** A state
  machine whose execution role grants `states:StartExecution` on `*` (or
  on a more-privileged sibling's ARN) can chain into that sibling,
  inheriting its broader permissions. This is the Step Functions analogue
  of `sts:AssumeRole`. Treat `states:StartExecution` on `*` as
  `OVERPERMISSIVE_ROLE`.

- **Default `TimeoutSeconds` is 60.** A `Task` state without an explicit
  `TimeoutSeconds` uses a 60-second hard cap. Lambda functions configured
  with longer timeouts (up to 15 minutes) are silently killed by Step
  Functions at 60 seconds — the Lambda invocation continues (and bills)
  but the state machine advances to a `States.Timeout` error. Always check
  for explicit `TimeoutSeconds` on every `Task`.

- **`HeartbeatSeconds` is required for Activity-based Tasks.** A `Task`
  with `Resource: arn:aws:states:<region>:<account>:activity:<name>`
  relies on an external activity worker calling `GetActivityTask` and
  `SendTaskHeartbeat`. Without `HeartbeatSeconds`, a dead/crashed worker
  is not detected until `TimeoutSeconds` (which may be hours). Flag any
  Activity-based Task without `HeartbeatSeconds` as `CONFIG_GAP`.

- **`Retry` without explicit `IntervalSeconds`/`MaxAttempts`/`BackoffRate`
  uses defaults (1s, 3, 2.0).** These defaults are reasonable for
  transient errors. But a `Task` with NO `Retry` block at all fails the
  entire execution on the first error — including transient
  `Lambda.ServiceException` or `DynamoDB.ProvisionedThroughputExceededException`.

- **`Catch` vs `Retry` are not interchangeable.** `Retry` re-executes the
  SAME state. `Catch` routes to a DIFFERENT state (the error handler). A
  `Task` with only `Retry` (no `Catch`) still fails the execution if
  retries are exhausted. A `Task` with only `Catch` (no `Retry`) does not
  retry on transient errors. For production hardening, BOTH are expected
  on fallible Tasks. For the audit, a Task with NEITHER is `CONFIG_GAP`.

- **`Choice` state without `Default` is invalid ASL.** The API rejects it
  at creation, but Terraform/CloudFormation may accept the template and
  fail at apply-time. Flag any `Choice` state without a `Default` field as
  `CONFIG_GAP`.

- **`Map` state `MaxConcurrency: 0` means unbounded.** The default is 0,
  which means Step Functions invokes the iteration as fast as possible
  with no cap. For large item sets, this overwhelms downstream services
  (Lambda concurrency limits, DynamoDB throttling, API rate limits). Flag
  `MaxConcurrency: 0` on a Map iterating > 100 items as `CONFIG_GAP`.

- **`definition` is a STRING in the API, not a JSON object.**
  `CreateStateMachine` expects `"definition": "{\"StartAt\": ...}"` (a
  stringified ASL document). Passing a parsed JSON object fails with
  `InvalidDefinition`. This is a Terraform/CloudFormation footgun, not a
  runtime audit issue, but note it in REMEDIATION when the definition
  fails to parse.

- **The execution role's trust policy MUST include `states.amazonaws.com`.**
  `CreateStateMachine` does NOT validate the trust policy — it accepts any
  role ARN. At runtime, the state machine fails with `AccessDenied` on the
  first service integration if the role does not trust Step Functions.
  Always check the role's `AssumeRolePolicyDocument`.

- **X-Ray tracing requires `xray:PutTraceSegments` on the role.** Even
  with `TracingConfiguration.enabled: true` on a Standard workflow, if the
  execution role lacks `xray:PutTraceSegments` and
  `xray:PutTelemetryRecords`, no traces are emitted. Tracing silently
  fails — no error, no alarm. When the role is in scope, verify these
  permissions are present.

- **Logging delivery requires `logs:CreateLogDelivery` + `logs:PutLogEvents`
  on the role.** Without these, `LoggingConfiguration.level: ALL` is
  accepted at the API but produces no CloudWatch Logs. The console shows
  "logging enabled" but no log events arrive. When the role is in scope,
  verify these permissions.

- **`States.Timeout` is the error caught when `TimeoutSeconds` is hit.**
  Operators sometimes write `Catch` blocks for `States.TaskFailed` but
  forget `States.Timeout`. A `Catch` matching only specific errors misses
  the timeout path. Flag a `Catch` block that does not include a broad
  fallback (e.g., `States.ALL`) as a weaker but non-blocking finding.

- **`HeartbeatSeconds` MUST be strictly less than `TimeoutSeconds`.** The
  `CreateStateMachine` / `UpdateStateMachine` API rejects
  `HeartbeatSeconds >= TimeoutSeconds` with `ValidationException`, but
  Terraform/CloudFormation may accept the template and fail at apply-time.
  When auditing Activity-based Tasks, verify `HeartbeatSeconds <
  TimeoutSeconds` (e.g., heartbeat 30, timeout 300 — not heartbeat 300,
  timeout 300).

- **`RedriveExecution` (added November 2024) changes the remediation
  calculus for CONFIG_GAP on Standard workflows.** A failed Standard
  execution can be **redriven** from the point of failure after fixing
  the definition (e.g., adding a missing `Catch` block, scoping a role)
  — without re-running the already-succeeded states. This is a
  non-obvious alternative to `StartExecution` when the input payload is
  large, the upstream queue is emptied, or the side effects of
  re-running early states are non-idempotent. Express workflows do NOT
  support redrive. When recommending remediation for a CONFIG_GAP on
  Standard, mention redrive as the recovery path AFTER the definition
  fix is deployed: `aws stepfunctions redrive-execution
  --execution-arn <arn>`. The redrive replays from the failed state
  onward using the ORIGINAL input — not a fresh invocation.

- **`States.ALL` does NOT match `States.Timeout` in older runtime
  versions.** On Standard workflows created before November 2022, a
  `Catch` with `ErrorEquals: ["States.ALL"]` catches most errors but NOT
  `States.Timeout` (the matching set was expanded in a runtime update).
  For state machines created before that date, recommend explicitly
  listing `States.Timeout` alongside `States.ALL` in Catch blocks. This
  is a subtle, version-dependent gap that affects long-running
  production workflows.

### Step 1: Logging configuration (NO_LOGGING)

Evaluate `LoggingConfiguration` for both Standard and Express workflows:

| Condition | Finding | Why |
|---|---|---|
| `level: OFF` or `LoggingConfiguration` absent | **NO_LOGGING** | No CloudWatch Logs delivery. Execution history is the only signal, and it expires (90d Standard, minutes Express). |
| `level: ERROR` | **NO_LOGGING** | Only failed states are logged. Successful executions leave no trace — blind to slow degradation, data exfiltration via successful API calls, or unexpected state transitions. |
| `level: ALL` + `includeExecutionData: false` or absent | **NO_LOGGING** | State transitions are logged but NOT input/output payloads. Forensically near-useless — you cannot reconstruct what data flowed through the workflow. |
| `level: ALL` + `includeExecutionData: true` | **OK (this dimension)** | Full observability. Both transitions and payloads are in CloudWatch Logs. |

**Express-specific escalation:** for Express workflows, execution history
expires in minutes. `NO_LOGGING` on Express means there is NO durable
record of the execution — flag this as a critical-severity secondary note
in FINDINGS.

**`logGroupName` presence:** if `level: ALL` but no `logGroupName` (or no
`logDestinationArn`), Step Functions creates a default log group. Verify
the role has `logs:CreateLogGroup` or the delivery silently fails.

### Step 2: Tracing configuration (NO_TRACING)

Evaluate `TracingConfiguration` with the type gate from Pre-flight:

| Workflow type | `TracingConfiguration.enabled` | Finding |
|---|---|---|
| `STANDARD` | `true` | OK (this dimension) — verify role has `xray:PutTraceSegments`. |
| `STANDARD` | `false` or absent | **NO_TRACING** — no distributed tracing; cross-service latency and error analysis impossible. |
| `EXPRESS` | any value | **NO_TRACING** — `TracingConfiguration` is a no-op on Express. Operator's tracing expectation is not met. |

**Why this matters:** Step Functions orchestrates multiple services
(Lambda, DynamoDB, SQS, API Gateway, ECS). Without X-Ray, a latency spike
in the workflow cannot be attributed to a specific service integration.
The operator sees "execution took 45 seconds" but not "DynamoDB GetItem
took 40 of those seconds".

### Step 3: IAM execution role blast radius (OVERPERMISSIVE_ROLE)

The execution role is the identity under which EVERY service integration
in the state machine runs. Its scope determines the workflow's total
blast radius. Evaluate the role's identity-based policies (managed +
inline):

**CRITICAL-severity role findings (emit OVERPERMISSIVE_ROLE):**

- `Action: "*"` on `Resource: "*"` — admin-equivalent. The state machine
  can call any service on any resource. This is the single most dangerous
  pattern in Step Functions because one state machine compromise = full
  account compromise.
- Service wildcard (e.g., `lambda:*`, `dynamodb:*`, `s3:*`, `sqs:*`,
  `sns:*`, `states:*`) on `Resource: "*"` — broad fan-out access to every
  resource of that service. The state machine can invoke any Lambda, read
  any DynamoDB table, publish to any SNS topic.
- `states:StartExecution` on `Resource: "*"` — can start ANY state machine
  in the account, including more-privileged ones. This is the Step
  Functions chaining/escalation vector (analogous to `sts:AssumeRole`).
- `iam:PassRole` on `Resource: "*"` — can pass any role to any service
  that accepts a role ARN. Combined with a Lambda/Lambda-invoking Task,
  this enables privilege escalation.
- `states:CreateStateMachine` / `states:UpdateStateMachine` on `*` — can
  create or modify other state machines, widening the attack surface.

**Role trust policy check (secondary finding, does not drive the verdict
but appears in FINDINGS):**

- The role's `AssumeRolePolicyDocument` MUST include
  `Principal: { Service: "states.amazonaws.com" }` with
  `Action: "sts:AssumeRole"`. Without this trust, the state machine
  cannot assume the role — every service integration fails at runtime
  with `AccessDenied`. Flag as an operational risk.

**Scoped role (OK for this dimension):**

- Named actions (e.g., `lambda:InvokeFunction`,
  `dynamodb:GetItem`, `dynamodb:PutItem`) on specific ARNs (e.g.,
  `arn:aws:lambda:us-east-1:111111111111:function:order-processor`) → OK.
- The minimum-viable execution role grants only the actions the
  definition's service integrations require, scoped to the specific
  resource ARNs.

**Live-account enumeration (when auditing by ARN):**

```
aws iam list-attached-role-policies --role-name <role-name> --profile <p>
aws iam list-role-policies --role-name <role-name> --profile <p>
aws iam get-role-policy --role-name <role-name> --policy-name <name> --profile <p>
```

Page inline policies — `get-role-policy` returns one policy at a time.

### Step 4: ASL definition validation (CONFIG_GAP)

Validate the `Definition` (ASL document) for structural correctness,
error handling, and runtime-safety gaps. The API's
`ValidateStateMachineDefinition` catches syntax errors and some structural
issues, but it does NOT check for production-hardening gaps (missing
Catch, missing TimeoutSeconds). The auditor goes beyond API validation.

**Fallible Task without error handling (CONFIG_GAP):**

A `Task` state with a fallible `Resource` (any ARN that invokes an
external service — Lambda, DynamoDB, SQS, ECS, Glue, SNS, Step Functions
nested) MUST have either a `Catch` block, a `Retry` block, or both. A
Task with NEITHER fails the entire execution on the first error,
including transient errors that would resolve on retry.

Fallible `Resource` ARN patterns:
- `arn:aws:lambda:*` — Lambda invocation (transient `ServiceException`)
- `arn:aws:dynamodb:*` — DynamoDB CRUD (provisioned-throughput errors)
- `arn:aws:sqs:*` — SQS SendMessage (rate limits)
- `arn:aws:sns:*` — SNS Publish (rate limits)
- `arn:aws:states:*:execution:*` — nested Step Functions
- `arn:aws:ecs:*` — ECS RunTask (capacity errors)
- Any AWS service integration

Non-fallible states (no error handling needed):
- `Succeed`, `Fail`, `Pass`, `Wait`, `Choice`, `Map`, `Parallel`

**Missing `TimeoutSeconds` on Task (CONFIG_GAP):**

A `Task` without `TimeoutSeconds` defaults to 60 seconds. Long-running
integrations (Lambda with > 60s timeout, Activities, Glue jobs, ECS
tasks) are silently killed at 60s. Flag any `Task` without explicit
`TimeoutSeconds`.

**Missing `HeartbeatSeconds` on Activity-based Task (CONFIG_GAP):**

A `Task` with `Resource: arn:aws:states:*:activity:*` relies on an
external worker. Without `HeartbeatSeconds`, worker death is not detected
until `TimeoutSeconds` (which can be hours). Flag any Activity-based Task
without `HeartbeatSeconds`.

**Unreachable states (CONFIG_GAP):**

Walk the state graph from `StartAt`. Any state NOT reachable via
`Next`/`Default`/`Catch[].Next`/`Iterator.StartAt` chain is unreachable.
Unreachable states are dead code — they may contain stale logic or
privilege assumptions that diverge from the live path. Flag each
unreachable state by name.

**Cyclic references without exit (CONFIG_GAP):**

ASL permits cycles (a `Choice` that loops back, a `Task` that retries via
`Next` to itself). A cycle is valid IF there is an exit path (a `Choice`
branch that leaves the cycle, or a `Retry`/`Catch` that routes elsewhere).
A cycle with NO exit path (e.g., a `Task` whose `Next` points back to
itself with no `Retry`/`Catch`) is an infinite loop. Flag as CONFIG_GAP.

**Choice without Default (CONFIG_GAP):**

A `Choice` state without a `Default` field is invalid ASL — the API
rejects it. But if the input is a template (Terraform/CloudFormation), it
may pass initial parsing and fail at apply. Flag any `Choice` without
`Default`.

**Map state with `MaxConcurrency: 0` and large item set (CONFIG_GAP):**

`MaxConcurrency: 0` means unbounded parallelism. For a Map iterating > 100
items, this can overwhelm downstream services (Lambda concurrency,
DynamoDB throttling). Flag as CONFIG_GAP and recommend setting
`MaxConcurrency` to a value within the downstream service's capacity.

### Step 5: Aggregation — worst finding wins by precedence

The final verdict is the worst finding across all dimensions, in this
precedence order (highest to lowest):

```
OVERPERMISSIVE_ROLE > NO_LOGGING > NO_TRACING > CONFIG_GAP > OK
```

This precedence reflects: security exposure first (the role is the blast
radius), then forensic visibility (logging), then distributed observability
(tracing), then correctness (definition gaps). A state machine with both
an over-permissive role AND missing logging gets `OVERPERMISSIVE_ROLE` as
the verdict, with both findings enumerated.

If no findings across any dimension, the verdict is **OK**.

## Output format (per state machine)

```text
STATE_MACHINE: <arn-or-name>
TYPE: STANDARD | EXPRESS
VERDICT: NO_LOGGING | NO_TRACING | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [OVERPERMISSIVE_ROLE] <finding description (Step 3)>
  - [NO_LOGGING] <finding description (Step 1)>
  - [OK] <dimensions that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — over-permissive role on Standard workflow

```text
STATE_MACHINE: arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline
TYPE: STANDARD
VERDICT: OVERPERMISSIVE_ROLE
REASON: Execution role grants lambda:* and dynamodb:* on Resource "*" — the
state machine has fan-out access to every Lambda function and DynamoDB table
in the account (Step 3). Logging and tracing are correctly configured.
FINDINGS:
  - [OVERPERMISSIVE_ROLE] Role policy: lambda:* on Resource "*" (Step 3) —
    can invoke any Lambda function in the account
  - [OVERPERMISSIVE_ROLE] Role policy: dynamodb:* on Resource "*" (Step 3) —
    can read/write any DynamoDB table
  - [OK] LoggingConfiguration.level: ALL + includeExecutionData: true (Step 1)
  - [OK] TracingConfiguration.enabled: true on STANDARD workflow (Step 2)
  - [OK] All Task states have Catch + Retry + TimeoutSeconds (Step 4)
REMEDIATION:
  1. Replace lambda:* with lambda:InvokeFunction scoped to the specific
     function ARNs the definition invokes.
  2. Replace dynamodb:* with the specific actions (GetItem, PutItem,
     UpdateItem) scoped to the specific table ARNs.
  3. Verify the role retains states:StartExecution only on this state
     machine's own ARN (if self-chaining is intended) or remove it.
```

## Anti-Patterns — NEVER

- NEVER classify a state machine with `loggingConfiguration.level: OFF`
  as `OK` for the logging dimension. `OFF` means no CloudWatch Logs
  delivery. The 90-day execution history (Standard) is a fallback, not a
  replacement — it is not queryable, not alertable, and not retained for
  compliance windows.

- NEVER treat `level: ALL` as sufficient when `includeExecutionData` is
  false or absent. Without execution data, CloudWatch Logs has state
  transitions but no input/output payloads. For forensics, this is nearly
  as blind as `OFF`. Treat as `NO_LOGGING`.

- NEVER assume `TracingConfiguration.enabled: true` on an EXPRESS workflow
  produces X-Ray traces. The field is accepted silently but produces no
  X-Ray console traces. Always emit `NO_TRACING` for Express workflows.

- NEVER classify `Action: "*"` on `Resource: "*"` on the execution role as
  anything other than `OVERPERMISSIVE_ROLE`. This is admin-equivalent —
  the state machine can call any AWS service on any resource. One
  compromised state machine = full account compromise.

- NEVER overlook `states:StartExecution` on `Resource: "*"` as a benign
  permission. It enables the state machine to start ANY other state
  machine in the account, including more-privileged ones. This is the Step
  Functions chaining/escalation vector, analogous to `sts:AssumeRole`.

- NEVER classify a `Task` with a fallible `Resource` (Lambda, DynamoDB,
  SQS, etc.) and NO `Catch` and NO `Retry` as `OK`. Transient errors
  (`Lambda.ServiceException`,
  `DynamoDB.ProvisionedThroughputExceededException`) fail the entire
  execution on first occurrence. This is a production-hardening gap.

- NEVER assume a `Task` without `TimeoutSeconds` is safe. The 60-second
  default silently kills Lambda functions configured for longer runtimes.
  The Lambda continues executing (and billing) but Step Functions advances
  to a `States.Timeout` error.

- NEVER flag a legitimate retry loop (a `Task` with `Retry` block whose
  `Next` stays on the same state) as a "cyclic reference" defect. Cycles
  are valid ASL for iteration. Only flag cycles with NO exit path (no
  `Retry`/`Catch` that can break out, no `Choice` branch that leaves).

- NEVER recommend `AdministratorAccess` or `AmazonStepFunctionsFullAccess`
  as a remediation for a scoped role. These grant `states:*` on `*`,
  reintroducing the over-permission you are fixing.

- NEVER assume the execution role's trust policy is correct without
  checking. `CreateStateMachine` accepts any role ARN — the trust policy
  is NOT validated at creation. A role that does not trust
  `states.amazonaws.com` fails silently at runtime.

- NEVER treat `level: ERROR` as adequate logging. Only failed states are
  logged. Successful executions — including data-exfiltration paths via
  successful `dynamodb:GetItem` or `s3:GetObject` calls — leave no trace.

- NEVER assume X-Ray tracing works just because
  `TracingConfiguration.enabled: true` is set on a Standard workflow. The
  execution role MUST also grant `xray:PutTraceSegments` and
  `xray:PutTelemetryRecords`. Without these permissions, tracing silently
  produces nothing.

- NEVER assume `LoggingConfiguration.level: ALL` is delivering logs just
  because the API accepted it. The execution role MUST grant
  `logs:CreateLogDelivery`, `logs:GetLogDelivery`, `logs:UpdateLogDelivery`,
  `logs:DescribeLogGroups`, and `logs:PutLogEvents`. Without these,
  logging silently fails.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`UpdateStateMachine`, `DeleteStateMachine`, `StopExecution`), the
  auditor MUST emit:
  `CONFIRM: About to <action> on state machine <arn>. This affects
  <consequence>. Proceed? (yes/no)`
  Do NOT execute the CLI command until the operator confirms.

- **Definition changes are unversioned.** `UpdateStateMachine` replaces
  the entire definition atomically — there is no rollback. Capture the
  current definition first:
  `aws stepfunctions describe-state-machine --state-machine-arn <arn> --output json > /tmp/<name>-backup-$(date +%s).json`

- **Role policy changes affect ALL state machines using that role.** An
  execution role may be shared across multiple state machines. Tightening
  the role for one workflow may break another. List dependents before
  modifying:
  `aws resourcegroupstaggingapi get-resources --resource-type-filters states:stateMachine --query "ResourceTagMappingList[].ResourceARN" --output text`
  then grep for the role ARN in each state machine's `roleArn`.

- **Express workflow logging changes take effect immediately for new
  executions** but do NOT retroactively log in-flight executions. Existing
  Express executions continue without logging until they complete.

- **Enabling X-Ray on a Standard workflow** requires the execution role to
  have `xray:PutTraceSegments` + `xray:PutTelemetryRecords`. Add these
  permissions BEFORE enabling tracing, or the first traced execution fails
  with `AccessDenied`.

- **Validate the ASL definition before pushing:**
  `aws stepfunctions validate-state-machine-definition --definition <file> --type STANDARD`
  This catches structural errors before they reach production. It does NOT
  catch missing-Catch or missing-TimeoutSeconds (the auditor does).

- Prefer additive changes (add a `Catch` block, add a `Retry` block) over
  destructive changes (rewriting the definition) — additive changes are
  reversible and lower-risk.

## Remediation guidance

### For OVERPERMISSIVE_ROLE — wildcard or broad execution role

1. **Inventory the definition's service integrations.** Parse each `Task`
   state's `Resource` ARN to identify the exact actions + resources the
   workflow needs.
2. **Generate a scoped policy** granting only those actions on those ARNs.
   Use IAM Access Analyzer policy generation or build manually.
3. **Replace the broad policy:**
   ```
   aws iam put-role-policy --role-name <role> --policy-name Scoped \
     --policy-document file://scoped-policy.json --profile <p>
   ```
4. **For `states:StartExecution` on `*`:** scope to the specific state
   machine ARNs the workflow is permitted to chain into. If self-chaining
   is intended, scope to the workflow's own ARN only.
5. **Verify the trust policy** includes
   `Principal: { Service: "states.amazonaws.com" }`.

### For NO_LOGGING — missing or partial execution logging

1. **Set logging to ALL with execution data:**
   ```
   aws stepfunctions update-state-machine --state-machine-arn <arn> \
     --logging-configuration level=ALL,includeExecutionData=true \
     --profile <p>
   ```
2. **Verify the execution role has logging permissions:**
   `logs:CreateLogDelivery`, `logs:GetLogDelivery`,
   `logs:UpdateLogDelivery`, `logs:DeleteLogDelivery`,
   `logs:DescribeLogGroups`, `logs:PutLogEvents`.
3. **For Express workflows:** this is the ONLY durable record. Treat as
   incident-response priority — without logs, failed Express executions
   are irretrievable after 5-60 minutes.

### For NO_TRACING — missing or ineffective X-Ray tracing

1. **For Standard workflows:** enable tracing:
   ```
   aws stepfunctions update-state-machine --state-machine-arn <arn> \
     --tracing-configuration enabled=true --profile <p>
   ```
2. **Verify the role grants `xray:PutTraceSegments` +**
   `xray:PutTelemetryRecords`. Add if missing.
3. **For Express workflows:** X-Ray via `TracingConfiguration` is a no-op.
   Use CloudWatch Logs ServiceLens for partial distributed visibility.
   Migrate to Standard if full X-Ray tracing is a hard requirement.

### For CONFIG_GAP — definition or error-handling gap

1. **Missing Catch/Retry on a fallible Task:** add a `Catch` block matching
   `States.ALL` (broadest fallback) routing to an error-handler state, and
   a `Retry` block for known-transient errors:
   ```json
   "Catch": [{"ErrorEquals": ["States.ALL"], "Next": "ErrorHandler"}],
   "Retry": [{"ErrorEquals": ["Lambda.ServiceException", "Lambda.TooManyRequestsException"], "IntervalSeconds": 2, "MaxAttempts": 3, "BackoffRate": 2.0}]
   ```
2. **Missing `TimeoutSeconds`:** add an explicit value based on the
   integration's expected runtime (e.g., 30 for a fast Lambda, 300 for
   Glue, 3600 for long ECS tasks).
3. **Missing `HeartbeatSeconds` on Activity Tasks:** set
   `HeartbeatSeconds` < `TimeoutSeconds` (e.g., heartbeat 30, timeout 300).
4. **Unreachable states:** remove them or wire them into the `StartAt`
   chain. Dead states accumulate drift and confuse future maintainers.
5. **Choice without Default:** add a `Default` branch routing to a safe
   fallback or `Fail` state.
6. **Validate before pushing:**
   ```
   aws stepfunctions validate-state-machine-definition --definition file://def.json --type STANDARD
   ```

### For OK

1. No remediation required for the current posture.
2. Recommend periodic review of the execution role as new service
   integrations are added to the definition.
3. Recommend a CloudWatch alarm on `ExecutionsFailed` > threshold for
   early detection of runtime issues logging alone would not surface.

## Deep reference: Step Functions internals

### Execution history vs CloudWatch Logs

Step Functions provides two distinct observability signals:

1. **Execution history** — the canonical event log for an execution,
   queryable via `describe-execution` and the console. Standard workflows:
   90-day retention. Express workflows: 5 minutes (Synchronous) or 1 hour
   (Asynchronous). This is ALWAYS available regardless of
   `LoggingConfiguration`.
2. **CloudWatch Logs delivery** — controlled by `LoggingConfiguration`.
   Delivers the same execution-history events to a CloudWatch Logs group
   for structured queries, metric filters, and alarms. This is what
   `level: ALL` enables.

`NO_LOGGING` means (2) is off, not (1). For Standard, (1) is a 90-day
fallback. For Express, (1) expires in minutes — making (2) the only
durable record. This is why `NO_LOGGING` on Express is operationally
catastrophic.

### X-Ray integration model

X-Ray integrates with Step Functions at the orchestration layer. When
`TracingConfiguration.enabled: true` (Standard only), Step Functions emits
trace segments for each state transition, with sub-segments for each
service integration call. The trace is correlated by the
`X-Amzn-Trace-Id` header, which Step Functions propagates to Lambda,
DynamoDB (when supported), and other X-Ray-integrated services.

The execution role must grant `xray:PutTraceSegments` (for trace data)
and `xray:PutTelemetryRecords` (for service-map telemetry). Without
either, tracing is silently disabled — no error, no alarm.

Express workflows do NOT propagate the trace header the same way. The
`TracingConfiguration` field is accepted but produces no X-Ray console
traces. CloudWatch Logs ServiceLens provides partial distributed visibility
for Express by correlating log entries across services.

### Role evaluation for service integrations

Each `Task` state's `Resource` ARN maps to a specific IAM action:

| Resource pattern | Required IAM action |
|---|---|
| `arn:aws:lambda:*:function:*` | `lambda:InvokeFunction` |
| `arn:aws:dynamodb:*:table/*` | `dynamodb:GetItem`, `PutItem`, `UpdateItem`, `DeleteItem`, `Query`, `Scan` (as used) |
| `arn:aws:sqs:*` | `sqs:SendMessage`, `sqs:ReceiveMessage` |
| `arn:aws:sns:*` | `sns:Publish` |
| `arn:aws:states:*:stateMachine:*` | `states:StartExecution` |
| `arn:aws:states:*:activity:*` | `states:GetActivityTask`, `states:SendTaskSuccess`, `states:SendTaskFailure`, `states:SendTaskHeartbeat` |
| `arn:aws:ecs:*:task/*` | `ecs:RunTask`, `ecs:DescribeTasks`, `ecs:StopTask` |

A scoped execution role grants only the actions corresponding to the
definition's `Resource` ARNs, on the specific resource ARNs (not `*`).

## Recent AWS features (2024-2026)

- **Distributed Map state enhancements (2024-2025):** Distributed Map now supports more item sources (S3 cross-account, DynamoDB) and higher concurrency limits. Auditors should verify that Distributed Map configurations have appropriate `MaxConcurrency` and `ToleratedFailurePercentage` settings — an unbounded Distributed Map can exhaust downstream API quotas.
- **Synchronous Express workflows (Sync) (2024):** Express workflows can now be invoked synchronously via the API. Auditors should verify that synchronous Express workflows have appropriate timeout and error-handling configurations — they cannot use the standard retry/DLQ mechanisms.
- **Step Functions Editor v2 (2024):** The new visual editor supports Workflow Studio with improved ASL validation. No new audit-surface fields.
- **Resource-based policies for state machines (2024-2025):** Enhanced resource-based policy support allowing cross-account state machine execution. Auditors should verify that cross-account execution policies include `aws:SourceAccount` conditions and that `Principal: "*"` policies are bounded.
- **Payload validation (2024):** Step Functions now supports JSON Schema-based payload validation on state inputs. Auditors should verify that payload validation schemas are defined for states handling external input — validation prevents malformed data from propagating through the workflow.

## Domain

AWS CloudOps / Step Functions Observability, Security & ASL Correctness.

## AWS documentation

- **AWS Step Functions Developer Guide** — https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html
- **Step Functions Security** — https://docs.aws.amazon.com/step-functions/latest/dg/security.html
- **Step Functions API Reference** — https://docs.aws.amazon.com/step-functions/latest/apireference/
- **Step Functions CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/stepfunctions/
- **Distributed Map** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-asl-use-map-state-distributed.html
