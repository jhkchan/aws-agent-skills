# Step Functions error catalog and decision tree

On-demand reference for the `stepfunctions-execution-troubleshooter`
skill. Loaded when the skill needs the full per-category walk with
worked examples. The SKILL.md contains the summary table; this file
expands each category with verbatim `error` and `cause` examples, the
diagnostic walk, and the canonical fix.

## How to use this file

1. Identify the `error` value from `describe-execution` or
   `get-execution-history`.
2. Jump to the matching section below.
3. Follow the walk; cross-reference evidence with the worked example.

---

## A. RUNTIME_ERROR — States.Runtime

### Signature

```text
error: "States.Runtime"
cause: "An error occurred while executing the state '<state-name>'." \
       (may include the specific JSONPath that failed)
```

### Decision tree

1. **Read the `cause` for the offending JSONPath.** Common cause
   strings:
   - "Invalid path: ..."
   - "The JSONPath provided is invalid"
   - "The field ... is not supported"
2. **Read the ASL definition of the named state.**
3. **Identify the JSONPath field at fault:**
   - `InputPath`
   - `OutputPath`
   - `ResultPath`
   - `ResultSelector`
   - `Parameters` (each `.<key>.$` entry)
   - `ItemsPath` (Map states)
   - `Iterator` (Distributed Map)
4. **Cross-reference the path against the actual input payload** to the
   state (from `get-execution-history` `StateEntered` event).

### Top sub-causes

| Sub-cause | Example | Fix |
|---|---|---|
| JSONPath does not parse | `$.input..nested` with no terminator | Use `$.input.nested` or `$.input[*].nested` |
| Field does not exist in payload | `$.orderId` when payload has `$.order.id` | Align the path or upstream `ResultPath` |
| `ResultPath` collides with input field | `ResultPath: "$.result"` with input already containing `result` | Use `ResultPath: "$.taskResult"` or `ResultPath: null` |
| Used a filter expression `?()` on an unsupported integration | Activity tasks do not support filters | Drop filter; post-process in a Pass state |
| JSONata syntax error (2024+ runtimes) | Mixing JSONPath `$.` with JSONata `{}` in the same expression | Pick one syntax per workflow |

### Worked example

```text
INCIDENT: arn:aws:states:us-east-1:111111111111:stateMachine:order-pipeline
 / arn:aws:states:us-east-1:111111111111:execution:order-pipeline:abc —
 States.Runtime on state EnrichOrder
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: RUNTIME_ERROR — state EnrichOrder's Parameters references
"OrderId.$": "$.order.orderId" but the upstream state emits the field
at "$.orderId" (no nested object)
EVIDENCE:
  - describe-execution: error "States.Runtime", cause "An error
    occurred while executing the state 'EnrichOrder'"
  - get-execution-history StateEntered for EnrichOrder: input
    { "orderId": "ord-123", "customerId": "cust-9" }
  - describe-state-machine EnrichOrder Parameters:
    { "OrderId.$": "$.order.orderId" }
ROOT_CAUSE_CATALOG: #1 (invalid JSONPath)
REMEDIATION:
  1. Update the EnrichOrder Parameters to reference the actual path:
     "OrderId.$": "$.orderId"
  2. Validate the ASL via TestState API before deploying:
     aws stepfunctions test-state --definition <asl> --role-arn <role> --input file://test-input.json
  3. Re-run the execution with the original input; the EnrichOrder
     state should now succeed.
```

---

## B. TASK_TIMEOUT — States.Timeout

### Signature

```text
error: "States.Timeout"
cause: "Task timed out at <iso>"
```

### Decision tree

1. **Read the state's `TimeoutSeconds` and `HeartbeatSeconds`.**
2. **For synchronous Lambda invokes:** compare `TimeoutSeconds` against
   the function's own `Timeout` and CloudWatch Logs for actual duration.
3. **For activity tasks:** verify the worker is calling
   `SendTaskHeartbeat` at intervals < `HeartbeatSeconds`.
4. **For `.sync` integrations (Glue, Athena, Batch):** the
   `TimeoutSeconds` should cover the integration's p99 runtime; if it
   cannot, switch to a polling pattern via the `.waitForTaskToken`
   integration.

### Top sub-causes

| Sub-cause | Example | Fix |
|---|---|---|
| Lambda invoke exceeds `TimeoutSeconds` | State `TimeoutSeconds: 60`, function averages 90s | Raise state `TimeoutSeconds` to 120; raise function `Timeout` to 100 |
| Activity worker missed heartbeat | `HeartbeatSeconds: 30`, worker heartbeats every 60s | Worker should heartbeat at `HeartbeatSeconds / 2` |
| Glue `.sync` exceeds 1 hour | Default `TimeoutSeconds: 60`, job runs 90 min | Raise to 7200; or use activity pattern for very long jobs |
| Express workflow `ExecutionTimedOut` | Express execution at 305s | See EXECUTION_LIMIT_HIT — this is NOT a per-task timeout |

---

## C. TASK_FAILED — States.TaskFailed

### Signature

```text
error: "States.TaskFailed"
cause: "<downstream SDK error, often JSON-encoded>"
```

### Decision tree

1. **Parse the `cause`.** Common shapes:
   - Lambda: `{"errorMessage": "...", "errorType": "...", "requestId": "..."}`
   - DynamoDB: `{"message": "...", "code": "ProvisionedThroughputExceededException"}`
   - S3: `{"message": "...", "code": "NoSuchKey"}`
2. **Identify whether the error is retryable.**
   - Retryable: `ThrottlingException`, `ServiceUnavailable`,
     `ProvisionedThroughputExceededException`, `RequestLimitExceeded`.
   - Non-retryable: `ResourceNotFoundException`, `ValidationException`,
     `UnauthorizedOperation`.
3. **Match against `Retry[].ErrorEquals`** in the state definition.
4. **For Lambda `Unhandled`**, read the function's CloudWatch Logs and
   fix the function before retrying.

### Top sub-causes

| Sub-cause | Real root cause | Fix |
|---|---|---|
| `ProvisionedThroughputExceededException` | DynamoDB capacity too low | Raise capacity; add Retry with backoff |
| `ThrottlingException` (Lambda) | Concurrent invocations > account quota | Request quota increase; add Retry |
| `ResourceNotFoundException` | Wrong ARN in `Parameters` | Verify resource exists |
| `AccessDeniedException` | IAM permission missing (see PERMISSION_DENIED) | Fix IAM |
| Lambda `Unhandled` | Function threw uncaught exception | Fix function code |
| `StateMachineDoesNotExist` | Nested state machine ARN wrong | Update Parameters |

---

## D. PERMISSION_DENIED — States.Permission / States.Permissions

### Signature

```text
error: "States.Permission"
cause: "Is not authorized to assume role ..." OR
       "is not authorized to perform: <service>:<action>"
```

### Decision tree

1. **Read `roleArn` from `describe-state-machine`.**
2. **Identify the action and resource** the failing state needs.
3. **Simulate the role:**
   ```bash
   aws iam simulate-principal-policy \
     --policy-source-arn <role-arn> \
     --action-names <service>:<Action> \
     --resource-arns <resource-arn>
   ```
4. **For cross-account,** also read the target resource's policy.

### States.Permission vs States.TaskFailed for IAM

| Symptom | Step Functions layer | Action |
|---|---|---|
| State machine role lacks `lambda:InvokeFunction` | Step Functions layer | `States.Permission` (sometimes) or `States.TaskFailed` with `AccessDeniedException` |
| State machine role cannot assume cross-account role | Step Functions layer (assume role) | `States.Permission` |
| Resource policy in target account denies the role | Downstream layer | `States.TaskFailed` with `AccessDeniedException` |
| KMS key policy denies the role (for encrypted resources) | Downstream layer | `States.TaskFailed` with `AccessDeniedException` |

The Step Functions `error` field alone is insufficient — read the
`cause` to determine which layer is failing.

---

## E. PARAMETER_PATH_FAILURE — States.ParameterPathFailure

### Signature

```text
error: "States.ParameterPathFailure"
cause: "An error occurred while executing the state '<state>'."
       "Parameters" field references a path that does not exist.
```

### Decision tree

1. **Read the failing state's `Parameters` block.**
2. **For each `.<key>.$` entry,** verify the path resolves in the
   state's input.
3. **Trace the input shape** from upstream states.

### Top sub-causes

| Sub-cause | Fix |
|---|---|
| `Parameters` references `$.orderId` but payload has `$.order.id` | Align the path |
| Map state `ItemsPath` points to a non-array | Fix `ItemsPath` or upstream payload |
| Used `.$` on a literal value | Drop `.$` for literals |
| Used `$$.Execution.Name` (context object) on an integration that does not expose the context | Use a Pass state to materialize the context field |

---

## F. BRANCH_FAILED — States.BranchFailed

### Signature

```text
error: "States.BranchFailed"
cause: "<inner branch error wrapped>"
```

### Decision tree

1. **Read the Map / Parallel state definition.**
2. **For Distributed Map:** the child execution ARNs are in the parent
   history. Read each child's history.
3. **For inline Map / Parallel:** the branch error is surfaced in the
   parent history under `mapIterationFailed` or `branchFailed`.
4. **Diagnose the inner failure** using the matching category walk.

---

## G. RETRY_EXHAUSTED

### Signature

```text
Execution FAILED after N+1 TaskFailed events for the same state
(where N = Retry[0].MaxAttempts)
No Catcher, or Catcher ErrorEquals does not match
```

### Decision tree

1. **Read `Retry[0]` in the state definition.**
2. **Count `TaskFailed` events** in the execution history for this
   state — should equal `MaxAttempts + 1`.
3. **Verify the Catcher** — if absent or `ErrorEquals` does not match,
   the execution fails terminally.
4. **Identify the underlying error** from the last `TaskFailed` event.

### Top sub-causes

| Sub-cause | Fix |
|---|---|
| `Retry[0].ErrorEquals: ["States.Timeout"]` but actual error is `States.TaskFailed` | Add the actual error name OR use `States.ALL` |
| `MaxAttempts: 3` but downstream outage lasted longer | Raise `MaxAttempts` AND `BackoffRate`; consider a dead-letter state via Catch |
| Catcher exists but `ErrorEquals` lists the wrong error | Update `ErrorEquals` to match the actual error |
| Retries fired but downstream never recovered | Fix downstream; do not raise `MaxAttempts` as a workaround |

---

## H. CATCH_MISCONFIGURED

### Catch semantics

| `ErrorEquals` value | Catches |
|---|---|
| `States.ALL` | Almost all errors — EXCEPT `States.DataDoesNotExist` and some runtime errors |
| `States.TaskFailed` | Only integration failures — NOT `States.Timeout`, `States.Permission`, `States.Runtime` |
| `States.Timeout` | Only timeout errors |
| `Lambda.TooManyRequestsException` | NOT matched — Step Functions only sees the wrapped `States.TaskFailed` |
| `["States.TaskFailed", "States.Timeout"]` | Both — list explicitly for multi-error catches |

### Decision tree

1. **Read the actual `error` value** that escaped the Catcher.
2. **Read the `Catch[].ErrorEquals` array.**
3. **Verify the mismatch** — the actual error is not in the array.
4. **Update `ErrorEquals`** to include the actual error, or use
   `States.ALL` with documented caveats.

---

## I. EXECUTION_LIMIT_HIT

### Limits

| Workflow type | Max duration | Redrive |
|---|---|---|
| Express (ASYNC or SYNC) | 5 minutes (300s) hard cap | NOT supported |
| Standard | 1 year | Supported |

### Decision tree

1. **Read `StateMachineType`** via `describe-state-machine`.
2. **For Express `ExecutionTimedOut`:** refactor or migrate.
3. **For `ExecutionThrottled` / `ThrottledStateTransition`:** request
   Service Quota increase; reduce transition count.

---

## J. REDRIVE_CANDIDATE

### Eligibility

- Workflow type MUST be STANDARD.
- Execution status MUST be FAILED (or SUCCEEDED with redriveable
  states).
- `redriveStatus: REDRIVABLE` from `describe-execution`.

### What redrive does

- Re-runs the failed state.
- Re-runs all downstream states.
- Does NOT re-run succeeded states.
- Does NOT pick up ASL changes to upstream states — those require a
  fresh execution.

### Common gotchas

- Root cause not fixed: redrive will fail identically.
- ASL changed on an upstream state: redrive will not pick up the
  change.
- Map state failure: Distributed Map re-runs only failed iterations;
  inline Map re-runs the whole Map.
- Input payload at the failed state may differ from what the operator
  expects — read the `StateEntered` event from the original history.
