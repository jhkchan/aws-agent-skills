# Baseline (no-skill) response: eventbridge-auto-retention

This file captures what a generic assistant produces WITHOUT the
log-retention-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, tier validation,
EventBridge automation, Firehose archival, cost estimation, expert
CloudWatch Logs knowledge).

---

You can use EventBridge to trigger a Lambda when a new log group
is created. Set up a rule on CreateLogGroup and point it at a
Lambda that calls put-retention-policy.

Something like:

```
aws events put-rule --name log-retention --event-pattern '...'
aws events put-targets --rule log-retention --targets ...
```

The Lambda just needs to extract the log group name and set the
retention. You'll also want to handle the existing 120 Never
Expire groups by running a one-time script.

Don't forget to add a DLQ in case the Lambda fails.
