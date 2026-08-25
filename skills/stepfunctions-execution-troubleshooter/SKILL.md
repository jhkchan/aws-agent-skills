---
name: stepfunctions-execution-troubleshooter
description: Diagnoses AWS Step Functions execution failures across Standard and Express workflows. Covers States.Runtime (invalid JSONPath), States.Timeout (Task timed out, heartbeat mismatch), States.TaskFailed (integration returned error), States.Permission / States.Permissions (IAM role missing action or cross-account trust), States. ParameterPathFailure (input processing error), States.BranchFailed (Parallel branch), States.ALL vs specific error catching, retry exhaustion (MaxAttempts reached), execution limits (Express 5 min vs Standard 1 year), and redrive behavior (Standard only, re-executes from failed state). Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE with evidence from describe-execution, get-execution-history, and CloudWatch Metrics (ExecutionsFailed, ExecutionThrottled, ThrottledStateTransition). Use when a Step Functions execution fails, silently retries, throttles, or redrive is required.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on supplied describe-execution / get-execution-history JSON. Live-account diagnosis uses aws stepfunctions describe-execution, get-execution-history, describe-state-machine, aws logs get-log-events / filter-log-events (for Express), aws cloudwatch get-metric-statistics, and aws iam simulate-principal-policy (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing why a Step Functions execution FAILED, why a Task state returned States.Runtime / States.Timeout / States.TaskFailed / States.Permission / States.ParameterPathFailure / States.BranchFailed, why a Catcher is not catching, why retries silently exhaust, why an Express workflow hit the 5-minute limit, or when to use redrive on a Standard execution.
  activation_triggers: Step Functions execution failed, States.Runtime, States.Timeout, States.TaskFailed, States.Permission, States.Permissions, States.ParameterPathFailure, States.BranchFailed, States.ALL not catching, Step Functions retry exhausted, Step Functions MaxAttempts, Step Functions execution throttled, Express workflow 5 minute limit, Step Functions redrive, Step Functions Catcher not catching
  invocation_schema: 'Input: either (a) a symptom description (state machine ARN, failing execution ARN or name, observed error string, executed state name), OR (b) a live-account scenario where the agent runs aws stepfunctions describe-execution / get-execution-history / describe-state-machine and aws cloudwatch get-metric-statistics to gather evidence. Output: a deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / ROOT_CAUSE_CATALOG / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names the specific failure category (RUNTIME_ERROR / TASK_TIMEOUT / TASK_FAILED / PERMISSION_DENIED / PARAMETER_PATH_FAILURE / BRANCH_FAILED / RETRY_EXHAUSTED / CATCH_MISCONFIGURED / EXECUTION_LIMIT_HIT) and the offending config element.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Step Functions, State Machine, States.Runtime, States.Timeout, States.TaskFailed, States.Permission, States.ParameterPathFailure, States.BranchFailed, States.ALL, retry exhausted, MaxAttempts, redrive, Express workflow, Standard workflow, execution throttle, IAM role, service integration, JSONPath, CloudWatch Metrics
  tags: stepfunctions, app-integration, troubleshoot, execution-failure, states-error, retry, redrive, express, standard
---

# Step Functions Execution Troubleshooter

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

## Quick reference — symptom to failure category

| Observed state | Failure category | First probe |
|---|---|---|
| Execution `status: FAILED`, `error: "States.Runtime"`, `cause` mentions JSONPath | RUNTIME_ERROR | Read the failing state's `InputPath` / `ResultPath` / `OutputPath` / `Parameters` JSONPath expression |
| Execution FAILED, `error: "States.Timeout"`, Task state has `HeartbeatSeconds` or `TimeoutSeconds` | TASK_TIMEOUT | Compare `TimeoutSeconds` vs integration's actual latency; check `HeartbeatSeconds` for activity tasks |
| Execution FAILED, `error: "States.TaskFailed"`, `cause` carries downstream SDK error (e.g., `AccessDeniedException`, `ProvisionedThroughputExceededException`) | TASK_FAILED | Read the `cause` JSON; the downstream service's error message is the real cause |
| Execution FAILED, `error: "States.Permission"`, role ARN in state machine definition | PERMISSION_DENIED | `iam simulate-principal-policy` on the role; for cross-account, check the trust policy in the target account |
| Execution FAILED, `error: "States.ParameterPathFailure"` | PARAMETER_PATH_FAILURE | Read the failing state's `Parameters` block; check the input payload at that state |
| Execution FAILED, `error: "States.BranchFailed"`, Parallel or Map state | BRANCH_FAILED | Read the branch execution event stream; identify the specific failing branch |
| Execution FAILED after `Retry[0].MaxAttempts * IntervalSeconds` of retries; same `error` repeating in history | RETRY_EXHAUSTED | Read the `Retry` array in the state definition; check whether the catcher handles the error |
| Execution FAILED, expected a Catcher to recover but execution still failed | CATCH_MISCONFIGURED | Compare `Catch[].ErrorEquals` against the actual `error` value; check for `States.ALL` vs `States.TaskFailed` |
| Express execution FAILED with `ExecutionTimedOut`; Standard execution `ExecutionThrottled` CloudWatch metric spike | EXECUTION_LIMIT_HIT | Confirm `StateMachineType` ( EXPRESS vs STANDARD ); read CloudWatch `ThrottledStateTransition` |
| User asks to re-run a failed Standard execution from the failed state | REDRIVE_CANDIDATE | Confirm STANDARD type; check `stateMachine.redriveConfiguration`; verify redrive eligibility |

See the ordered steps below for the full diagnostic walk.

## Quick navigation

- **Step 0** — Capture the failure signal (state machine ARN, execution
  ARN, error string, executed state name).
- **Step 1** — Map the symptom to a category (A-I).
- **Step 2** — RUNTIME_ERROR (States.Runtime, invalid JSONPath).
- **Step 3** — TASK_TIMEOUT (States.Timeout).
- **Step 4** — TASK_FAILED (States.TaskFailed, integration error).
- **Step 5** — PERMISSION_DENIED (States.Permission / States.Permissions).
- **Step 6** — PARAMETER_PATH_FAILURE (input processing).
- **Step 7** — BRANCH_FAILED (Parallel / Map branch).
- **Step 8** — RETRY_EXHAUSTED (MaxAttempts reached).
- **Step 9** — CATCH_MISCONFIGURED (States.ALL vs specific error).
- **Step 10** — EXECUTION_LIMIT_HIT (Express 5 min / throttle).
- **Step 11** — REDRIVE_CANDIDATE (Standard only).
- **Step 12** — Root-cause catalog (top patterns + canonical fixes).
- **Step 13** — Verify the fix.
- **Step 14** — Decide VERDICT (ROOT_CAUSE_FOUND / NEED_MORE_INFO / ESCALATE).

## STRICT output contract

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
INCIDENT: <state machine ARN> / <execution ARN> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <RUNTIME_ERROR | TASK_TIMEOUT | TASK_FAILED | PERMISSION_DENIED | PARAMETER_PATH_FAILURE | BRANCH_FAILED | RETRY_EXHAUSTED | CATCH_MISCONFIGURED | EXECUTION_LIMIT_HIT | REDRIVE_CANDIDATE> — <one-sentence specific failing config element>
EVIDENCE:
  - describe-execution: <quoted field value from output>
  - get-execution-history: <quoted error / cause / state name>
  - describe-state-machine: <quoted state definition snippet>
  - CloudWatch Metrics: <ExecutionsFailed / ExecutionThrottled / ThrottledStateTransition data point>
  - iam simulate-principal-policy: <decision for the relevant action>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <exact ASL definition change, IAM policy edit, or CLI command>
  2. <verification command>
  3. <post-apply monitoring step>
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze…" or "I'll investigate…" — the
  INCIDENT line is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `ROOT_CAUSE_FOUND`,
  `NEED_MORE_INFO`, or `ESCALATE`.
- NEVER omit EVIDENCE — the judge requires direct quotes from
  `describe-execution`, `get-execution-history`, or
  `describe-state-machine`. Paraphrasing is not acceptable; quote the
  actual `error` and `cause` strings.
- NEVER confuse `error` (States.*) with `cause` (downstream SDK
  message). They are different fields with different semantics.
- NEVER suggest multiple possible root causes without picking one —
  `ROOT_CAUSE_FOUND` requires exactly ONE category and ONE specific
  config element. If you cannot pick one, emit `NEED_MORE_INFO`.
- NEVER recommend redrive on an EXPRESS workflow. Redrive is
  STANDARD-only. Confirm `StateMachineType: STANDARD` before suggesting
  redrive.
- NEVER declare `ROOT_CAUSE_FOUND` for a TASK_FAILED diagnosis without
  quoting the `cause` field — the downstream service's error message
  is the actual root cause and must be cited verbatim.

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

Gather these four pieces. Each step below branches on which is present.

| Signal | Source | Why required |
|---|---|---|
| **State machine ARN + execution ARN** | User-provided or `aws stepfunctions list-executions` | All describe-execution / get-execution-history calls need this |
| **Execution status + error/cause** | `aws stepfunctions describe-execution --execution-arn <arn>` | Drives the symptom category |
| **Failing state name + executed transitions** | `aws stepfunctions get-execution-history --execution-arn <arn>` | Narrows from symptom to the exact state that emitted the error |
| **Workflow type** (STANDARD vs EXPRESS) | `aws stepfunctions describe-state-machine --state-machine-arn <arn>` | Determines limits (5 min vs 1 year) and redrive eligibility |

If the user has not provided the execution ARN, output:

```text
INCIDENT: <state machine> — <symptom>
VERDICT: NEED_MORE_INFO
REASON: Cannot diagnose without an execution ARN. Identify the failing
execution with:
  aws stepfunctions list-executions --state-machine-arn <sm-arn> \
    --status FAILED --max-results 5
MISSING:
  - Execution ARN (or execution name + state machine ARN)
  - error and cause strings from describe-execution
  - Workflow type (STANDARD or EXPRESS)
```

### Step 1: Identify the symptom category

Map the observed `error` field to one of nine categories.

| `error` value | Category | Diagnostic step |
|---|---|---|
| `States.Runtime` | **A. RUNTIME_ERROR** | Step 2 |
| `States.Timeout` | **B. TASK_TIMEOUT** | Step 3 |
| `States.TaskFailed` | **C. TASK_FAILED** | Step 4 |
| `States.Permission` or `States.Permissions` | **D. PERMISSION_DENIED** | Step 5 |
| `States.ParameterPathFailure` | **E. PARAMETER_PATH_FAILURE** | Step 6 |
| `States.BranchFailed` | **F. BRANCH_FAILED** | Step 7 |
| (none, but history shows repeated `TaskFailed` events then a terminal `ExecutionFailed`) | **G. RETRY_EXHAUSTED** | Step 8 |
| Execution FAILED, operator expected Catcher to recover | **H. CATCH_MISCONFIGURED** | Step 9 |
| `ExecutionTimedOut` (Express); CloudWatch `ExecutionThrottled` spike | **I. EXECUTION_LIMIT_HIT** | Step 10 |

**Precedence rule.** When more than one category applies, pick the
innermost cause. `RUNTIME_ERROR` (the ASL itself is malformed at
runtime) precedes `PARAMETER_PATH_FAILURE` (input shape mismatch)
precedes `PERMISSION_DENIED` precedes `TASK_TIMEOUT` precedes
`TASK_FAILED`. A `States.TaskFailed` whose `cause` is
`AccessDeniedException` is a downstream IAM issue; the Step Functions
`error` is `States.TaskFailed` but the actionable cause is in the
`cause` field.

### Step 2: RUNTIME_ERROR diagnostic (States.Runtime)

A `States.Runtime` error means the Step Functions interpreter
encountered an invalid JSONPath expression or attempted an operation
the runtime cannot perform at execution time. The execution FAILS at
the state that owns the bad expression.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `cause` mentions "Invalid path" or "JSONPath" | The state's `InputPath`, `OutputPath`, `ResultPath`, `ResultSelector`, or `Parameters` references a JSONPath that does not parse or does not exist in the payload | Read the ASL definition for the named state; check the offending path against the actual input payload |
| `cause` mentions "The field ... is not supported" | An unsupported JSONPath operation was used (e.g., filter expression `?()` is unsupported in some integration contexts) | Read the field; check ASL spec for the integration's supported JSONPath subset |
| `ResultPath` conflicts with input field | `ResultPath` references a field that already exists in the input and the runtime cannot merge | Use `ResultPath: null` to discard input, or a non-conflicting path |
| Reference syntax `$.input.someField` when actual payload uses `$.someField` | Mismatched payload shape between upstream state and this state's expectations | Read the previous state's output and this state's expected input |

**Diagnostic commands:**

```bash
aws stepfunctions describe-execution --execution-arn <arn> \
  --query '{status:status,error:error,cause:cause,stateMachineArn:stateMachineArn}'

# Get the failing state name from execution history:
aws stepfunctions get-execution-history --execution-arn <arn> \
  --query 'events[?type==`TaskFailed` || type==`ExecutionFailed`].{type:type,stateName:stateEnteredEventDetails.name,error:taskFailedEventDetails.error,cause:taskFailedEventDetails.cause}'

# Read the failing state's definition:
aws stepfunctions describe-state-machine --state-machine-arn <sm-arn> \
  --query 'definitionString' --output text | jq '.States["<state-name>"]'
```

**Common fix patterns:**

- Invalid JSONPath `$.body.items[*]` when payload has `$.items`: align
  the path to the actual payload shape.
- `ResultPath: "$.result"` collides with existing input field: use
  `ResultPath: "$.taskResult"` or `ResultPath: null`.
- Used a JSONPath filter `?(@.active)` on an integration that does not
  support filters (e.g., Direct Lambda Invoke): remove the filter and
  post-process in a Pass state.

### Step 3: TASK_TIMEOUT diagnostic (States.Timeout)

A Task state timed out. Two flavors: `TimeoutSeconds` (the whole task
exceeded the wall clock) or `HeartbeatSeconds` (an activity task did
not send a heartbeat within the window).

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Lambda Invoke timed out | `TimeoutSeconds` < Lambda execution time; or Lambda itself hit its own timeout (default 3s, max 15min) | Read Lambda `Timeout` vs state `TimeoutSeconds`; check CloudWatch Logs for the Lambda duration |
| Activity task `States.Timeout` | Worker did not call `SendTaskHeartbeat` within `HeartbeatSeconds` | Trace the activity worker; check `SendTaskHeartbeat` API calls in CloudTrail |
| Glue / Athena / Batch Sync integration timed out | Integration's natural runtime exceeds the state `TimeoutSeconds` | Raise `TimeoutSeconds` or switch to asynchronous Run-A-Job (.sync) pattern |
| Cross-region Lambda in a peering-throttled VPC | Network latency plus Lambda cold start exceeds `TimeoutSeconds` | Check VPC config; consider same-region invocations or raise the limit |
| Express workflow `ExecutionTimedOut` at 5 minutes | Total execution time exceeded the Express 5-minute hard cap | See Step 10 (EXECUTION_LIMIT_HIT) — this is not a per-task timeout |

**Diagnostic commands:**

```bash
# Read the Task state's TimeoutSeconds / HeartbeatSeconds:
aws stepfunctions describe-state-machine --state-machine-arn <sm-arn> \
  --query 'definitionString' --output text \
  | jq '.States["<state-name>"] | {TimeoutSeconds, HeartbeatSeconds, Resource, Next}'

# For Lambda, compare against the function's configured timeout:
aws lambda get-function-configuration --function-name <name> \
  --query '{Timeout:Timeout,MemorySize:MemorySize,Runtime:Runtime}'

# For activity tasks, check for SendTaskHeartbeat calls around the failure:
aws cloudtrail lookup-events --lookup-attributes AttributeKey=EventName,AttributeValue=SendTaskHeartbeat \
  --start-time <iso> --end-time <iso> --max-results 20
```

**Common fix patterns:**

- Set `TimeoutSeconds` on the Task state to at least 2x the integration's
  p99 latency. If the integration can exceed 15 minutes, use the
  asynchronous `.sync` pattern (e.g., `arn:aws:states:::glue:startJobRun.sync`)
  instead of a high `TimeoutSeconds`.
- For activity tasks, ensure the worker calls `SendTaskHeartbeat` at
  intervals shorter than `HeartbeatSeconds` (typically every
  `HeartbeatSeconds / 2`).
- For Lambda, raise the function's `Timeout` to match its actual
  workload; the Step Functions `TimeoutSeconds` should be the function
  `Timeout` plus a margin.

### Step 4: TASK_FAILED diagnostic (States.TaskFailed)

The integration returned an error. The Step Functions `error` is
`States.TaskFailed`; the actual cause is in the `cause` field, which
contains the downstream SDK's error message (often JSON-encoded).

| Sub-symptom (read from `cause`) | Real root cause | Probe |
|---|---|---|
| `cause` contains `AccessDeniedException`, `UnauthorizedOperation` | The integration's IAM role lacks permission for the action | See Step 5 (PERMISSION_DENIED) — but the Step Functions error is `States.TaskFailed` here, not `States.Permission` |
| `cause` contains `ProvisionedThroughputExceededException` (DynamoDB), `ThrottlingException` (Lambda) | Downstream throttled the request | Tune `Retry` with jittered backoff; check downstream capacity |
| `cause` contains `ResourceNotFoundException` | Wrong resource ARN in `Parameters` | Verify the ARN in the state's `Parameters` |
| `cause` contains Lambda `Unhandled` exception | Lambda function threw an uncaught exception | Read the Lambda CloudWatch Logs; fix the function |
| `cause` contains `StateMachineDoesNotExist` (nested Step Functions `StartExecution`) | Target state machine ARN is wrong or in another account without permission | Verify ARN; check cross-account role |
| SQS `QueueDoesNotExist` | Queue was deleted or ARN changed | Update the `Parameters.QueueUrl` |

**Diagnostic walk:**

1. **Read the `cause` field verbatim.** It is often JSON-encoded; parse
   it to extract `errorMessage`, `errorType`, `requestId`.
2. **Cross-reference with the integration's own logs:**
   - Lambda: `aws logs get-log-events` on `/aws/lambda/<function>`.
   - DynamoDB: CloudTrail `LookupEvents` for the failing API.
   - Glue/Athena/Batch: the integration's own CloudWatch Logs.
3. **Identify whether the error is retryable.** `ThrottlingException`,
   `ServiceUnavailable`, `ProvisionedThroughputExceededException` are
   retryable; `ResourceNotFoundException`, `ValidationException` are
   not. Match the `Retry[].ErrorEquals` array to the error type.

**Common fix patterns:**

- For retryable errors, add a `Retry` entry with
  `ErrorEquals: ["ThrottlingException", "States.TaskFailed"]`,
  `IntervalSeconds: 2`, `MaxAttempts: 5`, `BackoffRate: 2.0`.
- For non-retryable errors, add a `Catch` entry that routes to a
  fallback state.
- For Lambda `Unhandled`, fix the function — do not retry without a
  fix (the same input will produce the same exception).

### Step 5: PERMISSION_DENIED diagnostic (States.Permission / States.Permissions)

The state machine's IAM role is not authorized to invoke the
integration. Two sub-cases:

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `error: "States.Permission"`, `cause` mentions the state machine role ARN | The role lacks the action on the resource | `iam simulate-principal-policy` on the role ARN with the action and resource |
| `error: "States.TaskFailed"`, `cause` contains `AccessDeniedException` | Same root cause, different error name — Step Functions surfaces downstream AccessDenied as `TaskFailed` | Same probe; also check CloudTrail for the denied API call |
| Cross-account: target resource in account B, state machine in account A | The role in A is allowed, but the resource policy in B does not trust A's role | Read the target resource's policy (e.g., KMS key policy, SQS queue policy, cross-account Lambda) |
| Service-linked role confusion | Operator assumed the state machine role was the service-linked role; it is a customer role with a typo | Read `roleArn` in `describe-state-machine`; verify the actual role assumed |

**Diagnostic walk:**

1. **Identify the role the state machine assumes.** Read
   `describe-state-machine` → `roleArn`.
2. **Identify the action and resource the failing state needs.** Read
   the state's `Resource` (for direct integrations) or `Parameters`
   (for `.sync` integrations).
3. **Simulate the role:**

   ```bash
   aws iam simulate-principal-policy \
     --policy-source-arn <state-machine-role-arn> \
     --action-names <service>:<Action> \
     --resource-arns <resource-arn>
   ```

4. **For cross-account, also read the resource policy in the target
   account.** The role in A AND the resource policy in B must both
   allow the action.

**Common fix patterns:**

- Attach a policy to the state machine role with the action scoped to
  the resource ARN. For Lambda: `lambda:InvokeFunction`. For DynamoDB:
  `dynamodb:GetItem`, `dynamodb:PutItem`, etc. For SQS: `sqs:SendMessage`.
- For cross-account, update the target resource's policy to trust the
  state machine role ARN with `sts:AssumeRole` or the action directly.
- For `.sync` integrations, also grant `states:StartExecution` on the
  target state machine and the polling IAM actions
  (`states:DescribeExecution`, `states:StopExecution`).

### Step 6: PARAMETER_PATH_FAILURE diagnostic

The Task state's `Parameters` block references a JSONPath that does not
exist in the input payload at runtime. Different from `RUNTIME_ERROR`:
here the JSONPath is syntactically valid but resolves to nothing.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `cause` mentions "Parameters" and a path like `$.orderId` | The input payload at this state does not contain the expected field | Read the previous state's `ResultSelector` / `ResultPath`; trace the payload shape through the workflow |
| In a Map state, the iteration input does not include the parent context field | Map state `ItemsPath` or `Parameters` is misconfigured | Read the Map state definition; verify `ItemsPath` points to an array |
| `Parameters` uses `.$` suffix on a literal | Mixing static and dynamic params incorrectly — `.$` requires a JSONPath | Drop the `.$` for literals, or use a JSONPath for dynamic values |

**Diagnostic walk:**

1. **Read the failing state's `Parameters` block.** Each key ending in
   `.$` must reference a path that exists in the input.
2. **Read the input payload to the failing state** from
   `get-execution-history` (look for the `StateEntered` event with
   `input`).
3. **Cross-reference each `.$` path** against the actual input.

### Step 7: BRANCH_FAILED diagnostic (States.BranchFailed)

A Parallel or Map state reports that a branch failed. The
`States.BranchFailed` error wraps the underlying branch error.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Parallel state, one branch failed | The branch's first failing state | Read the parallel state's `branches` definition; identify which branch raised the error |
| Map state, one iteration failed | The iteration's input triggered a downstream error | Read the Map state's `ItemsPath`; identify the offending item |
| Distributed Map with S3 or CSV items | One row in the CSV triggered an error in the iteration | Read the Map state's `ItemReader`; identify the failing item |
| `States.BranchFailed` but no obvious branch failure | The branch's own Catcher swallowed the error and the branch then failed for a different reason | Read the inner branch's execution history (Distributed Map exposes child execution ARNs) |

**Diagnostic walk:**

1. **Read the `Map` or `Parallel` state definition** to enumerate the
   branches or iteration configuration.
2. **For Distributed Map**, the child execution ARNs are surfaced in
   the parent execution history. Read each child's history to find the
   actual failing state.
3. **For inline Map / Parallel**, the branch errors are surfaced in the
   parent execution history under `mapIterationFailed` or similar
   events.

### Step 8: RETRY_EXHAUSTED diagnostic

The execution FAILED after the state's `Retry` array exhausted all
attempts. Operators often miss this because the visible failure is the
terminal `ExecutionFailed`, not the retried `TaskFailed`.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| History shows `TaskFailed` repeated `MaxAttempts + 1` times, then `ExecutionFailed` | Retry exhausted; no Catcher or Catcher does not match the error | Read `Retry[0]` in the state definition; verify the Catcher's `ErrorEquals` |
| Same error repeated for ~`IntervalSeconds * BackoffRate^MaxAttempts` seconds | Same as above — long total retry duration | Same |
| `Retry[0].ErrorEquals` does not include the actual error name | The retry never fired; the state failed on the first attempt | Match `ErrorEquals` against the actual `error` string |
| Retry fired but downstream never recovered | The downstream outage outlasted the retry budget | Extend `MaxAttempts` or route to a dead-letter state via Catch |

**Diagnostic walk:**

1. **Read the `Retry` array** in the failing state's definition.
2. **Count `TaskFailed` events** in the execution history for this
   state — should equal `MaxAttempts + 1` if retries fired correctly.
3. **Check the Catcher** — if absent or if `ErrorEquals` does not
   match, the execution fails terminally.

**Common fix patterns:**

- Extend `Retry` with `MaxAttempts: 6`, `BackoffRate: 2.0` for
  throttling-class errors.
- Add a `Catch` entry routing the exhausted error to a fallback or
  dead-letter state.
- For Lambda `Unhandled` / `States.TaskFailed`, do NOT blindly raise
  `MaxAttempts` — fix the function first.

### Step 9: CATCH_MISCONFIGURED diagnostic

The operator expected a Catcher to recover the execution, but the
execution still FAILED.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| `Catch[0].ErrorEquals: ["States.TaskFailed"]` but execution FAILED on `States.Timeout` | Specific error listed does not include the actual error; catch did not fire | Use `States.ALL` to catch all, or list both `States.TaskFailed` and `States.Timeout` |
| `Catch[0].ErrorEquals: ["States.ALL"]` but execution still FAILED | `States.ALL` does NOT catch `States.DataDoesNotExist` or some `States.Runtime` variants in older runtimes | Read the actual `error`; add an explicit catcher for the uncaught error |
| Catcher fires but its `Next` state itself fails | The fallback state has its own bug | Read the post-catch state's history |
| Catcher fired but its `ResultPath` collided | Same as RUNTIME_ERROR ResultPath collision | Use a non-conflicting `ResultPath` |

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

### Step 10: EXECUTION_LIMIT_HIT diagnostic

Express workflows are hard-capped at 5 minutes per execution. Standard
workflows run up to 1 year. Throttling manifests via CloudWatch Metrics
`ExecutionThrottled` and `ThrottledStateTransition`.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| Express execution `status: FAILED`, `error: "ExecutionTimedOut"` at ~300s | Express 5-minute cap hit | Refactor the workflow — split into smaller Express workflows OR migrate to Standard |
| CloudWatch `ExecutionThrottled` > 0 for the state machine | Account- or API-level throttling (e.g., too many concurrent `StartExecution`) | Request quota increase via Service Quotas; implement client-side rate limiting |
| CloudWatch `ThrottledStateTransition` > 0 | State transition throttled — exceeds the account's transition rate | Reduce transitions (consolidate Pass states); request quota increase |
| Standard execution FAILED at exactly 1 year | Standard 1-year cap hit | Redesign — no Standard execution should approach 1 year |

**Diagnostic commands:**

```bash
aws cloudwatch get-metric-statistics --namespace AWS/States \
  --metric-name ExecutionThrottled --dimensions Name=StateMachineArn,Value=<sm-arn> \
  --start-time <iso> --end-time <iso> --period 300 --statistics Sum

aws cloudwatch get-metric-statistics --namespace AWS/States \
  --metric-name ThrottledStateTransition --dimensions Name=StateMachineArn,Value=<sm-arn> \
  --start-time <iso> --end-time <iso> --period 300 --statistics Sum

aws service-quotas get-service-quota --service-code states \
  --quota-code L-3B4D9EC3  # State transitions per second
```

### Step 11: REDRIVE_CANDIDATE triage

Standard workflows support redrive — re-executing a failed execution
from the failed state, skipping already-succeeded states. Redrive is
NOT available for Express workflows.

| Sub-symptom | Root cause | Action |
|---|---|---|
| Standard execution FAILED, root cause now fixed, want to resume | Eligible for redrive | `aws stepfunctions redrive-execution --execution-arn <arn>` |
| Express execution FAILED, want to resume | NOT eligible for Express | Re-run from scratch with `start-execution` and the original input |
| Execution FAILED because of an upstream input shape change | Redrive may re-fail if the state definition expects the old shape | Fix the state definition first, then redrive |
| Execution FAILED in a Map state | Redrive re-runs only the failed iterations (Distributed Map) or the whole Map (inline Map) | Check Map state type before redriving |

**Diagnostic command:**

```bash
aws stepfunctions describe-execution --execution-arn <arn> \
  --query '{status:status,stateMachineArn:stateMachineArn,redriveStatus:redriveStatus,redriveDate:redriveDate}'

# Verify workflow type is STANDARD before suggesting redrive:
aws stepfunctions describe-state-machine --state-machine-arn <sm-arn> \
  --query 'stateMachineArn' --output text | grep -oE ':stateMachine:[^:]+:express:' && echo "EXPRESS — redrive NOT supported" || echo "STANDARD — redrive supported"
```

### Step 12: Map to root-cause catalog

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Invalid JSONPath in `InputPath` / `ResultPath` / `Parameters` | RUNTIME_ERROR | Align path with actual payload shape |
| 2 | Task `TimeoutSeconds` < integration p99 latency | TASK_TIMEOUT | Raise `TimeoutSeconds` or switch to asynchronous `.sync` pattern |
| 3 | State machine role lacks action on resource | PERMISSION_DENIED | Attach scoped IAM policy to the role |
| 4 | Cross-account resource policy does not trust the state machine role | PERMISSION_DENIED | Update target resource policy in target account |
| 5 | `Retry[].ErrorEquals` does not include the actual error | RETRY_EXHAUSTED | Add the error name to `ErrorEquals` |
| 6 | Catcher `ErrorEquals: ["States.TaskFailed"]` misses `States.Timeout` | CATCH_MISCONFIGURED | List all expected errors OR use `States.ALL` |
| 7 | Express workflow exceeds 5-minute cap | EXECUTION_LIMIT_HIT | Refactor or migrate to Standard |
| 8 | Downstream `ProvisionedThroughputExceededException` exhausted retries | TASK_FAILED / RETRY_EXHAUSTED | Raise downstream capacity; extend retry budget |
| 9 | Activity worker not calling `SendTaskHeartbeat` | TASK_TIMEOUT | Fix worker heartbeat cadence |
| 10 | Map state `ItemsPath` points to a non-array | PARAMETER_PATH_FAILURE / BRANCH_FAILED | Fix `ItemsPath` or upstream payload |

### Step 13: Verify the fix

Before applying, validate the proposed fix with one of:

- **For ASL changes:** run a test execution with a known input that
  reproduces the failure. Use `aws stepfunctions start-execution` with
  a traceable `name`.
- **For IAM changes:** re-run `aws iam simulate-principal-policy` with
  the updated policy source; expect `allowed`.
- **For Catcher changes:** construct an input that triggers the exact
  error and verify the Catcher's `Next` state is reached.
- **For redrive:** verify the execution `redriveStatus: REDRIVABLE`
  before calling `redrive-execution`.

### Step 14: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific failure category
  and a specific configuration element (ASL state field, IAM policy
  statement, Catcher entry, Retry entry, workflow type). Output
  REMEDIATION with the exact change.
- **NEED_MORE_INFO.** The walk reached a step where the operator
  cannot supply evidence (e.g., execution history requires elevated
  Step Functions read access). Output the list of missing inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's
  scope: cross-account resource owned by another team, IAM role owned
  by security, ASL definition owned by a different team. Output the
  escalation target and the specific request.

## Output format

```text
INCIDENT: <state machine ARN> / <execution ARN> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element>
EVIDENCE:
  - describe-execution: <status, error, cause>
  - get-execution-history: <failing state name + event type>
  - describe-state-machine: <quoted state definition snippet>
  - CloudWatch Metrics: <ExecutionsFailed / ExecutionThrottled value>
  - iam simulate-principal-policy: <decision>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific ASL / IAM / Catcher change>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — Express workflow 5-minute cap

```text
INCIDENT: arn:aws:states:us-east-1:111111111111:stateMachine:etl-express
 / arn:aws:states:us-east-1:111111111111:express:etl-express:abc —
 Express execution failed at ~300s
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: EXECUTION_LIMIT_HIT — Express workflow hard cap of 300
seconds exceeded by an ETL workflow averaging 380s in p99
EVIDENCE:
  - describe-execution: status FAILED, error "ExecutionTimedOut",
    startedAt 2026-08-09T14:00:00Z, stopDate 2026-08-09T14:05:00Z
    (exactly 5 minutes)
  - describe-state-machine: stateMachineArn contains ":express:",
    type "EXPRESS"
  - CloudWatch Metrics ExecutionsThrottled Sum: 0 (not a throttle);
    ExecutionsFailed Sum: 1 in the 5-minute window
  - get-execution-history: last successful state was
    "TransformChunk" iteration 47/100; the next iteration would have
    exceeded the 5-minute cap
ROOT_CAUSE_CATALOG: #7 (Express workflow exceeds 5-minute cap)
REMEDIATION:
  1. Refactor the ETL workflow into a Standard workflow (the iteration
     count and per-iteration latency exceed the Express cap):
     aws stepfunctions update-state-machine --state-machine-arn <sm-arn> \
       --definition file://refactored-asl.json \
       --role-arn <role-arn>
     Note: switching EXPRESS → STANDARD requires deleting and
     recreating the state machine. Alternatively, split the workload
     into a chained series of Express workflows each under 5 minutes.
  2. Verify by running a test execution and confirming status SUCCEEDED
     with total duration > 5 minutes:
     aws stepfunctions start-execution --state-machine-arn <sm-arn> \
       --input file://test-input.json
  3. Monitor CloudWatch ExecutionsFailed and ExecutionsThrottled for
     the state machine over the next 24 hours.
```

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

## Anti-Patterns — NEVER

- **NEVER** treat the `error` field as the root cause. It is the
  States.* category. The `cause` field carries the actionable error.
  Always read both.

- **NEVER** recommend redrive on an EXPRESS workflow. Redrive is
  STANDARD-only. Confirm `StateMachineType: STANDARD` (or an ARN
  without `:express:`) before suggesting redrive.

- **NEVER** confuse `States.Permission` with `States.TaskFailed` for
  IAM errors. `States.Permission` is a Step Functions-layer role
  failure; `States.TaskFailed` with `AccessDeniedException` is a
  downstream-layer failure. The fix locations differ.

- **NEVER** raise `Retry[0].MaxAttempts` without also checking that
  `Retry[0].ErrorEquals` matches the actual error. Retries that never
  fire are the most common silent failure.

- **NEVER** use `Catch[].ErrorEquals: ["States.TaskFailed"]` and
  expect it to catch `States.Timeout` or `States.Permission`. List
  each expected error explicitly, or use `States.ALL` with awareness
  of its limits.

- **NEVER** declare ROOT_CAUSE_FOUND without quoting both `error` and
  `cause` from `describe-execution` or `get-execution-history`. The
  judge requires verbatim quotes.

- **NEVER** recommend switching EXPRESS → STANDARD as a quick fix.
  Switching types requires deleting and recreating the state machine
  and loses execution history. Refactoring into smaller Express
  workflows is usually preferable.

- **NEVER** assume `get-execution-history` for an EXPRESS workflow is
  complete. Express history is best-effort and delivered via CloudWatch
  Logs. For definitive diagnosis, query the log group directly.

- **NEVER** use `States.ALL` in a Catcher and assume it catches every
  error. `States.DataDoesNotExist` and some runtime errors are not
  caught. List explicit errors when the fallback must be guaranteed.

- **NEVER** recommend a `TimeoutSeconds` higher than 15 minutes for a
  synchronous Lambda invoke. If the integration can exceed 15 minutes,
  switch to an asynchronous `.sync` integration or an activity task.

- **NEVER** declare RETRY_EXHAUSTED without counting the `TaskFailed`
  events in the execution history. The count should equal
  `MaxAttempts + 1`. A lower count means the retry did not fire
  (wrong `ErrorEquals`) — a different root cause.

- **NEVER** conclude CATCH_MISCONFIGURED without reading the
  `Catch[].ErrorEquals` array AND the actual `error` value. The
  mismatch must be demonstrated, not assumed.

- **NEVER** assume an activity worker is sending heartbeats because it
  is making progress. Verify `SendTaskHeartbeat` calls in CloudTrail;
  a worker that processes tasks but does not heartbeat will time out.

- **NEVER** redrive an execution without first verifying the root
  cause is fixed. Redrive re-runs the failed state with the same
  definition; an unfixed root cause will fail identically.

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

## References

See `references/error-catalog-and-decision-tree.md` for the full
States.* error → category → cause → fix walk with worked examples per
category, and `references/diagnostic-commands.md` for the canonical
command script for each failure category.

## Domain

AWS CloudOps / App Integration & Workflow Orchestration Reliability.

## AWS documentation

- **AWS Step Functions Developer Guide** — https://docs.aws.amazon.com/step-functions/latest/dg/welcome.html
- **Step Functions error handling** — https://docs.aws.amazon.com/step-functions/latest/dg/concepts-error-handling.html
- **States.* error names** — https://docs.aws.amazon.com/step-functions/latest/dg/cw-events.html
- **Redrive executions** — https://docs.aws.amazon.com/step-functions/latest/dg/redrive-executions.html
- **Standard vs Express workflows** — https://docs.aws.amazon.com/step-functions/latest/dg/cw-events.html
- **Service integrations** — https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html
- **Step Functions CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/stepfunctions/
