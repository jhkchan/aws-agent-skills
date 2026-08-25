# Step Functions Express Workflows Deployer - advanced patterns (load on demand)

> Moved verbatim from SKILL.md during progressive-disclosure restructure. Load on demand.

## Reasoning framework (why the Express decision matters)

Step Functions offers two workflow types. The choice is a cost,
durability, and semantics decision — not a syntax decision (the
ASL is identical for both).

1. **Standard bills per state transition; Express bills per
   invocation + duration + memory.** Standard is $0.025 per 1,000
   state transitions; Express is $1.00 per million invocations plus
   $0.025 / GB-hour. A 10-state workflow at 10M runs/day costs
   ~$2,500/day on Standard vs ~$10/day on Express (short duration).

2. **Standard is exactly-once; Express is at-least-once.** Express
   async executions may retry steps on infrastructure events; the
   same input can produce two invocations of a side-effecting
   integration. Write paths MUST be idempotent.

3. **Standard supports runs up to 1 year; Express caps at 5
   minutes.** The 5-minute cap is enforced per execution, not per
   state — a 4-min Lambda plus a 2-min downstream fails at minute 5.

4. **`.waitForTaskToken` is NOT supported on Express.** Only `.sync`
   is Express-compatible among the callback-style integrations.
   Operators migrating from Standard discover this only at
   create-time.

## Expert heuristic: the waitForTaskToken Express block

The most dangerous migration trap: a Standard workflow using
`.waitForTaskToken` (the callback pattern, e.g., for human
approval, external system callbacks, long-running ECS tasks) is
silently converted to Express. The `create-state-machine` API call
rejects the ASL with a definition-validation error — but the error
references the line number of the Resource ARN, not the
incompatibility, and operators re-apply believing the issue is IAM
or formatting.

```text
Operator sees:                What it actually means:
"Invalid State Machine         .waitForTaskToken is NOT supported
 Definition: ...Resource       on EXPRESS workflows. The Resource
 ...".                         ARN suffix :waitForTaskToken is the
                               cause; convert to .sync or use
                               STANDARD workflow type.
```

The `.waitForTaskToken` pattern is fundamentally incompatible with
the 5-minute Express cap because the task token can be returned
days later. Two remedies: (1) use `.sync` for supported run-job
integrations, or (2) use a Standard workflow for the callback
portion and an Express workflow for the high-volume portion, with
`StartExecution` between them.

## Expert heuristic: at-least-once idempotency

Express executions are at-least-once. The infrastructure can
restart an execution on rare events (deployment, failover); the
same input can produce two invocations of a side-effecting
integration. For read-only integrations this is invisible; for
side-effecting integrations it is a data-corruption hazard.

```text
Operator assumes:              What actually happens:
Lambda writes a charge          Lambda invoked twice with same input
 to the card → one charge       → two charges, no error signal
```

The remedy is an idempotency key at the workflow input, persisted
BEFORE the side-effecting state:

```json
{
  "ChargeCard": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:charge-card",
    "Parameters": {
      "IdempotencyKey.$": "$$.Execution.Id",
      "Amount.$": "$.amount"
    },
    "Retry": [{ "ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 3 }]
  }
}
```

The Lambda handler checks `IdempotencyKey` against a DynamoDB table
before charging; duplicate retries are no-ops. Every side-effecting
Express integration MUST have this pattern.

## Expert heuristic: sync API Gateway timeout misalignment

A sync Express workflow (`start-sync-execution`) invoked from API
Gateway returns the workflow result synchronously. API Gateway caps
the integration at 29 seconds; Express sync can run up to 5 minutes.
Misalignment produces a pattern that works in dev (2-second runs)
and fails in production (a cold Lambda pushes it past 30 seconds):
- API Gateway returns 504 to the client at second 29.
- Express keeps running to completion (up to 5 min) and writes the
  result to logs.
- The client retries; if the integration is non-idempotent, this is
  a double-charge.

Remedy: set the API Gateway integration timeout to 29000 ms,
monitor p99 execution duration, and alarm on `ExecutionsTimedOut`.
If p99 exceeds 25s, move to async (return a 202 with the execution
ARN).

## Step 1 cost estimate (rough)

Cost estimate (rough): Standard = $0.025 / 1,000 state transitions.
Express = $1.00 / 1M invocations + $0.025 / GB-hour. A 5-state
workflow at 1M runs/day = ~$125/day on Standard vs ~$1/day on
Express. Always compute the break-even for your state count.

## Recent AWS features

- **Express + Distributed Map (GA)**: Distributed Map is supported
  on Express, but the 5-min cap limits total iteration time. Use
  `MaxConcurrency` 1000 with short per-item Lambdas; monitor
  `MapRunItemCount` / `MapRunFailedCount`.
- **Express + AWS SDK integrations**: direct API calls (e.g.,
  DynamoDB `UpdateItem`, SNS `Publish`) without a Lambda wrapper.
  The IAM role must allow the underlying SDK action.
- **Express + Typed integrations**: Resource ARNs follow
  `arn:aws:states:::service:action` (RequestResponse) or
  `arn:aws:states:::service:action.sync` (run-job-and-wait).
- **CloudWatch Logs granularity**: levels ALL / ERROR / FATAL / OFF
  control which execution events are logged;
  `includeExecutionData` controls input/output capture. Both set
  in `loggingConfiguration`.
- **X-Ray tracing on Express**: enable via
  `tracingConfiguration.enabled=true`; the execution role needs
  `xray:PutTraceSegments` / `PutTelemetryRecords`.
- **Step Functions IAM condition keys**: `states:StateMachineArn`
  scopes who can start executions on which state machines; useful
  for cross-account Express.

