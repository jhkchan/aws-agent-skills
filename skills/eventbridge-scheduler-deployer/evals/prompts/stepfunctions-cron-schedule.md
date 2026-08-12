# Eval: stepfunctions-cron-schedule

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — cron(0 9 ? * MON-FRI *), Step Functions target, America/New_York timezone, DLQ configured, retry max 3

## Prompt

Create an EventBridge Scheduler schedule called weekday-etl
that triggers Step Functions state machine etl-pipeline
(arn:aws:states:us-east-1:123456789012:stateMachine:etl-pipeline)
at 9 AM weekdays, US Eastern timezone. DLQ:
arn:aws:sqs:us-east-1:123456789012:scheduler-dlq. Retry: max 3
attempts, max event age 3600 seconds. Tags: Environment=
production, Team=data.
