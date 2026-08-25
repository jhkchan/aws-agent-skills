# EventBridge Scheduler Deployer — command listings (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Step 1 — rate/cron create-schedule commands (moved from SKILL.md)

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

## Step 2 — flexible time window commands (moved from SKILL.md)

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

## Step 3 — target configuration examples (moved from SKILL.md)

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

## Step 4 — one-time schedule commands (moved from SKILL.md)

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

## Step 5 — timezone specification command (moved from SKILL.md)

```bash
aws scheduler create-schedule \
  --name ny-business-hours \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --schedule-expression-timezone "America/New_York" \
  --flexible-time-window '{"Mode": "OFF"}' \
  --target '...' \
  --region us-east-1
```

## Step 6 — schedule group commands (moved from SKILL.md)

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

## Step 7 — retry policy and DLQ command (moved from SKILL.md)

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

## Step 8 — start/end date window command (moved from SKILL.md)

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

## Step 9 — constant JSON input command (moved from SKILL.md)

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

## Step 10 — enable/disable state commands (moved from SKILL.md)

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

## Step 11 — CloudWatch metrics command (moved from SKILL.md)

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
