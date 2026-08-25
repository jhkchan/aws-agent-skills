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

Mindset and misconceptions moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Configuration dependency graph (novel heuristic)

Configuration dependency graph moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

## Expert heuristic: the flexible time window trade-off

Flexible time window trade-off heuristic moved to
[references/schedule-expressions-and-flex-window.md](references/schedule-expressions-and-flex-window.md).

## Expert heuristic: Scheduler-managed IAM role

Scheduler-managed IAM role heuristic moved to
[references/targets-iam-and-error-handling.md](references/targets-iam-and-error-handling.md).

## Expert heuristic: schedule groups for bulk operations

Schedule groups bulk-operations heuristic moved to
[references/targets-iam-and-error-handling.md](references/targets-iam-and-error-handling.md).

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

Step 1 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

## Step 2 — Flexible time window (cost optimization)

The flexible time window controls invocation precision and cost.

| Mode | Behavior | Cost | When to use |
|---|---|---|---|
| OFF | Invokes at exact schedule time | Higher | Time-sensitive jobs |
| MAXIMUM | Invokes any time within window | Lower | Non-time-sensitive periodic tasks |

Step 2 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Step 3 target examples moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**The RoleArn in the target** is the role the Scheduler assumes to
invoke the target. The Scheduler can auto-manage this if using the
console; via CLI, you specify a pre-existing role that the Scheduler
assumes. The caller must have `iam:PassRole` for this role.

## Step 4 — One-time vs recurring schedules

| Type | Schedule expression | Behavior | Delete after completion |
|---|---|---|---|
| Recurring | `rate(...)` or `cron(...)` | Fires repeatedly on schedule | N/A |
| One-time | `at(2026-08-15T09:00:00)` | Fires once at the specified time | `--delete-after-completion` |

Step 4 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Key:** one-time schedules use `at(<ISO-8601 datetime>)` expression.
With `delete-after-completion`, no trace remains in the API.

## Step 5 — Timezone specification

Timezone is set per-schedule using IANA timezone identifiers:

Step 5 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Step 6 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Critical:** group assignment is immutable. You CANNOT move a
schedule between groups. To change groups, delete and recreate the
schedule.

## Step 7 — Retry policy and DLQ

The retry policy controls how the Scheduler retries failed
invocations. The DLQ receives events that exhaust all retries.

Step 7 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

**Retry behavior:**
- `MaximumRetryAttempts`: 0-185 (default 185)
- `MaximumEventAgeInSeconds`: 60-86400 (default 86400 = 24 hours)
- Retries use exponential backoff
- After all retries are exhausted, the event goes to the DLQ

**DLQ requirement:** the SQS queue MUST exist before schedule
creation.

## Step 8 — Start/after and end/before time windows

These parameters bound when the schedule is active:

Step 8 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

- `--start-date`: schedule does NOT fire before this datetime
- `--end-date`: schedule does NOT fire after this datetime

**Use case:** time-limited campaigns, seasonal jobs, or schedules
that should only run during a specific window.

## Step 9 — Target input (constant JSON)

Pass a fixed JSON payload to the target on every invocation:

Step 9 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

The `Input` field is passed verbatim to the target. Invalid JSON
causes invocation failure.

## Step 10 — Schedule state (ENABLED/DISABLED)

Each schedule has a state that can be toggled:

Step 10 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

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

Step 11 command listing moved to
[references/diagnostic-commands.md](references/diagnostic-commands.md).

## Step 12 — Recent features

Recent AWS features moved to
[references/advanced-patterns.md](references/advanced-patterns.md).

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

Error-handling deep dives moved to
[references/targets-iam-and-error-handling.md](references/targets-iam-and-error-handling.md).

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — mindset, configuration dependency graph, recent features (moved from this file)
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — per-step create/update command listings (moved from this file)
- [references/schedule-expressions-and-flex-window.md](references/schedule-expressions-and-flex-window.md) — rate/cron/at expressions and flexible time window detail (moved-from heuristic appended)
- [references/targets-iam-and-error-handling.md](references/targets-iam-and-error-handling.md) — targets, IAM role mechanics, schedule groups, retry/DLQ, error handling (moved-from sections appended)

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
