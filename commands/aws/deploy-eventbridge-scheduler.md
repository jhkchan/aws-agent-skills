---
description: Provision an Amazon EventBridge Scheduler schedule with production-grade defaults (rate vs cron expressions, flexible time window, target invocation, schedule groups, retry policy, DLQ, timezone, one-time vs recurring). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "eventbridge scheduler"
  - "eventbridge schedule"
  - "rate schedule"
  - "cron schedule"
  - "flexible time window"
  - "one-time schedule"
  - "schedule group"
  - "scheduler retry policy"
  - "scheduler dlq"
  - "scheduler timezone"
  - "create eventbridge schedule"
  - "deploy eventbridge scheduler"
  - "scheduler target"
routes_to: eventbridge-scheduler-deployer
---

# /aws:deploy-eventbridge-scheduler

Activate the `eventbridge-scheduler-deployer` skill and provision an
Amazon EventBridge Scheduler schedule with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Rate vs cron schedule expressions
2. Flexible time window (OFF vs MAXIMUM for cost optimization)
3. Target types and IAM role (Scheduler-managed)
4. One-time vs recurring schedules
5. Timezone specification
6. Schedule groups (bulk enable/disable)
7. Retry policy and DLQ
8. Start/after and end/before time windows
9. Target input (constant JSON)
10. Schedule state (ENABLED/DISABLED)
11. CloudWatch metrics (Invocations, InvocationsFailed)
12. Recent features (universal templates, timezone, auto-delete)

## When to use

- You need to create an EventBridge schedule (rate or cron based).
- You want to configure a flexible time window for cost optimization.
- You need a one-time schedule with auto-delete.
- You want to manage schedule groups for bulk enable/disable.
- You need retry policy and DLQ configuration.
- You need to specify a timezone for cron evaluation.
- You want to pass constant JSON input to the target.

## When NOT to use

- **EventBridge event bus rules** — use eventbridge-rule-deployer for
  event-pattern-based routing.
- **EventBridge Pipes** — use eventbridge-pipe-deployer for
  point-to-point event streaming.
- **CloudWatch Events (legacy)** — use EventBridge Scheduler instead
  for scheduled invocations.

## How to invoke

### Slash command

```
/aws:deploy-eventbridge-scheduler
```

Then provide: schedule name, expression (rate or cron), target type
and ARN, flexible time window mode, timezone, schedule group name,
retry policy, DLQ ARN, start/end dates, target input JSON, tags.

### Natural language

Any of these routes to the same skill:

- "create an eventbridge schedule that runs every hour"
- "set up a cron schedule for 9 AM weekdays in New York"
- "create a one-time schedule that fires on September 1st"
- "set up a schedule group for bulk enable/disable"
- "configure eventbridge scheduler with retry and DLQ"

### CLI routing

```bash
node cli/bin/cli.js route "create an eventbridge schedule"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create
EventBridge schedules. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-eventbridge-scheduler

     Create a schedule called hourly-report that invokes Lambda
     report-generator every hour. OFF flexible time window.
     Add retry policy (max 3) and DLQ. Group: prod-schedules.

Skill:
  SCHEDULER: hourly-report (rate(1 hour))
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Expression: rate(1 hour)
    [✓] Flexible time window: OFF (exact-time)
    [✓] Target: Lambda — report-generator
    [✓] Retry: max 3 attempts
    [✓] DLQ: scheduler-dlq
    [✓] Group: prod-schedules
  VERIFICATION_COMMANDS:
    aws scheduler get-schedule --name hourly-report --group-name prod-schedules --region us-east-1
```

## References

- Skill definition: `skills/eventbridge-scheduler-deployer/SKILL.md`
- Schedule expressions and flex window: `skills/eventbridge-scheduler-deployer/references/schedule-expressions-and-flex-window.md`
- Targets, IAM, and error handling: `skills/eventbridge-scheduler-deployer/references/targets-iam-and-error-handling.md`
- Eval suite: `skills/eventbridge-scheduler-deployer/evals/evals.json`
