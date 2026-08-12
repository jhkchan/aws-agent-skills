# Eval: lambda-rate-schedule

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — rate(1 hour), Lambda target, flexible time window OFF (exact-time), constant JSON input, Scheduler-managed IAM role

## Prompt

Create an EventBridge Scheduler schedule called hourly-report
that invokes Lambda function report-generator
(arn:aws:lambda:us-east-1:123456789012:function:report-generator)
every 1 hour. Flexible time window OFF (exact-time invocation).
Pass constant JSON input: {"report_type": "hourly", "env":
"prod"}. Schedule group: prod-schedules. Tags: Environment=
production, Team=data.
