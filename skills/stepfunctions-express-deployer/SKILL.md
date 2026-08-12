---
name: stepfunctions-express-deployer
description: >-
  Provisions Step Functions Express Workflows with production
  defaults: Express-vs-Standard decision (5-min cap, at-least-once
  vs exactly-once, per-invocation vs per-transition pricing), sync
  (RequestResponse) vs async invocation, CloudWatch Logs
  configuration (ALL / ERROR / FATAL / OFF levels and INCLUDE_DATA
  / EXCLUDE_DATA), IAM least-privilege execution role, EventBridge
  scheduling, Distributed Map and Inline Map fan-out,
  Express-compatible service integrations (.sync, AWS SDK direct
  calls), idempotency for at-least-once delivery, observability
  (metrics, X-Ray, CloudWatch alarms). Emits READY_TO_DEPLOY /
  PREREQUISITES_MISSING with copy-pasteable stepfunctions / logs /
  events / iam CLI. Use when provisioning an Express workflow,
  migrating high-volume Standard workloads to Express, configuring
  sync invocation from API Gateway, or hardening logging. Triggers:
  Express workflow, create state machine EXPRESS, sync express,
  async express, EventBridge Step Functions, Step Functions
  logging, Distributed Map Express.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Live provisioning uses AWS CLI v2 with
  stepfunctions (create-state-machine, update-state-machine,
  describe-state-machine, start-sync-execution, start-execution,
  validate-state-machine-definition), logs (create-log-group,
  put-retention-policy), events (put-rule, put-targets), iam
  (create-role, attach-role-policy, put-role-policy), and
  cloudformation / terraform aws_sfn_state_machine equivalents.
keywords:
  - aws
  - step-functions
  - stepfunctions
  - express-workflow
  - state-machine
  - asl
  - amazon-states-language
  - sync-execution
  - requestresponse
  - async-execution
  - cloudwatch-logs
  - include-data
  - exclude-data
  - eventbridge
  - distributed-map
  - inline-map
  - sync-integration
  - waitfortasktoken
  - idempotency
  - at-least-once
  - iam-execution-role
  - x-ray
  - cloudops
  - deploy
tags:
  - aws
  - step-functions
  - express-workflow
  - state-machine
  - sync-execution
  - logging
  - eventbridge
  - deploy
  - app-integration
dependencies:
  - aws-orchestrator
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
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Provisioning a new Step Functions Express Workflow, deciding
    between Express and Standard (5-min cap, at-least-once semantics,
    per-invocation pricing), configuring sync (RequestResponse) vs
    async invocation, attaching a CloudWatch Logs log group with the
    correct level (ALL / ERROR / FATAL / OFF) and INCLUDE_DATA /
    EXCLUDE_DATA exposure, scheduling recurring Express executions
    via EventBridge, using Distributed Map or Inline Map with
    Express, using .sync service integrations (Glue, Batch, ECS,
    SageMaker), or hardening idempotency for at-least-once delivery.
    Do NOT invoke for Standard workflows that run >5 minutes or use
    .waitForTaskToken (use stepfunctions-statemachine-deployer), or
    for troubleshooting execution failures (use
    stepfunctions-execution-troubleshooter).
  activation_triggers:
    - "Express workflow"
    - "create Express state machine"
    - "Step Functions EXPRESS"
    - "sync express execution"
    - "start-sync-execution"
    - "async express"
    - "Express workflow logging"
    - "Step Functions CloudWatch Logs"
    - "INCLUDE_DATA"
    - "EXCLUDE_DATA"
    - "EventBridge Step Functions"
    - "Distributed Map Express"
    - "Standard-to-Express migration"
    - "Express idempotency"
  invocation_schema: >-
    Input: either (a) a workflow name + ASL definition (or
    requirements to derive one) + sync/async invocation mode, or
    (b) a Standard-to-Express migration spec (existing state machine
    ARN + compatibility check), or (c) an EventBridge-scheduled
    Express spec (schedule expression + execution role). Output:
    deterministic EXPRESS_WORKFLOW / VERDICT / CHECKLIST /
    VERIFICATION_COMMANDS block per the STRICT output contract,
    where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.
---

# Step Functions Express Workflows Deployer

## What this skill does

Provisions Step Functions Express Workflows and surrounding
primitives (CloudWatch Logs with correct level and data-exposure,
IAM least-privilege execution role, EventBridge scheduling,
Distributed Map configuration, idempotency guard for at-least-once
delivery) with production defaults. The skill walks a 9-step
procedure, surfaces the silent-failure modes unique to Express
(most dangerous: `.waitForTaskToken` is rejected at create-time,
but operators migrating from Standard discover this only on deploy;
logging is NOT enabled by default, so async Express executions are
invisible after the 5-minute history window; the at-least-once
delivery model means non-idempotent Lambda handlers can double-
execute on retries). The single most common incident this skill
prevents: an operator migrates a high-volume Standard workflow to
Express for cost savings, the migration drops CloudWatch Logs, and
the first failed execution is invisible — no alarm, no log, and the
5-minute execution history has already rolled over.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (9 steps), verdict thresholds | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Reasoning framework** | Why Express is a cost + semantics decision | Choosing Express vs Standard |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "logs are empty" |
| **Expert heuristic** | waitForTaskToken block; at-least-once idempotency; sync API Gateway timeouts | Pre-empt incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **9-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent silent exposure / data-plane bugs | Review before deploy |
| **STRICT output contract** | Required EXPRESS_WORKFLOW / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | Express + Distributed Map, AWS SDK direct calls | Stay current |

## Quick reference — provisioning summary (9 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Confirm Express-vs-Standard decision (5-min cap, at-least-once, cost model) | — | wrong type = 100x cost or 5-min timeout |
| 2 | Verify workflow duration fits in the 5-minute Express cap | Yes | sync API Gateway returns 500; async retried mid-flight |
| 3 | Verify all service integrations are Express-compatible (NO `.waitForTaskToken`) | Yes | create-state-machine API silently rejects the definition |
| 4 | Define the ASL with Express-compatible patterns (Distributed Map, .sync, AWS SDK) | Yes | — |
| 5 | Create the IAM execution role with least-privilege | Yes | over-broad `states:*` on `*` |
| 6 | Configure logging (CloudWatch Logs + level + INCLUDE_DATA/EXCLUDE_DATA) | Yes | async executions invisible after 5-min history |
| 7 | Choose sync (RequestResponse) vs async invocation mode | Yes | sync API Gateway timeout misalignment |
| 8 | Configure EventBridge scheduling + observability (X-Ray, CloudWatch alarms) | Yes | silent failures with no alarm |
| 9 | Verify every configuration item against actual state + emit checklist | — | silent no-ops |

**Critical ordering constraints:** Express-vs-Standard decision
first (every downstream choice depends on the type); duration
budget before ASL definition (a workflow that exceeds 5 minutes
cannot be Express); integration compatibility before the IAM role
(`.waitForTaskToken` rejected at create-time even with a valid
role); logging configuration before the first execution (without
logging, async Express executions are invisible after the 5-minute
history rolls over); sync-vs-async choice before the caller
integration (API Gateway sync requires timeout alignment to ≤ 29s
to avoid 504). Rationale and the silent-failure table are below.

## Activation keywords

Express workflow, create Express state machine, Step Functions
EXPRESS, sync express execution, start-sync-execution, async
express, Express workflow logging, Step Functions CloudWatch Logs,
INCLUDE_DATA, EXCLUDE_DATA, FATAL / ERROR / ALL levels, EventBridge
Step Functions target, Distributed Map Express, Inline Map Express,
Standard-to-Express migration, at-least-once Step Functions, Express
idempotency, Express sync API Gateway, .sync integration Express,
AWS SDK integration, X-Ray tracing Step Functions.

## Invocation contract (hard requirement)

When this skill is invoked with an Express Workflow provisioning
request, the agent MUST respond with the checklist defined in
§"STRICT output contract" using the literal all-caps labels
`EXPRESS_WORKFLOW:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

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

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing) | Enables downstream |
|---|---|---|---|
| Express state machine | unique name; valid ASL | `.waitForTaskToken` in ASL → API rejects with definition-validation error; operators misread as IAM error and keep re-applying | — |
| CloudWatch Logs log group | log group exists in same account + region | **log group ARN omitted at create-time → executions do not log; 5-min history rolls over and failure is invisible** | observability |
| Log level (ALL / ERROR / FATAL / OFF) | log group attached | **level set to OFF or FATAL only → execution-level errors invisible; operator sees empty log group** | debuggability |
| INCLUDE_DATA / EXCLUDE_DATA | log group attached | **EXCLUDE_DATA on a workflow that takes PII inputs → traces show only metadata, blocking RCA** (or inverse: INCLUDE_DATA on PII → compliance violation) | input/output visibility |
| IAM execution role | trust policy allows `states.<region>.amazonaws.com` | trust policy missing service principal → `AccessDenied` on first execution; not surfaced at create-time | service integrations |
| Sync execution (start-sync-execution) | state machine type EXPRESS | calling start-sync-execution on a Standard state machine → error; but a caller using start-execution on Express works (just async) | API Gateway / direct sync |
| EventBridge target | execution role for EventBridge to assume | **target without role → rule fires, no execution; EventBridge shows Invocations = 1, Step Functions shows Executions = 0** | scheduled recurring runs |
| Distributed Map | state machine type EXPRESS or STANDARD; IAM allows read on ItemReader source | **Map state on Express with > 10,000-item fan-out hits 5-min cap → workflow fails mid-iteration with no progress signal** | large-scale fan-out |
| .sync integration | supported service (Glue, Batch, ECS, SageMaker) | unsupported service in Resource ARN → API rejects; misread as syntax error | run-job-and-wait |
| AWS SDK integration | IAM allows the underlying SDK action | **IAM allows `lambda:InvokeFunction` but the SDK integration calls `lambda:UpdateFunctionCode` → runtime AccessDenied** | direct API calls (no Lambda) |

**The four silent-failure rows are the ones a baseline model
misses.** Missing logging, wrong log level, EXCLUDE_DATA on
debugging inputs, and missing EventBridge target role all return
success or wrong-shaped errors. Only Step 9 verification catches
the gap.

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

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Workflow duration fits in 5 min | Express caps at 5 min; sync API Gateway caps at 29s | estimate from longest task * longest retry; `validate-state-machine-definition` does NOT check this |
| Workflow does NOT use `.waitForTaskToken` | Express rejects it at create-time | grep ASL for `:waitForTaskToken` |
| IAM execution role trust policy | service principal must be `states.<region>.amazonaws.com` | `aws iam get-role --role-name <ROLE>` |
| CloudWatch Logs log group exists (recommended) | Express execution history rolls over after 5 min | `aws logs describe-log-groups --log-group-name-prefix /aws/states/<NAME>` |
| Caller can assume the role (cross-account) | Cross-account callers need their own permission | caller identity policy check |
| EventBridge rule exists (scheduled) | Scheduled Express requires an EventBridge rule + target role | `aws events describe-rule --name <RULE>` |
| AWS region supports Express | Express is available in all commercial regions | `aws stepfunctions list-state-machines --region <REGION>` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 9-step provisioning procedure

### Step 1 — Confirm Express-vs-Standard decision

Verify Express is the correct type. Use this decision table:

| If your workload… | Use |
|---|---|
| Runs > 5 minutes per execution | STANDARD |
| Uses `.waitForTaskToken` (callbacks) | STANDARD |
| Needs exactly-once semantics and idempotency is infeasible | STANDARD |
| Runs < 5 minutes, high-volume (>1k/day), idempotent or read-mostly | EXPRESS |
| Triggered by EventBridge at high frequency | EXPRESS |
| Fronted by API Gateway returning the workflow result synchronously | EXPRESS (sync) |
| Async messaging with very high throughput | EXPRESS (async) |

Cost estimate (rough): Standard = $0.025 / 1,000 state transitions.
Express = $1.00 / 1M invocations + $0.025 / GB-hour. A 5-state
workflow at 1M runs/day = ~$125/day on Standard vs ~$1/day on
Express. Always compute the break-even for your state count.

### Step 2 — Verify workflow duration fits in the 5-minute cap

Sum the worst-case duration of every Task state multiplied by its
Retry `MaxAttempts`. If the workflow includes a Distributed Map,
sum the longest batch. If the result can exceed 5 minutes, the
workflow is incompatible with Express — go back to Step 1.

```bash
# Validate the ASL definition (does NOT check duration)
aws stepfunctions validate-state-machine-definition \
  --definition file://definition.json --type EXPRESS
```

**Common mistake:** assuming `validate-state-machine-definition`
checks the 5-min cap. It does NOT — only syntax. The cap is
enforced at runtime; executions fail with `States.Timeout`.

### Step 3 — Verify all service integrations are Express-compatible

```bash
# Reject if any match
grep -E ':waitForTaskToken' definition.json && echo "INCOMPATIBLE"
```

Express-compatible integration patterns:
- RequestResponse (default): invoke and return immediately
- `.sync`: invoke and wait for completion (Glue, Batch, ECS, SageMaker, Comprehend)
- AWS SDK integrations: direct API calls without Lambda

Express-INCOMPATIBLE patterns:
- `.waitForTaskToken`: callback pattern (unbounded wait)

**Common mistake:** converting a Standard workflow that uses
`.waitForTaskToken` for the human-approval step. Replace with a
DynamoDB polling loop (`.sync` on a Lambda that polls approval
status) or split into two workflows.

### Step 4 — Define the ASL with Express-compatible patterns

Write the ASL definition. For fan-out, use Inline Map (≤40
concurrent) or Distributed Map (≤10,000 concurrent with S3 /
DynamoDB ItemReader). For job-style integrations, use `.sync`.

```json
{
  "StartAt": "FanOut",
  "States": {
    "FanOut": {
      "Type": "Map",
      "ItemProcessor": {
        "ProcessorConfig": { "Mode": "DISTRIBUTED" },
        "StartAt": "ProcessItem",
        "States": {
          "ProcessItem": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:process-item",
            "End": true
          }
        }
      },
      "ItemReader": {
        "Resource": "arn:aws:states:::s3:getObject",
        "Parameters": { "Bucket": "my-bucket", "Key": "input.json" }
      },
      "MaxConcurrency": 1000,
      "End": true
    }
  }
}
```

**Common mistake:** Inline Map on Express with > 40 concurrent
iterations. Inline Map caps at 40 concurrent; the rest queue. For
large fan-out on Express, use Distributed Map — but verify the
total iteration time still fits in the 5-minute cap.

### Step 5 — Create the IAM execution role with least-privilege

```bash
cat > trust-policy.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "states.<REGION>.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role --role-name <ROLE_NAME> \
  --assume-role-policy-document file://trust-policy.json
```

The inline policy MUST scope each integration to specific ARNs:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Effect": "Allow", "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:<REGION>:<ACCOUNT>:function:process-item" },
    { "Effect": "Allow", "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-bucket/input.json" }
  ]
}
```

**Common mistake:** granting `lambda:InvokeFunction` on `*` and
forgetting an AWS SDK integration calls a different action
(e.g., `lambda:UpdateFunctionCode`). Scope to the exact ARNs.

### Step 6 — Configure logging (CloudWatch Logs)

Logging is NOT enabled by default. Without it, async Express
executions are invisible after the 5-minute execution-history
rollover.

```bash
# Create the log group with retention
aws logs create-log-group --log-group-name /aws/states/<NAME>
aws logs put-retention-policy --log-group-name /aws/states/<NAME> \
  --retention-in-days 30
```

Attach the log group at create-time:

```bash
aws stepfunctions create-state-machine \
  --name <NAME> --definition file://definition.json \
  --role-arn arn:aws:iam::<ACCOUNT>:role/<ROLE_NAME> \
  --type EXPRESS \
  --logging-configuration \
    level=ALL,includeExecutionData=true,\
    destinations='[{CloudWatchLogsLogGroup={LogGroupArn=arn:aws:logs:<REGION>:<ACCOUNT>:log-group:/aws/states/<NAME>:*}}]'
```

The level choices:
- `ALL`: log Start, StateEntered, StateExited, End. Highest volume; full RCA.
- `ERROR`: log only failures and state errors. Lower cost; cannot debug successful-path issues.
- `FATAL`: log only workflow-level fatal errors. Near-useless for debugging.
- `OFF`: no logging. NEVER for async Express — failures are invisible.

`includeExecutionData=true` records input/output at each transition. Without it, logs show only metadata.

**Common mistake:** setting `includeExecutionData=false` to save
cost on a PII workflow, then being unable to RCA a production
failure. Redact PII at workflow input; do NOT disable execution
data wholesale.

### Step 7 — Choose sync (RequestResponse) vs async invocation

| Mode | Caller | Use when |
|---|---|---|
| Sync | API Gateway, direct start-sync-execution | Caller needs result synchronously, workflow < 29s p99 |
| Async | EventBridge, S3, SQS, start-execution | High throughput, fire-and-forget, up to 5 min |

```bash
aws stepfunctions start-sync-execution \
  --state-machine-arn arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME> \
  --input '{"amount": 100}'
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME> \
  --input '{"amount": 100}'
```

**Common mistake:** fronting an Express workflow with API Gateway
sync and not aligning timeouts. API Gateway times out at 29s;
Express sync can run to 5 min. Set the API Gateway integration
timeout to 29000 ms and alarm on p99 execution duration > 25s.

### Step 8 — Configure EventBridge scheduling + observability

#### 8a. EventBridge rule for scheduled Express

```bash
# Schedule: every 5 minutes
aws events put-rule --name <RULE_NAME> \
  --schedule-expression "rate(5 minutes)"

# Target: the Express state machine
aws events put-targets --rule <RULE_NAME> \
  --targets 'Id=1,Arn=arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME>,RoleArn=arn:aws:iam::<ACCOUNT>:role/<EVENTBRIDGE_ROLE>'
```

The EventBridge target role MUST trust `events.amazonaws.com` and
allow `states:StartExecution` on the state machine ARN. Without
the target role, the rule fires but no execution starts —
EventBridge shows `Invocations: 1`, Step Functions shows
`Executions: 0`, with no error.

#### 8b. CloudWatch alarms

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "<NAME>-failed" \
  --metric-name "ExecutionsFailed" \
  --namespace "AWS/States" \
  --dimensions Name=StateMachineArn,Value=arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME> \
  --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold \
  --period 60 --evaluation-periods 1 --treat-missing-data notBreaching
```

Always alarm on `ExecutionsFailed` for async Express — there is no
caller to surface the error.

#### 8c. X-Ray tracing

```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME> \
  --tracing-configuration enabled=true
```

X-Ray tracing requires the execution role to have
`xray:PutTraceSegments` and `xray:PutTelemetryRecords`.

### Step 9 — Verification

Run every verification command and confirm each output matches the
expected state.

```bash
aws stepfunctions describe-state-machine \
  --state-machine-arn arn:aws:states:<REGION>:<ACCOUNT>:stateMachine:<NAME>
# Expected: type EXPRESS, loggingConfiguration.level=ALL, includeExecutionData=true
aws logs describe-log-groups --log-group-name-prefix /aws/states/<NAME>
# Expected: retentionInDays > 0
aws events describe-rule --name <RULE_NAME>  # if scheduled; State ENABLED
aws cloudwatch describe-alarms --alarm-names <NAME>-failed  # StateValue OK
```

## NEVER do these things

These anti-patterns cause silent exposure, data-plane bugs, or
compliance violations. Each is observed in real production incidents
— the "why it's wrong" line is the post-mortem finding.

1. **NEVER provision an Express workflow with `.waitForTaskToken` in
   the ASL.** Why it's wrong: Express rejects the integration at
   create-time (5-min cap is incompatible with unbounded callback
   wait). The error references the line number, not the
   incompatibility — operators loop on re-applying. Replace with
   `.sync` for supported run-job integrations or split into a
   Standard + Express pair.

2. **NEVER deploy async Express without CloudWatch Logs enabled and
   an `ExecutionsFailed` alarm.** Why it's wrong: async Express has
   no caller to surface errors. The 5-min execution-history window
   rolls over quickly; without persistent logging, failures are
   invisible. Without an alarm, the failure may go undetected for
   days. ALWAYS attach a log group with `level >= ERROR` and alarm
   on `ExecutionsFailed`.

3. **NEVER assume Express executions are exactly-once.** Why it's
   wrong: Express is at-least-once. The infrastructure can restart
   an execution on internal events; the same input can produce two
   invocations of a side-effecting integration. Every write-path
   integration MUST be idempotent via a key persisted BEFORE the
   side effect.

4. **NEVER front a sync Express workflow with API Gateway without
   aligning the timeout.** Why it's wrong: API Gateway caps at 29s;
   Express sync can run to 5 min. When p99 exceeds 29s, API Gateway
   returns 504 while Express keeps running — the client retries,
   producing a second execution that may double-charge if the
   integration is non-idempotent. Set the API Gateway integration
   timeout to 29000 ms and alarm on p99 duration > 25s.

5. **NEVER set log level to OFF or FATAL on an Express workflow.**
   Why it's wrong: OFF and FATAL produce near-empty logs, blocking
   RCA. Use `ALL` for development and non-PII workloads; `ERROR` for
   high-volume production. Always set `includeExecutionData=true`
   unless the workflow processes regulated PII — and in that case,
   redact the PII at the input, not by disabling execution data.

## Output format

```
EXPRESS_WORKFLOW: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Express-vs-Standard decision: EXPRESS (duration < 5 min, at-least-once acceptable)
  [✓|✗] Duration budget: p99 < 5 min (sync: p99 < 29s)
  [✓|✗] No .waitForTaskToken in ASL: verified
  [✓|✗] ASL definition validated: Distributed Map / .sync / AWS SDK as applicable
  [✓|✗] IAM execution role: least-privilege, service principal states.<region>.amazonaws.com
  [✓|✗] Logging: log-group /aws/states/<NAME>, level ALL|ERROR, includeExecutionData=true
  [✓|✗] Invocation mode: sync | async (sync caller timeout aligned)
  [✓|✗] EventBridge schedule + CloudWatch alarm: configured
  [✓|✗] Idempotency: side-effecting integrations have idempotency key
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
checklist that looks complete but contains a silent misconfiguration.
Self-check EVERY emitted block against these rules before returning.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT preface with prose, headings, or disclaimers.

```text
EXPRESS_WORKFLOW: <name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Express-vs-Standard decision: EXPRESS (duration < 5 min, at-least-once acceptable)
  [✓|✗] Duration budget: p99 < 5 min (sync: p99 < 29s)
  [✓|✗] No .waitForTaskToken in ASL: verified
  [✓|✗] ASL definition validated: Distributed Map / .sync / AWS SDK as applicable
  [✓|✗] IAM execution role: least-privilege, service principal states.<region>.amazonaws.com
  [✓|✗] Logging: log-group /aws/states/<NAME>, level ALL|ERROR, includeExecutionData=true
  [✓|✗] Invocation mode: sync | async (sync caller timeout aligned)
  [✓|✗] EventBridge schedule + CloudWatch alarm: configured
  [✓|✗] Idempotency: side-effecting integrations have idempotency key
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### Decision tree: Express vs Standard

```text
Express vs Standard — START
  │
  Q1: Does any single execution need to run > 5 minutes?
  ├── YES → STANDARD (Express hard-caps at 5 min per execution)
  └── NO  → Q2
  │
  Q2: Does the ASL use .waitForTaskToken (callback / human-approval)?
  ├── YES → STANDARD (Express rejects .waitForTaskToken at create-time)
  └── NO  → Q3
  │
  Q3: Is exactly-once required AND idempotency is infeasible?
  ├── YES → STANDARD (Express is at-least-once; retries can double-execute)
  └── NO  → Q4
  │
  Q4: Is the workload high-volume (> 1,000 executions/day)?
  ├── NO  → Either works; prefer STANDARD unless cost is a concern
  └── YES → Q5
  │
  Q5: Can all side-effecting integrations be made idempotent?
  ├── NO  → STANDARD (at-least-once risks duplicate writes / charges)
  └── YES → EXPRESS
             Cost model:
               Standard: $25.00 / 1M state transitions
               Express:  $1.00 / 1M invocations + $0.025 / GB-hour
               10-state workflow, 1M runs/day:
                 Standard = $250/day  |  Express = $1/day
               10-state workflow, 10M runs/day:
                 Standard = $2,500/day  |  Express = $10/day
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 9
   checklist items.** Every item MUST appear with a status marker:
   `[✓]`, `[✗]`, or `[OPTIONAL]` (e.g., EventBridge schedule when
   the workflow is not scheduled). Omitting a row implies it was
   not evaluated.

2. **NEVER mark the ASL as `[✓]` without confirming the definition
   contains NO `.waitForTaskToken` Resource ARN suffix.** The
   integration is silently rejected by Express at create-time; the
   verification MUST include a `grep` or equivalent.

3. **NEVER mark Logging as `[✓]` without citing the specific log
   group name, level (ALL / ERROR), and `includeExecutionData`
   value.** A bare `[✓] Logging: configured` is non-compliant —
   level and data-exposure flag are load-bearing. OFF and FATAL are
   non-compliant for an Express workflow.

4. **NEVER mark sync invocation as `[✓]` without confirming the
   caller's timeout is ≤ 29s (API Gateway) or equivalent for the
   direct caller.** Misaligned timeouts cause silent 504s while
   Express keeps running, producing double-executions on retry.

5. **NEVER mark Idempotency as `[✓]` for a workflow with side-
   effecting integrations unless each such integration has an
   idempotency key persisted BEFORE the side effect.** The checklist
   MUST cite the key source (e.g.,
   `IdempotencyKey.$: "$$.Execution.Id"`).

6. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason:
   `[✗] ASL uses .waitForTaskToken at line 42 — replace with .sync
   or migrate to Standard`. A bare `[✗]` is non-compliant.

7. **NEVER omit the cost-model comparison from the Express-vs-
   Standard checklist row.** The row MUST cite the cost delta
   (e.g., "Express $1/M invocations vs Standard $25/M transitions")
   so the operator can sanity-check the type choice. A bare
   "EXPRESS" without cost rationale is non-compliant.

### Perfect example output — READY_TO_DEPLOY

Scenario: High-volume event-processing Express workflow. JSON event
batches land in S3; a Distributed Map fans them out to a Lambda for
per-event processing. Async, triggered by EventBridge every 5 minutes.
At 2M executions/day with a 5-state workflow: Standard would cost
~$250/day ($25/M x 10M transitions); Express costs ~$2/day ($1/M
x 2M invocations). p99 execution duration = 12s.

```text
EXPRESS_WORKFLOW: event-processor-express
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Express-vs-Standard decision: EXPRESS (p99 12s, idempotent;
        cost: Express $1/M invocations vs Standard $25/M transitions;
        2M runs/day x 5 states = 10M transitions -> Standard $250/day vs Express $2/day)
  [✓] Duration budget: p99 12s < 5 min (async; no sync API Gateway alignment needed)
  [✓] No .waitForTaskToken in ASL: verified (grep -c ':waitForTaskToken' definition.json = 0)
  [✓] ASL definition validated: Distributed Map (MaxConcurrency 1000, S3 ItemReader)
        + Lambda Task with idempotency key (see ASL below)
  [✓] IAM execution role: sfn-event-processor-exec, trust=states.us-east-1.amazonaws.com,
        scoped to lambda:InvokeFunction on arn:aws:lambda:us-east-1:123456789012:function:process-event
        + s3:GetObject on arn:aws:s3:::event-input-bucket/events/*.json
  [✓] Logging: /aws/states/event-processor-express, level ALL, includeExecutionData=true
        (30-day retention; see logging CLI below)
  [✓] Invocation mode: async (EventBridge schedule rate(5 minutes))
  [✓] EventBridge schedule: rule event-processor-schedule, target role eventbridge-sfn-role,
        CloudWatch alarm event-processor-failed on ExecutionsFailed >= 1
  [✓] Idempotency: ProcessEvent Lambda checks IdempotencyKey=$$.Execution.Id against
        DynamoDB table event-idempotency before writing; duplicate retries are no-ops
VERIFICATION_COMMANDS:
  aws stepfunctions describe-state-machine --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:event-processor-express
  grep -c ':waitForTaskToken' definition.json
  aws logs describe-log-groups --log-group-name-prefix /aws/states/event-processor-express
  aws events describe-rule --name event-processor-schedule
  aws cloudwatch describe-alarms --alarm-names event-processor-failed
```

ASL definition (Distributed Map + Lambda Task with idempotency key):

```json
{
  "StartAt": "FanOutProcess",
  "States": {
    "FanOutProcess": {
      "Type": "Map",
      "ItemProcessor": {
        "ProcessorConfig": { "Mode": "DISTRIBUTED" },
        "StartAt": "ProcessEvent",
        "States": {
          "ProcessEvent": {
            "Type": "Task",
            "Resource": "arn:aws:lambda:us-east-1:123456789012:function:process-event",
            "Parameters": {
              "IdempotencyKey.$": "$$.Execution.Id",
              "EventPayload.$": "$.value"
            },
            "Retry": [
              { "ErrorEquals": ["States.TaskFailed"], "MaxAttempts": 3, "BackoffRate": 2 }
            ],
            "End": true
          }
        }
      },
      "ItemReader": {
        "Resource": "arn:aws:states:::s3:getObject",
        "Parameters": { "Bucket": "event-input-bucket", "Key": "events/batch.json" }
      },
      "MaxConcurrency": 1000,
      "End": true
    }
  }
}
```

Logging configuration CLI (create log group with retention + attach
at state machine creation):

```bash
aws logs create-log-group --log-group-name /aws/states/event-processor-express
aws logs put-retention-policy \
  --log-group-name /aws/states/event-processor-express --retention-in-days 30

aws stepfunctions create-state-machine \
  --name event-processor-express \
  --definition file://definition.json \
  --role-arn arn:aws:iam::123456789012:role/sfn-event-processor-exec \
  --type EXPRESS \
  --logging-configuration \
    level=ALL,includeExecutionData=true,\
    destinations='[{CloudWatchLogsLogGroup={LogGroupArn=arn:aws:logs:us-east-1:123456789012:log-group:/aws/states/event-processor-express:*}}]'
```

### Perfect example output — PREREQUISITES_MISSING

```text
EXPRESS_WORKFLOW: approval-flow
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Express-vs-Standard decision: EXPRESS requested
  [✗] Duration budget: workflow includes a 4-min Glue job plus a 2-min downstream ECS task; cannot fit in 5-min cap — migrate to STANDARD or split
  [✗] No .waitForTaskToken in ASL: FAILED — arn:aws:states:::sqs:sendMessage.waitForTaskToken at line 18; replace with .sync or STANDARD
  [✗] ASL definition validated: blocked pending integration fixes
  [✓] IAM execution role: scoped
  [✗] Logging: not yet attached — create /aws/states/approval-flow first
  [OPTIONAL] Invocation mode: not applicable pending ASL fix
  [OPTIONAL] EventBridge schedule: not requested
  [✗] Idempotency: cannot verify pending ASL fix
VERIFICATION_COMMANDS:
  grep -E ':waitForTaskToken' approval-flow.json
  aws logs create-log-group --log-group-name /aws/states/approval-flow
```

**Self-check before emit:**
- [ ] All 9 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] ASL contains NO `.waitForTaskToken` (verified by grep)?
- [ ] Logging row cites log group name + level (ALL or ERROR) + includeExecutionData?
- [ ] Sync caller timeout ≤ 29s verified (if sync mode)?
- [ ] Idempotency row cites the key source for each side-effecting integration?
- [ ] Express-vs-Standard row cites the cost-model comparison ($1/M vs $25/M)?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

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
