---
name: eventbridge-scheduler-deployer
description: 'Provisions Amazon EventBridge Scheduler schedules with production defaults: schedule creation (rate-based vs cron-based), flexible time window (OFF vs MAXIMUM), target types (Lambda, Step Functions, SNS, SQS, Kinesis, Inspector, CodeBuild, and more), one-time vs recurring schedules, timezone specification, group management for bulk enable/disable, automatic schedule deletion after completion, retry policy with exponential backoff, dead-letter queue (DLQ), IAM role for target invocation (Scheduler creates and manages its own role), start/after and end/before time windows, target input (constant JSON), schedule state (ENABLED / DISABLED), and CloudWatch metrics. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an. Triggers: eventbridge scheduler, eventbridge schedule, rate schedule, cron schedule, flexible time window, one-time schedule, schedule group, scheduler retry policy, scheduler DLQ, scheduler timezone, scheduler target lambda step functions sns sqs, scheduler IAM role.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with scheduler, iam, sqs, lambda, stepfunctions, sns, kms, and cloudwatch access. Works with Terraform aws_scheduler_schedule / aws_scheduler_schedule_group resources, CloudFormation AWS::Scheduler::Schedule / AWS::Scheduler::ScheduleGroup templates, and the EventBridge Scheduler API (create-schedule, create-schedule-group).'
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, eventbridge, scheduler, appintegration, cloudops, deploy, provisioning, rate, cron, flexible-time-window, one-time-schedule, schedule-group, retry-policy, dead-letter-queue
  dependencies: aws-orchestrator
  keywords: aws, eventbridge, scheduler, schedule, appintegration, cloudops, deploy, provisioning, rate, cron, flexible-time-window, one-time-schedule, schedule-group, retry-policy, dead-letter-queue, timezone, target-invocation
  when_to_use: Invoke when the user wants to create an EventBridge Scheduler schedule (rate or cron based), configure a flexible time window for cost optimization, set up a one-time schedule, manage schedule groups for bulk enable/disable, configure retry policy and DLQ, specify a timezone, or wire a target (Lambda, Step Functions, SNS, SQS, Kinesis, Inspector, CodeBuild, etc.). Do NOT invoke for EventBridge event bus rules (use eventbridge-rule-deployer), EventBridge Pipes (use eventbridge-pipe-deployer), or CloudWatch Events (legacy — use Scheduler instead).
---

# EventBridge Scheduler Deployer

An AWS CloudOps agent skill that provisions Amazon EventBridge
Scheduler schedules with correct production defaults. The skill
walks the rate-vs-cron decision, flexible time window optimization
(batching for cost reduction), target invocation IAM role (Scheduler
creates and manages its own role per target type), group-level
operations for bulk enable/disable, one-time vs recurring schedules,
retry policy with dead-letter queue, timezone specification, and
schedule state management, captures scheduling and target decisions,
explains why each default matters, and emits a READY_TO_DEPLOY
checklist with copy-pasteable verification commands.

## Activation keywords

eventbridge scheduler, eventbridge schedule, rate schedule, cron
schedule, flexible time window, one-time schedule, schedule group,
scheduler retry policy, scheduler DLQ, scheduler timezone, scheduler
target lambda step functions sns sqs, scheduler IAM role.

## STRICT output contract

When this skill is invoked with an EventBridge-Scheduler-provisioning
request (create a schedule, configure rate or cron, set up flexible
time window, configure retry/DLQ, manage groups, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `SCHEDULER:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Rate vs cron schedule expressions | Schedule type decision |
| Step 2 — Flexible time window (cost optimization) | Batching |
| Step 3 — Target types and IAM role | Target invocation |
| Step 4 — One-time vs recurring schedules | Schedule lifecycle |
| Step 5 — Timezone specification | TZ handling |
| Step 6 — Schedule groups (bulk operations) | Group management |
| Step 7 — Retry policy and DLQ | Error handling |
| Step 8 — Start/after and end/before time windows | Schedule bounds |
| Step 9 — Target input (constant JSON) | Input passing |
| Step 10 — Schedule state (ENABLED/DISABLED) | State management |
| Step 11 — CloudWatch metrics | Monitoring |
| Step 12 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/schedule-expressions-and-flex-window.md | Expression + window detail |
| references/targets-iam-and-error-handling.md | Target + IAM + retry detail |

## Mindset

**One-line takeaway:** EventBridge Scheduler is a serverless
scheduler that invokes AWS targets at specified times. It creates
and manages its own IAM role for target invocation (you do NOT
pre-create the role). Flexible time windows reduce cost by batching
invocations within a window. Schedule groups enable bulk enable/
disable. One-time schedules auto-delete after completion if
configured.

Three misconceptions dominate EventBridge Scheduler misdesign at
provisioning time:

- **"I need to create an IAM role for the Scheduler to assume."**
  You do NOT. The Scheduler creates and manages its own IAM role
  automatically. You specify the target ARN and the Scheduler
  generates the appropriate permissions policy. The only role
  requirement is that the CALLER (you) must have
  `iam:PassRole` permission so the Scheduler can use the role it
  creates.

- **"Flexible time window OFF means immediate invocation."** It
  does NOT mean immediate — it means the Scheduler invokes at the
  exact schedule time. Setting the window to MAXIMUM means the
  Scheduler can invoke any time within the window (batching for
  cost optimization). The trade-off is precision vs cost: OFF is
  precise but more expensive; MAXIMUM is cheaper but less precise
  about exact invocation time.

- **"Schedule groups are just for organization."** They are NOT
  just labels. Groups enable bulk operations: you can enable or
  disable ALL schedules in a group with one API call. This is
  critical for maintenance windows, feature flags, and environment
  promotions. Without groups, you must toggle schedules one by one.

## Configuration dependency graph (novel heuristic)

EventBridge Scheduler configurations are NOT independent. The IAM
role is auto-created per target type. The flexible time window
affects cost and precision. DLQ must exist before schedule creation.
Groups must exist before schedules are assigned. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Schedule group | Caller has scheduler:CreateScheduleGroup | group name is immutable (cannot rename); group CANNOT be deleted if it has schedules | group-level bulk enable/disable |
| Schedule (rate) | Target ARN exists; caller has scheduler:CreateSchedule + iam:PassRole | rate expression minimum is 1 minute; flexible time window must be >= rate for MAXIMUM mode | periodic target invocation |
| Schedule (cron) | Target ARN exists; caller has scheduler:CreateSchedule + iam:PassRole | cron expression uses UTC fields but timezone can be specified; cron is more precise than rate | precise-time target invocation |
| One-time schedule | Target ARN exists; schedule date/time in the future | one-time schedule with delete-after-completion=true is REMOVED after invocation — no history remains in the API | single-fire target invocation |
| Flexible time window (OFF) | Schedule rate or cron specified | OFF means exact-time invocation (higher cost per invocation) | precise scheduling |
| Flexible time window (MAXIMUM) | Schedule rate specified; window must be >= rate interval | MAXIMUM batches invocations within the window — reduces cost but invocation time is imprecise | cost-optimized scheduling |
| IAM role (target invocation) | Scheduler auto-creates; caller must have iam:PassRole | role is managed by Scheduler — do NOT manually edit or delete it | target invocation permissions |
| Retry policy | DLQ ARN (if configured); max retry count + max event age | retries use exponential backoff; after max retries, event goes to DLQ | error recovery |
| Dead-letter queue (DLQ) | SQS queue exists before schedule creation; caller has sqs permissions | DLQ receives failed invocations after retries are exhausted — messages persist until processed | error handling |
| Start/after time | Schedule created; start datetime in the future | schedule does NOT fire before the start time — it is effectively DISABLED until then | delayed activation |
| End/before time | Schedule created; end datetime in the future | schedule does NOT fire after the end time — it is effectively DISABLED after then | automatic deactivation |
| Target input (constant JSON) | Valid JSON string; target accepts the input format | input is passed verbatim to the target — invalid JSON causes invocation failure | parameterized invocation |

**The IAM-role-auto-creation row is the one a baseline model misses.**
A model that tries to pre-create a role for the Scheduler to assume
will create unnecessary complexity. The Scheduler handles role
creation and permission scoping automatically. The caller only needs
`iam:PassRole` to authorize the Scheduler to use the managed role.

**Cross-dependency gotchas:**
- The DLQ SQS queue MUST exist before the schedule is created. If
  the queue does not exist, schedule creation fails.
- The flexible time window MUST be >= the rate interval for MAXIMUM
  mode. If the window is smaller than the rate, the API rejects it.
- One-time schedules with `delete-after-completion=true` leave no
  trace in the API after firing. If you need audit history, set it
  to false or log externally.
- Schedule group deletion fails if the group contains schedules.
  Delete or move all schedules first.
- Timezone is specified per schedule, not per group. Two schedules
  in the same group can have different timezones.

## Expert heuristic: the flexible time window trade-off

A baseline model says "set flexible time window to OFF for
precision." The correct heuristic recognizes that MAXIMUM reduces
cost by batching invocations within the window, trading precision
for cost savings.

```text
Schedule: rate(1 hour)

Flexible time window OFF:
  → Invokes EXACTLY at :00 each hour (or close to it)
  → 24 invocations per day per schedule
  → Higher cost (more invocations)
  → Use when: precision matters (billing, reminders, exact-time jobs)

Flexible time window MAXIMUM(1 hour):
  → Invokes any time within the 1-hour window
  → Scheduler batches invocations for efficiency
  → Fewer "actual" API calls (batched internally)
  → Lower cost
  → Use when: precision does NOT matter (cleanup, health checks,
    periodic polling, log rotation)

Decision matrix:
  ├── Need exact-time invocation? → OFF
  ├── Need cost optimization for periodic tasks? → MAXIMUM
  └── One-time schedule? → OFF (window does not apply meaningfully)
```

**Key implication:** for periodic maintenance tasks (cleanup, log
rotation, health checks), MAXIMUM can reduce costs significantly
when you have hundreds of schedules. For time-sensitive tasks
(billing, reminders, alerts), use OFF.

## Expert heuristic: Scheduler-managed IAM role

A baseline model tries to create an IAM role for the Scheduler to
assume. The correct heuristic recognizes that the Scheduler creates
and manages its own role.

```text
Target invocation flow:
  1. Caller creates schedule with target ARN (e.g., Lambda function)
  2. Scheduler auto-creates IAM role:
     → Role name: Amazon_EventBridge_Scheduler_Lambda_Assume_Role_<random>
     → Trust policy: allows scheduler.amazonaws.com to assume
     → Permissions: lambda:InvokeFunction on the target ARN
  3. Caller must have iam:PassRole to authorize role usage
  4. Scheduler invokes the target using the auto-created role

What the caller needs:
  ├── scheduler:CreateSchedule (to create the schedule)
  ├── iam:PassRole (to authorize the Scheduler's managed role)
  └── NOT iam:CreateRole (Scheduler handles this)

Per-target-type permissions:
  ├── Lambda target → lambda:InvokeFunction
  ├── Step Functions → states:StartExecution
  ├── SNS target → sns:Publish
  ├── SQS target → sqs:SendMessage
  ├── Kinesis target → kinesis:PutRecord
  ├── CodeBuild → codebuild:StartBuild
  ├── Inspector → inspector-specific actions
  └── Universal template → Amazon EventBridge Scheduler Lambda role
```

**Key implication:** do NOT pre-create roles. Do NOT manually edit
the Scheduler-managed role. The role is auto-scoped to the specific
target ARN, providing least-privilege access without manual
configuration.

## Expert heuristic: schedule groups for bulk operations

A baseline model creates schedules without groups. The correct
heuristic uses groups for bulk enable/disable, which is critical
for maintenance windows and environment promotions.

```text
Group operations:
  aws scheduler update-schedule-group \
    --name prod-schedules --state DISABLED
  → ALL schedules in prod-schedules are disabled instantly

  aws scheduler update-schedule-group \
    --name prod-schedules --state ENABLED
  → ALL schedules in prod-schedules are enabled instantly

Use cases:
  ├── Maintenance windows: disable non-critical schedules during deploys
  ├── Feature flags: enable/disable scheduled jobs per environment
  ├── Cost control: disable schedules in non-prod during off-hours
  └── Environment promotion: disable staging, enable prod

Without groups:
  → Must call update-schedule for EACH schedule individually
  → N schedules = N API calls (slow, error-prone)
  → No atomic bulk operation
```

**Key implication:** always assign schedules to groups at creation
time. Retroactively grouping schedules requires deletion and
recreation (group assignment is immutable after creation).

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Target ARN exists | Scheduler needs a valid target to invoke | `aws lambda get-function --function-name <name>` (or equivalent) |
| iam:PassRole permission | Caller must authorize Scheduler's managed role | Check caller's IAM policies |
| Schedule group exists (if group specified) | Group must exist before schedules are assigned | `aws scheduler list-schedule-groups` |
| DLQ SQS queue exists (if retry/DLQ configured) | DLQ must exist before schedule creation | `aws sqs get-queue-url --queue-name <name>` |
| Schedule expression valid | Rate or cron expression must be syntactically correct | Validate expression syntax |
| Timezone identified | Affects cron evaluation; default is UTC | Confirm timezone (e.g., America/New_York) |
| Start/end time windows (if bounded) | Must be valid ISO 8601 datetimes in the future | Confirm datetime values |
| Target input JSON valid (if constant input) | Invalid JSON causes invocation failure | Validate JSON structure |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Rate vs cron schedule expressions

EventBridge Scheduler supports two expression types:

| Type | Syntax | Example | When to use |
|---|---|---|---|
| Rate | `rate(<value> <unit>)` | `rate(5 minutes)`, `rate(1 hour)` | Simple periodic schedules; minimum 1 minute |
| Cron | `cron(<fields>)` | `cron(0 9 ? * MON-FRI *)` | Complex schedules with specific day/time requirements |

**Rate expression rules:**
- Singular for 1: `rate(1 minute)` (NOT `rate(1 minutes)`)
- Plural for >1: `rate(5 minutes)` (NOT `rate(5 minute`)
- Minimum: 1 minute
- Units: minute(s), hour(s), day(s)

**Cron expression rules:**
- 6 fields: Minutes, Hours, Day-of-month, Month, Day-of-week, Year
- `?` for "no specific value" (use in either Day-of-month or Day-of-week)
- `*` for "all values"
- `MON-FRI` for ranges
- `L` for last day of month

```bash
# Rate-based schedule (every 15 minutes)
aws scheduler create-schedule \
  --name my-schedule \
  --schedule-expression "rate(15 minutes)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{"RoleArn": "arn:aws:iam::123456789012:role/SchedulerRole", "Arn": "arn:aws:lambda:us-east-1:123456789012:function:my-function"}' \
  --region us-east-1

# Cron-based schedule (9 AM weekdays, US Eastern)
aws scheduler create-schedule \
  --name weekday-morning \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{"RoleArn": "...", "Arn": "..."}' \
  --region us-east-1
```

## Step 2 — Flexible time window (cost optimization)

The flexible time window controls invocation precision and cost.

| Mode | Behavior | Cost | When to use |
|---|---|---|---|
| OFF | Invokes at exact schedule time | Higher | Time-sensitive jobs |
| MAXIMUM | Invokes any time within window | Lower | Non-time-sensitive periodic tasks |

```bash
# Flexible time window OFF (exact-time invocation)
aws scheduler create-schedule \
  --name precise-schedule \
  --schedule-expression "rate(1 hour)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '...' \
  --region us-east-1

# Flexible time window MAXIMUM (cost-optimized batching)
aws scheduler create-schedule \
  --name batched-schedule \
  --schedule-expression "rate(1 hour)" \
  --flexible-time-window '{"Mode": "FLEXIBLE", "MaximumWindowInMinutes": 60}' \
  --target '...' \
  --region us-east-1
```

**Critical:** the MaximumWindowInMinutes must be >= the rate interval.
For `rate(1 hour)`, the window must be >= 60 minutes.

## Step 3 — Target types and IAM role

The Scheduler supports many target types. It auto-creates an IAM
role scoped to each target.

| Target type | ARN format | Auto-created role permission |
|---|---|---|
| Lambda | `arn:aws:lambda:<region>:<acct>:function:<name>` | `lambda:InvokeFunction` |
| Step Functions | `arn:aws:states:<region>:<acct>:stateMachine:<name>` | `states:StartExecution` |
| SNS | `arn:aws:sns:<region>:<acct>:<name>` | `sns:Publish` |
| SQS | `arn:aws:sqs:<region>:<acct>:<name>` | `sqs:SendMessage` |
| Kinesis | `arn:aws:kinesis:<region>:<acct>:stream/<name>` | `kinesis:PutRecord` |
| CodeBuild | `arn:aws:codebuild:<region>:<acct>:project/<name>` | `codebuild:StartBuild` |
| Inspector | `arn:aws:inspector2:<region>:<acct>:...` | Inspector-specific |
| ECS | `arn:aws:ecs:<region>:<acct>:...` | `ecs:RunTask` |
| CodePipeline | `arn:aws:codepipeline:<region>:<acct>:...` | `codepipeline:StartPipelineExecution` |

```bash
# Lambda target
--target '{
  "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSchedulerRole",
  "Arn": "arn:aws:lambda:us-east-1:123456789012:function:my-function"
}'

# Step Functions target
--target '{
  "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSchedulerRole",
  "Arn": "arn:aws:states:us-east-1:123456789012:stateMachine:my-statemachine"
}'

# SNS target
--target '{
  "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSchedulerRole",
  "Arn": "arn:aws:sns:us-east-1:123456789012:my-topic"
}'
```

**The RoleArn in the target** is the role the Scheduler assumes to
invoke the target. The Scheduler can auto-manage this if using the
console; via CLI, you specify a pre-existing role that the Scheduler
assumes. The caller must have `iam:PassRole` for this role.

## Step 4 — One-time vs recurring schedules

| Type | Schedule expression | Behavior | Delete after completion |
|---|---|---|---|
| Recurring | `rate(...)` or `cron(...)` | Fires repeatedly on schedule | N/A |
| One-time | `at(2026-08-15T09:00:00)` | Fires once at the specified time | `--delete-after-completion` |

```bash
# One-time schedule (fires once, auto-deletes)
aws scheduler create-schedule \
  --name one-time-job \
  --schedule-expression "at(2026-08-15T09:00:00)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '...' \
  --region us-east-1

# One-time schedule with auto-delete
aws scheduler create-schedule \
  --name one-time-cleanup \
  --schedule-expression "at(2026-08-20T02:00:00)" \
  --schedule-expression-timezone "UTC" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '...' \
  --region us-east-1
# After firing, the schedule is automatically deleted
```

**Key:** one-time schedules use `at(<ISO-8601 datetime>)` expression.
With `delete-after-completion`, no trace remains in the API.

## Step 5 — Timezone specification

Timezone is set per-schedule using IANA timezone identifiers:

```bash
aws scheduler create-schedule \
  --name ny-business-hours \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '...' \
  --region us-east-1
```

**Common timezones:**
- `UTC` — default
- `America/New_York` — US Eastern
- `America/Los_Angeles` — US Pacific
- `Europe/London` — UK
- `Asia/Tokyo` — Japan
- `Australia/Sydney` — Australia Eastern

**Critical:** timezone affects cron evaluation but NOT rate. Rate
expressions are timezone-independent (they count from schedule
creation). Only cron and `at()` expressions are timezone-sensitive.

## Step 6 — Schedule groups (bulk operations)

Groups enable bulk enable/disable of all schedules within the group.

```bash
# Create a schedule group
aws scheduler create-schedule-group \
  --name prod-schedules \
  --region us-east-1

# Create a schedule within a group
aws scheduler create-schedule \
  --name hourly-report \
  --group-name prod-schedules \
  --schedule-expression "rate(1 hour)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '...' \
  --region us-east-1

# Bulk disable all schedules in the group
aws scheduler update-schedule-group \
  --name prod-schedules \
  --state DISABLED \
  --region us-east-1

# Bulk enable all schedules in the group
aws scheduler update-schedule-group \
  --name prod-schedules \
  --state ENABLED \
  --region us-east-1
```

**Critical:** group assignment is immutable. You CANNOT move a
schedule between groups. To change groups, delete and recreate the
schedule.

## Step 7 — Retry policy and DLQ

The retry policy controls how the Scheduler retries failed
invocations. The DLQ receives events that exhaust all retries.

```bash
aws scheduler create-schedule \
  --name resilient-schedule \
  --schedule-expression "rate(30 minutes)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSchedulerRole",
    "Arn": "arn:aws:lambda:us-east-1:123456789012:function:my-function",
    "RetryPolicy": {
      "MaximumRetryAttempts": 3,
      "MaximumEventAgeInSeconds": 3600
    },
    "DeadLetterConfig": {
      "Arn": "arn:aws:sqs:us-east-1:123456789012:scheduler-dlq"
    }
  }' \
  --region us-east-1
```

**Retry behavior:**
- `MaximumRetryAttempts`: 0-185 (default 185)
- `MaximumEventAgeInSeconds`: 60-86400 (default 86400 = 24 hours)
- Retries use exponential backoff
- After all retries are exhausted, the event goes to the DLQ

**DLQ requirement:** the SQS queue MUST exist before schedule
creation.

## Step 8 — Start/after and end/before time windows

These parameters bound when the schedule is active:

```bash
aws scheduler create-schedule \
  --name bounded-schedule \
  --schedule-expression "rate(1 hour)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --start-date "2026-08-11T00:00:00Z" \
  --end-date "2026-09-11T00:00:00Z" \
  --target '...' \
  --region us-east-1
```

- `--start-date`: schedule does NOT fire before this datetime
- `--end-date`: schedule does NOT fire after this datetime

**Use case:** time-limited campaigns, seasonal jobs, or schedules
that should only run during a specific window.

## Step 9 — Target input (constant JSON)

Pass a fixed JSON payload to the target on every invocation:

```bash
aws scheduler create-schedule \
  --name parameterized-schedule \
  --schedule-expression "rate(1 hour)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '{
    "RoleArn": "arn:aws:iam::123456789012:role/EventBridgeSchedulerRole",
    "Arn": "arn:aws:lambda:us-east-1:123456789012:function:my-function",
    "Input": "{\"environment\": \"production\", \"region\": \"us-east-1\"}"
  }' \
  --region us-east-1
```

The `Input` field is passed verbatim to the target. Invalid JSON
causes invocation failure.

## Step 10 — Schedule state (ENABLED/DISABLED)

Each schedule has a state that can be toggled:

```bash
# Disable a specific schedule
aws scheduler update-schedule \
  --name my-schedule \
  --state DISABLED \
  --schedule-expression "rate(1 hour)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '...' \
  --region us-east-1

# Enable a specific schedule
aws scheduler update-schedule \
  --name my-schedule \
  --state ENABLED \
  --schedule-expression "rate(1 hour)" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '...' \
  --region us-east-1
```

**Note:** `update-schedule` requires ALL parameters (not just the
state change). This is a full-replacement API.

## Step 11 — CloudWatch metrics

EventBridge Scheduler emits CloudWatch metrics:

| Metric | Description |
|---|---|
| `Invocations` | Number of target invocations |
| `InvocationsFailed` | Number of failed invocations |
| `InvocationsFailedToBeSentToDlq` | Invocations that failed AND failed DLQ delivery |
| `ThrottledEvents` | Events throttled by the Scheduler |

```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Scheduler \
  --metric-name Invocations \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-11T00:00:00Z \
  --period 86400 \
  --statistics Sum \
  --region us-east-1
```

## Step 12 — Recent features

**Recent AWS features (2023-2026):**

- **EventBridge Scheduler GA (2023-2024):** General availability of
  EventBridge Scheduler, providing a serverless, managed scheduler
  with no infrastructure to manage. Supports 200+ AWS target types
  via universal templates.

- **Schedule groups (2023-2024):** Group-level bulk operations for
  enable/disable, enabling maintenance window patterns and
  environment-level schedule management.

- **Timezone support (2023-2024):** Per-schedule timezone
  specification using IANA identifiers, eliminating the need to
  manually convert cron expressions to UTC.

- **One-time schedules with auto-delete (2023-2024):** One-time
  schedules can auto-delete after completion, preventing clutter
  in the schedule inventory.

- **Universal templates (2024-2025):** Expanded target templates
  covering Inspector, ECS RunTask, CodePipeline StartExecution,
  and more, simplifying target configuration.

- **Enhanced retry controls (2024-2025):** Granular retry policy
  with configurable max attempts and max event age, plus DLQ
  support for failed invocations.

- **Terraform provider maturity (2024-2025):** Full Terraform
  support for aws_scheduler_schedule and
  aws_scheduler_schedule_group, including flexible time window,
  retry policy, DLQ, and timezone.

## NEVER do these things

1. **NEVER pre-create an IAM role for the Scheduler to assume.**
   The Scheduler auto-creates and manages its own role scoped to
   the target ARN. You only need `iam:PassRole` permission. Pre-
   creating roles adds unnecessary complexity and can lead to over-
   privileged policies.

2. **NEVER set flexible time window to MAXIMUM for time-sensitive
   jobs.** MAXIMUM batches invocations within the window, meaning
   the actual invocation time is imprecise. Use OFF for billing,
   reminders, alerts, and any job where exact timing matters.

3. **NEVER forget to create the DLQ SQS queue before the schedule.**
   If the DLQ does not exist, schedule creation fails. Create the
   queue first, then reference its ARN in the schedule's target
   configuration.

4. **NEVER assume group assignment can be changed.** Group
   assignment is immutable. To move a schedule between groups,
   you must delete and recreate it. Always assign groups at
   creation time.

5. **NEVER use a flexible time window smaller than the rate.** The
   MaximumWindowInMinutes must be >= the rate interval. A window
   smaller than the rate is rejected by the API.

6. **NEVER forget that update-schedule is a full-replacement API.**
   When updating a schedule, ALL parameters must be provided, not
   just the changed field. Omitting parameters resets them to
   defaults or causes errors.

7. **NEVER assume one-time schedules persist after firing.** With
   `delete-after-completion=true`, the schedule is removed after
   invocation. If you need audit history, set it to false or log
   externally.

8. **NEVER use rate expressions for timezone-sensitive schedules.**
   Rate is timezone-independent (counts from creation). Only cron
   and `at()` expressions are affected by timezone. For "9 AM in
   New York," use cron with `--schedule-expression-timezone`.

9. **NEVER delete a schedule group that has schedules.** Group
   deletion fails if schedules exist. Delete or move all schedules
   first, then delete the group.

10. **NEVER ignore failed invocation metrics.** Monitor
    `InvocationsFailed` and `InvocationsFailedToBeSentToDlq` in
    CloudWatch. Silent failures are common when targets are
    misconfigured or permissions drift.

## Output format

```text
SCHEDULER: <schedule-name> (<schedule-expression>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Schedule name: <name>
  [✓|✗] Schedule type: <rate | cron | one-time>
  [✓|✗] Expression: <expression> (timezone: <tz>)
  [✓|✗] Flexible time window: <OFF | MAXIMUM(<N> min)>
  [✓|✗] Target: <type> — <arn>
  [✓|✗] IAM role: Scheduler-managed (auto-scoped to target ARN)
  [✓|✗] Target input: <constant JSON | none>
  [✓|✗] Schedule group: <group-name | default>
  [✓|✗] Retry policy: max <N> attempts, max age <N>s
  [✓|✗] Dead-letter queue: <sqs-arn | none>
  [✓|✗] Start date: <ISO-8601 | none>
  [✓|✗] End date: <ISO-8601 | none>
  [✓|✗] State: ENABLED | DISABLED
  [✓|✗] Delete after completion: <true | false> (one-time only)
  [✓|✗] CloudWatch metrics: Invocations, InvocationsFailed
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws scheduler get-schedule --name <name> [--group-name <group>] --region <region>
  aws scheduler list-schedules [--group-name <group>] --region <region>
```

### Worked example — Lambda rate schedule with retry and DLQ

```text
SCHEDULER: hourly-report (rate(1 hour))
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Schedule name: hourly-report
  [✓] Schedule type: rate
  [✓] Expression: rate(1 hour) (timezone: UTC)
  [✓] Flexible time window: OFF (exact-time invocation)
  [✓] Target: Lambda — arn:aws:lambda:us-east-1:123456789012:function:report-generator
  [✓] IAM role: Scheduler-managed (auto-scoped to target ARN)
  [✓] Target input: {"report_type": "hourly", "env": "prod"}
  [✓] Schedule group: prod-schedules
  [✓] Retry policy: max 3 attempts, max age 3600s
  [✓] Dead-letter queue: arn:aws:sqs:us-east-1:123456789012:scheduler-dlq
  [✓] Start date: none
  [✓] End date: none
  [✓] State: ENABLED
  [✓] Delete after completion: false (recurring)
  [✓] CloudWatch metrics: Invocations, InvocationsFailed
  [✓] Tags: Environment=production, Team=data
VERIFICATION_COMMANDS:
  aws scheduler get-schedule --name hourly-report --group-name prod-schedules --region us-east-1
  aws scheduler list-schedules --group-name prod-schedules --region us-east-1
```

## Error handling

### Schedule creation fails with IAM error
- The caller does not have `iam:PassRole` permission. Add this to
  the caller's IAM policy. The Scheduler needs to assume the role
  it manages, and `iam:PassRole` authorizes this handoff.

### Invocations failing silently
- Check CloudWatch `InvocationsFailed` metric. Common causes: target
  does not exist, target permissions are wrong, or the target input
  JSON is malformed. Enable DLQ to capture failed events for
  debugging.

### DLQ not receiving failed events
- The SQS queue may not exist, or the Scheduler's role may not have
  `sqs:SendMessage` on the queue. Verify the queue ARN and that the
  role policy includes SQS access.

### Flexible time window rejected
- The MaximumWindowInMinutes is smaller than the rate interval. The
  window must be >= the rate. For `rate(15 minutes)`, the window
  must be >= 15 minutes.

### Group deletion fails
- The group still has schedules. Delete or move all schedules to
  another group, then delete the group. Use `list-schedules --group-
  name <name>` to find remaining schedules.

### One-time schedule did not fire
- Verify the datetime is in the future and the timezone is correct.
  One-time schedules use `at(<datetime>)`. If the datetime has
  passed, the schedule will never fire. Check with `get-schedule`.

## Domain

AWS CloudOps / Amazon EventBridge Scheduler Provisioning & Managed
Scheduling.

## AWS documentation

- **EventBridge Scheduler** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/what-is-scheduler.html
- **Create schedule** — https://docs.aws.amazon.com/scheduler/latest/APIReference/API_CreateSchedule.html
- **Schedule groups** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/manage-schedule-groups.html
- **Rate and cron expressions** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html
- **Flexible time windows** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/using-scheduler-flexible-window.html
- **Target types** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/manage-schedule-targets.html
- **Retry policy and DLQ** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/using-scheduler-retry.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/monitoring-cloudwatch.html
- **IAM for Scheduler** — https://docs.aws.amazon.com/scheduler/latest/UserGuide/security_iam_service-with-iam.html
- **Terraform aws_scheduler_schedule** — https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/scheduler_schedule
