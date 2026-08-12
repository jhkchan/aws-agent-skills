# Eval prompt: schedule-cron-syntax

Diagnose the EventBridge schedule rule failure for the following rule.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: schedule-based rule `ev-schedule-cron-syntax` never fires at
the expected time (09:00 UTC daily). `describe-rule` shows
`State: DISABLED`.

```text
EventBusName: default
RuleName: ev-schedule-cron-syntax
ScheduleExpression: "cron(0 9 * * *)"
EventPattern: (none — schedule-based rule)
State: DISABLED

Target Lambda: fn-ev-schedule-cron (same account, has
  events.amazonaws.com principal with SourceArn matching the rule ARN).
```

The rule has no EventPattern (it is schedule-based). The
ScheduleExpression uses a cron expression. Count the number of fields
in the cron expression and compare against the EventBridge cron
requirement.
