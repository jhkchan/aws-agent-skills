# Error Handling — stepfunctions-execution-troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## NEED_MORE_INFO block when no execution ARN

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

## Step 2 — RUNTIME_ERROR fix patterns

**Common fix patterns:**

- Invalid JSONPath `$.body.items[*]` when payload has `$.items`: align
  the path to the actual payload shape.
- `ResultPath: "$.result"` collides with existing input field: use
  `ResultPath: "$.taskResult"` or `ResultPath: null`.
- Used a JSONPath filter `?(@.active)` on an integration that does not
  support filters (e.g., Direct Lambda Invoke): remove the filter and
  post-process in a Pass state.

## Step 3 — TASK_TIMEOUT fix patterns

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

## Step 4 — TASK_FAILED fix patterns

**Common fix patterns:**

- For retryable errors, add a `Retry` entry with
  `ErrorEquals: ["ThrottlingException", "States.TaskFailed"]`,
  `IntervalSeconds: 2`, `MaxAttempts: 5`, `BackoffRate: 2.0`.
- For non-retryable errors, add a `Catch` entry that routes to a
  fallback state.
- For Lambda `Unhandled`, fix the function — do not retry without a
  fix (the same input will produce the same exception).

## Step 5 — PERMISSION_DENIED fix patterns

**Common fix patterns:**

- Attach a policy to the state machine role with the action scoped to
  the resource ARN. For Lambda: `lambda:InvokeFunction`. For DynamoDB:
  `dynamodb:GetItem`, `dynamodb:PutItem`, etc. For SQS: `sqs:SendMessage`.
- For cross-account, update the target resource's policy to trust the
  state machine role ARN with `sts:AssumeRole` or the action directly.
- For `.sync` integrations, also grant `states:StartExecution` on the
  target state machine and the polling IAM actions
  (`states:DescribeExecution`, `states:StopExecution`).

## Step 8 — RETRY_EXHAUSTED fix patterns

**Common fix patterns:**

- Extend `Retry` with `MaxAttempts: 6`, `BackoffRate: 2.0` for
  throttling-class errors.
- Add a `Catch` entry routing the exhausted error to a fallback or
  dead-letter state.
- For Lambda `Unhandled` / `States.TaskFailed`, do NOT blindly raise
  `MaxAttempts` — fix the function first.

## Fix verification (Step 13)

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
