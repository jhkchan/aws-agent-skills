# Baseline (no-skill) response: scheduled-step-functions-deploy

This file captures what a generic assistant produces WITHOUT the
eventbridge-rule-deployer skill loaded.

---

To run a Step Functions state machine nightly, create a scheduled
EventBridge rule with a cron expression. Use `cron(0 2 * * *)` for
02:00 UTC daily. Then add the Step Functions state machine as a
target.

```
aws events put-rule --name nightly --schedule-expression 'cron(0 2 * * *)'
aws events put-targets --rule nightly --targets '[{"Arn":"<state-machine-arn>","Id":"sfn"}]'
```

You may want to set up a DLQ in case the workflow fails.
