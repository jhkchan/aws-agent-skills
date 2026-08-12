# Schedule Expressions and Flexible Time Windows — EventBridge Scheduler Deployer

Deep reference on EventBridge Scheduler expression types (rate, cron,
one-time at), flexible time window mechanics (OFF vs MAXIMUM, cost
optimization trade-off), timezone handling, start/end time bounds,
and target input (constant JSON). Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure
stays scannable.

## Rate expressions

### Syntax

```text
rate(<value> <unit>)

value: positive integer (1 or greater)
unit:  minute | minutes | hour | hours | day | days
       (singular for 1, plural for >1)
```

### Rules

- Minimum rate: 1 minute
- Rate is timezone-independent (counts from schedule creation)
- Rate does NOT support specific day/time targeting

### Examples

```text
rate(1 minute)     → every minute
rate(5 minutes)    → every 5 minutes
rate(1 hour)       → every hour
rate(6 hours)      → every 6 hours
rate(1 day)        → every day (from creation time)
rate(7 days)       → every 7 days
```

### Common mistakes

```text
rate(1 minutes)    → INVALID (use singular: rate(1 minute))
rate(5 minute)     → INVALID (use plural: rate(5 minutes))
rate(0 minutes)    → INVALID (minimum is 1)
rate(30 seconds)   → INVALID (minimum unit is minutes)
rate(1 month)      → INVALID (month is not a supported unit)
```

## Cron expressions

### Syntax

```text
cron(<Minutes> <Hours> <Day-of-month> <Month> <Day-of-week> <Year>)

Fields:
  Minutes:        0-59
  Hours:          0-23
  Day-of-month:   1-31
  Month:          1-12 or JAN-DEC
  Day-of-week:    1-7 or SUN-SAT
  Year:           * (wildcard)
```

### Special characters

| Character | Meaning | Example |
|---|---|---|
| `*` | All values | `*` in Hours = every hour |
| `?` | No specific value | Use in Day-of-month OR Day-of-week (not both) |
| `-` | Range | `MON-FRI` = Monday through Friday |
| `,` | List | `0,15,30,45` = specific values |
| `/` | Step | `0/15` = every 15 starting at 0 |
| `L` | Last | `L` in Day-of-month = last day of month |
| `#` | Nth | `2#1` in Day-of-week = second day (MON), first occurrence |

### The Day-of-month / Day-of-week rule

You MUST use `?` in one of Day-of-month or Day-of-week. Using specific
values in BOTH causes an error.

```text
cron(0 9 ? * MON-FRI *)  → 9 AM weekdays (Day-of-month = ?, Day-of-week = MON-FRI)
cron(0 0 1 * ? *)        → midnight on the 1st of every month (Day-of-month = 1, Day-of-week = ?)
```

### Timezone and cron

Cron expressions are evaluated in the timezone specified by
`--schedule-expression-timezone`. Without this, the default is UTC.

```bash
# 9 AM US Eastern (accounts for DST automatically)
aws scheduler create-schedule \
  --name ny-morning \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --region us-east-1

# 9 AM UTC (default)
aws scheduler create-schedule \
  --name utc-morning \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --region us-east-1
```

**DST handling:** IANA timezone identifiers automatically adjust for
daylight saving time. A schedule at 9 AM America/New_York fires at
9 AM EST or 9 AM EDT depending on the date.

### Cron examples reference

| Schedule | Expression |
|---|---|
| Every 15 minutes | `cron(0/15 * * * ? *)` |
| Every hour at :00 | `cron(0 * * * ? *)` |
| Every day at midnight | `cron(0 0 * * ? *)` |
| Every Monday at 9 AM | `cron(0 9 ? * MON *)` |
| Weekdays at 5 PM | `cron(0 17 ? * MON-FRI *)` |
| First of every month | `cron(0 0 1 * ? *)` |
| Last day of every month | `cron(0 0 L * ? *)` |
| Every Sunday at 2 AM | `cron(0 2 ? * SUN *)` |
| Quarterly (Jan, Apr, Jul, Oct 1st) | `cron(0 0 1 JAN,APR,JUL,OCT ? *)` |

## One-time schedules (at expression)

### Syntax

```text
at(<ISO-8601 datetime>)

datetime: ISO-8601 format (e.g., 2026-09-01T14:00:00)
timezone: controlled by --schedule-expression-timezone (default UTC)
```

### Auto-delete after completion

One-time schedules can auto-delete after firing:

```bash
aws scheduler create-schedule \
  --name one-time-job \
  --schedule-expression "at(2026-09-01T14:00:00)" \
  --schedule-expression-timezone "UTC" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '...' \
  --region us-east-1
```

With auto-delete, the schedule is removed from the API after it fires.
This prevents schedule clutter but means no API-level audit trail.

**Without auto-delete:** the schedule remains in a COMPLETED state
after firing, providing an audit trail of when it ran.

## Flexible time window

### OFF mode

OFF means the Scheduler invokes the target at the exact schedule time
(as close as possible).

```bash
--flexible-time-window '{"Mode": "OFF"}'
```

**Use OFF when:**
- Exact invocation time matters (billing, reminders, alerts)
- Downstream systems depend on precise timing
- Regulatory or compliance requirements mandate exact-time execution

**Cost implication:** OFF mode costs more per schedule because the
Scheduler cannot batch invocations. Each schedule fires independently
at its exact time.

### FLEXIBLE mode (MAXIMUM)

MAXIMUM means the Scheduler can invoke the target any time within
the specified window. This enables internal batching and cost
optimization.

```bash
--flexible-time-window '{"Mode": "FLEXIBLE", "MaximumWindowInMinutes": 60}'
```

**Use MAXIMUM when:**
- Exact invocation time does NOT matter (cleanup, health checks, polling)
- You have many schedules and want to reduce per-invocation cost
- Periodic maintenance tasks with loose timing requirements

**Constraint:** MaximumWindowInMinutes must be >= the rate interval.
For `rate(1 hour)`, the window must be >= 60 minutes.

### Cost comparison

```text
100 schedules, rate(1 hour), each invoking a Lambda:

OFF mode:
  → ~100 invocations per hour
  → Higher Scheduler cost (more individual invocations)
  → Precise timing

MAXIMUM(60) mode:
  → Scheduler batches invocations within the 60-minute window
  → Lower effective cost per invocation
  → Each schedule fires sometime within its window (imprecise)

Cost difference scales with the number of schedules.
For 10 schedules: negligible. For 1000 schedules: significant.
```

## Start/after and end/before time bounds

### Start date

The schedule does NOT fire before the start date. It is effectively
DISABLED until the start datetime.

```bash
--start-date "2026-08-15T00:00:00Z"
```

### End date

The schedule does NOT fire after the end date. It is effectively
DISABLED after the end datetime.

```bash
--end-date "2026-09-15T00:00:00Z"
```

### Use cases

- **Seasonal campaigns:** schedules that run only during a campaign period
- **Temporary maintenance:** schedules active during a migration window
- **Trial periods:** schedules that stop after a trial ends

```bash
aws scheduler create-schedule \
  --name seasonal-job \
  --schedule-expression "rate(1 day)" \
  --schedule-expression-timezone "UTC" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --start-date "2026-09-01T00:00:00Z" \
  --end-date "2026-12-01T00:00:00Z" \
  --target '...' \
  --region us-east-1
```

## Target input (constant JSON)

The `Input` field in the target configuration passes a fixed JSON
payload to the target on every invocation.

```bash
--target '{
  "RoleArn": "...",
  "Arn": "...",
  "Input": "{\"environment\": \"production\", \"region\": \"us-east-1\"}"
}'
```

**Rules:**
- The Input MUST be valid JSON (escaped string in CLI)
- The Input is passed verbatim — the target receives exactly this JSON
- Invalid JSON causes invocation failure (not schedule creation failure)
- The Input is the same on every invocation (constant — not dynamic)

**For dynamic input:** if you need different data per invocation, use
a Lambda target that fetches the data before processing. The Scheduler
itself does not support templated or dynamic inputs.

## Terraform examples

```hcl
# Rate schedule with OFF window
resource "aws_scheduler_schedule" "hourly" {
  name       = "hourly-report"
  group_name = aws_scheduler_schedule_group.prod.name

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "rate(1 hour)"

  target {
    arn      = aws_lambda_function.report.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ report_type = "hourly", env = "prod" })
  }
}

# Cron schedule with timezone and MAXIMUM window
resource "aws_scheduler_schedule" "weekday_etl" {
  name                         = "weekday-etl"
  group_name                   = aws_scheduler_schedule_group.prod.name
  schedule_expression          = "cron(0 9 ? * MON-FRI *)"
  schedule_expression_timezone = "America/New_York"

  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 15
  }

  target {
    arn      = aws_sfn_state_machine.etl.arn
    role_arn = aws_iam_role.scheduler.arn

    retry_policy {
      maximum_retry_attempts = 3
      maximum_event_age_in_seconds = 3600
    }

    dead_letter_config {
      arn = aws_sqs_queue.scheduler_dlq.arn
    }
  }
}

# Schedule group
resource "aws_scheduler_schedule_group" "prod" {
  name = "prod-schedules"
}
```
