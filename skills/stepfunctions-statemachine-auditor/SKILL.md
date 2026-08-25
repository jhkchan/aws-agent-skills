---
name: stepfunctions-statemachine-auditor
description: Audits AWS Step Functions state machines for execution logging coverage (level ALL + includeExecutionData), X-Ray tracing enablement (including the Express-workflow no-op trap), execution-role blast radius (wildcard actions, states:StartExecution chaining, iam:PassRole), and ASL definition validation (missing Catch/Retry on fallible Tasks, missing TimeoutSeconds, unreachable states, cyclic references without exit). Emits a deterministic verdict (NO_LOGGING | NO_TRACING | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK) per state machine with enumerated findings and specific remediation. Use when reviewing Step Functions state machines, checking logging coverage, validating X-Ray tracing, auditing execution-role scope, validating ASL definitions, or hardening state machine observability and security posture before production deployment.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline state-machine classification. Live-account audits use aws stepfunctions describe-state-machine, aws stepfunctions describe-execution, aws iam get-role-policy, and aws stepfunctions validate-state-machine-definition (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  verdict_shape: NO_LOGGING | NO_TRACING | OVERPERMISSIVE_ROLE | CONFIG_GAP | OK
  when_to_use: Reviewing a Step Functions state machine before production deployment, checking execution logging coverage, validating X-Ray tracing enablement, auditing the execution role's blast radius, validating ASL definition correctness (unreachable/cyclic states, missing error handling), or hardening state machine observability and security posture.
  activation_triggers: audit this state machine, check Step Functions logging, is X-Ray tracing enabled, state machine execution role too broad, validate ASL definition, missing Catch block, Express workflow tracing, state machine error handling, unreachable states in ASL, Step Functions blast radius
  invocation_schema: 'Input: either (a) a Step Functions state machine configuration (definition + type + loggingConfiguration + tracingConfiguration + roleArn + role policy), OR (b) a state-machine ARN for live-account audit. Output: deterministic STATE_MACHINE/VERDICT/REASON/FINDINGS/ REMEDIATION block per state machine, where VERDICT is one of NO_LOGGING, NO_TRACING, OVERPERMISSIVE_ROLE, CONFIG_GAP, OK, or ERROR.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Step Functions, state machine, ASL, Amazon States Language, execution logging, CloudWatch Logs, X-Ray tracing, distributed tracing, Express workflow, Standard workflow, execution role, IAM blast radius, states:StartExecution, iam:PassRole, definition validation, circular states, unreachable states, Catch block, Retry block, TimeoutSeconds, HeartbeatSeconds, error handling, Task state, Choice state, Map state, Parallel state, state machine audit
  tags: stepfunctions, app-integration, security, observability, state-machine, asl, xray, logging, iam, audit
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

> Full detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand.
> Summary: the complete Step 0 catalog of non-obvious Step Functions behaviors that change audit verdicts.

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

> Full detail moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand.
> Summary: the full pre-remediation safety checklist with CLI listings (confirmation gate, backups, dependents).

## Remediation guidance

> Full detail moved verbatim to [references/error-handling.md](references/error-handling.md) - load on demand.
> Summary: the per-verdict remediation playbooks (OVERPERMISSIVE_ROLE, NO_LOGGING, NO_TRACING, CONFIG_GAP, OK).

## Deep reference: Step Functions internals

> Full detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand.
> Summary: the internals deep-dive (execution history vs CloudWatch Logs, X-Ray model, role evaluation table).

## Recent AWS features (2024-2026)

> Full detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand.
> Summary: the 2024-2026 feature notes relevant to auditing.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) - Step 0 expert knowledge, Step Functions internals deep reference, recent AWS features
- [references/diagnostic-commands.md](references/diagnostic-commands.md) - pre-remediation safety checks and CLI listings
- [references/error-handling.md](references/error-handling.md) - per-verdict remediation playbooks

## Domain

AWS CloudOps / Step Functions Observability, Security & ASL Correctness.

## AWS documentation

- **AWS Step Functions Developer Guide** — https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html
- **Step Functions Security** — https://docs.aws.amazon.com/step-functions/latest/dg/security.html
- **Step Functions API Reference** — https://docs.aws.amazon.com/step-functions/latest/apireference/
- **Step Functions CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/stepfunctions/
- **Distributed Map** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-asl-use-map-state-distributed.html
