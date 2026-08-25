# Advanced Patterns — stepfunctions-execution-troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Activation

Activate this skill when the user reports a Step Functions execution
failure. Trigger phrases: "Step Functions execution failed",
"States.Runtime", "States.Timeout", "States.TaskFailed",
"States.Permission", "States.Permissions", "States.ParameterPathFailure",
"States.BranchFailed", "States.ALL not catching", "Step Functions retry
exhausted", "Step Functions MaxAttempts", "Step Functions execution
throttled", "Express workflow 5 minute limit", "Step Functions redrive".

## Mindset

**One-line takeaway:** every Step Functions execution failure has a
structured `error` and `cause` field in `get-execution-history`, and the
exact failing state is named in the execution event stream — these two
signals are the primary diagnostic surface. The job of this skill is to
walk from the error name to the specific root cause by combining the
execution history with the state machine definition, the integration's
IAM role, and CloudWatch Metrics.

Three facts make Step Functions troubleshooting different from generic
service debugging:

- **The `error` string is a States.* name, not an AWS SDK error.**
  `States.Timeout`, `States.TaskFailed`, `States.Permission`,
  `States.Runtime`, `States.ParameterPathFailure`, `States.BranchFailed`
  are the Step Functions runtime's own error names. They identify which
  part of the state machine contract was violated, not which downstream
  service failed. A `States.TaskFailed` for a Lambda invocation may have
  a `cause` containing the Lambda `TaskTimedOut` exception — but the
  Step Functions `error` is still `States.TaskFailed`. Always read both
  fields and never confuse them.

- **Retry and Catch are part of the state machine definition, not the
  runtime.** When retries silently exhaust, the state machine proceeds
  to the Catcher (if any) or fails the execution. Operators often
  report "the execution failed" without realising that the retried
  error fell through `Retry[0].MaxAttempts` over many minutes. The
  retry configuration in the ASL definition is the cause; the execution
  failure is the consequence.

- **Express and Standard workflows have different limits and
  diagnostics.** Express workflows cannot exceed 5 minutes and cannot
  be redriven. Standard workflows can run up to 1 year and support
  redrive from a failed state. Express execution history is delivered
  via CloudWatch Logs under `/aws/vendedlogs/states/express-<...>`,
  not via `get-execution-history` at full fidelity (Express history is
  best-effort and may be truncated). Misdiagnosing the workflow type
  leads to advice that has no effect (e.g., recommending redrive on an
  Express workflow).

## Category precedence rule

**Precedence rule.** When more than one category applies, pick the
innermost cause. `RUNTIME_ERROR` (the ASL itself is malformed at
runtime) precedes `PARAMETER_PATH_FAILURE` (input shape mismatch)
precedes `PERMISSION_DENIED` precedes `TASK_TIMEOUT` precedes
`TASK_FAILED`. A `States.TaskFailed` whose `cause` is
`AccessDeniedException` is a downstream IAM issue; the Step Functions
`error` is `States.TaskFailed` but the actionable cause is in the
`cause` field.

## Catch semantics cheat sheet

**Catch semantics cheat sheet:**

- `States.ALL` catches every error EXCEPT `States.DataDoesNotExist`
  (when used in Choices with `IsPresent`) in some runtime versions.
- `States.TaskFailed` catches only integration failures, NOT
  `States.Timeout`, `States.Permission`, `States.Runtime`.
- To catch all Task-related errors, list:
  `["States.TaskFailed", "States.Timeout", "States.Permission",
  "States.Permissions", "States.ParameterPathFailure"]`.
- Order matters: catchers are evaluated top-down; the first matching
  `ErrorEquals` wins.

## Expert edge cases

These patterns represent genuine, non-obvious Step Functions failure
modes that a senior operator would catch but a generalist would miss.

### States.Permission vs States.TaskFailed for IAM errors

Step Functions emits `States.Permission` when the state machine role
cannot assume the integration's required permissions at the Step
Functions layer (e.g., the role lacks `sts:AssumeRole` on a cross-
account role). It emits `States.TaskFailed` with a `cause` of
`AccessDeniedException` when the integration itself denies the action.
Operators often conflate these — the fix for the former is on the Step
Functions role; the fix for the latter is on either the Step Functions
role OR the target resource's policy.

### Express execution history is best-effort

For Express workflows, `get-execution-history` returns a best-effort
view delivered via CloudWatch Logs. Under high throughput, history
events may be truncated or delayed. For definitive diagnosis, query
the CloudWatch Log Group directly:

```bash
aws logs filter-log-events \
  --log-group-name /aws/vendedlogs/states/express-<sm-name>-Logs-<hash> \
  --filter-pattern "ExecutionFailed" \
  --start-time <epoch-ms>
```

A missing event in `get-execution-history` for an Express workflow is
NOT evidence the event did not occur.

### States.ALL does not catch everything

Despite the name, `States.ALL` does not catch:

- `States.DataDoesNotExist` (older runtimes, when used with
  Choice `IsPresent`).
- Some internal runtime errors that pre-empt the Catch evaluation.

If the operator needs a true catch-all, list the explicit errors
they care about. `States.ALL` is a convenience, not a guarantee.

### Distributed Map child execution ARNs are in the parent history

When a Distributed Map state fails, the parent execution's history
contains `MapRunStarted` and `MapRunFailed` events with the Map Run
ARN. The per-iteration failures are surfaced via
`aws stepfunctions describe-map-run` and the child execution ARNs.
Operators often stop at the parent's `States.BranchFailed` and miss
the actual iteration error.

### Activity worker HeartbeatSeconds must be < TimeoutSeconds

If `HeartbeatSeconds >= TimeoutSeconds`, the runtime rejects the state
definition at creation time. Less obvious: if the worker's actual
heartbeat interval is greater than `HeartbeatSeconds`, the task will
time out even though the worker is making progress. The worker should
call `SendTaskHeartbeat` at `HeartbeatSeconds / 2` intervals.

### Retry does not apply to Catch-less errors that the runtime will not retry

Step Functions retries only the errors listed in `Retry[].ErrorEquals`.
A common mistake is adding `Retry` for `States.TaskFailed` expecting
it to retry Lambda `Unhandled` exceptions — it will, but only if
`ErrorEquals` includes `States.TaskFailed` (or `States.ALL`). Adding
the Lambda-specific error name `Unhandled` to `ErrorEquals` will NOT
match, because Step Functions only sees the wrapped `States.TaskFailed`.

### Redrive does not re-run succeeded states

When redriving a Standard execution, only the failed state and any
states downstream of it re-run. If the root cause was an IAM permission
fix, the previously-failed state will now succeed. If the root cause
was an ASL change to an upstream state, the upstream change will NOT
be picked up by redrive — you must start a new execution. Operators
often redrive expecting the ASL changes to apply, then are surprised
when the same state fails the same way.

### Service integration .sync polling uses the state machine role

For `.sync` integrations (e.g., Glue StartJobRun.sync), Step Functions
polls the integration on the state machine's behalf using the state
machine's role. The role needs both the start action AND the describe
action (e.g., `glue:StartJobRun` AND `glue:GetJobRun`). A role with
only the start action will succeed at start but fail at the polling
step with `States.Permission` after several minutes.

## Expert heuristic — "Read the cause, not the error"

The single most common diagnostic mistake is treating the Step
Functions `error` name as the root cause. It is not. It is the runtime
category. The `cause` field carries the downstream service's actual
error message — and that is the actionable signal.

Quick lookup table for common `error` → real cause mappings:

| `error` | What it means | Where the real cause lives |
|---|---|---|
| `States.Runtime` | ASL runtime error (invalid JSONPath, unsupported operation) | The `cause` string names the offending path — read the ASL state |
| `States.Timeout` | Task exceeded `TimeoutSeconds` or missed `HeartbeatSeconds` | Read the state's timeout config vs integration latency |
| `States.TaskFailed` | Integration returned a non-success response | The `cause` is the integration's SDK error — parse it as JSON |
| `States.Permission` | State machine role cannot perform the action | `iam simulate-principal-policy` on the role |
| `States.ParameterPathFailure` | `Parameters` JSONPath did not resolve | The `cause` names the missing path — read the input payload |
| `States.BranchFailed` | A Parallel / Map branch failed | Read the branch's own execution history |
| `States.ALL` (in a Catcher) | Not an error — a catch specifier | N/A |

When in doubt, run:
`aws stepfunctions describe-execution --execution-arn <arn>` and read
the `error` and `cause` fields. The `cause` is the actionable signal;
the `error` is the category.

## Recent AWS features (2024-2026)

- **Redrive (Standard workflows, GA 2024):** re-execute a failed
  Standard execution from the failed state. Verify `redriveStatus:
  REDRIVABLE` via `describe-execution`. Express workflows are NOT
  eligible.
- **Distributed Map (2024 enhancements):** larger item counts, S3 and
  CSV item sources, child execution ARNs surfaced in parent history.
  Troubleshoot Distributed Map failures via `describe-map-run`.
- **Step Functions JSONata support (2024-2025):** newer workflows can
  use JSONata instead of JSONPath. `States.Runtime` errors in JSONata
  workflows have different cause strings — read the `cause` carefully.
- **Express workflow history via CloudWatch Logs insights:** enhanced
  query support for the vended logs group. Use CloudWatch Logs
  Insights instead of `get-execution-history` for high-volume Express
  workflows.
- **Variable and state persistence (2025):** workflows can persist
  variables across state transitions. Misuse produces
  `States.ParameterPathFailure` on the variable reference — read the
  variable definition.
- **Service Quotas for state transitions:** account-level quota for
  state transitions per second. `ThrottledStateTransition` indicates
  the quota was exceeded — request an increase via Service Quotas.
