# Step Functions State Machine Auditor - advanced patterns (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Step 0: Expert knowledge - non-obvious Step Functions behaviors

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

