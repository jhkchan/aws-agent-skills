# Baseline (no-skill) — stepfunctions-cron-schedule

> This is the response a model produces **without** the skill
> definition. It creates the schedule but misses the timezone
> specification (--schedule-expression-timezone), the DLQ
> configuration (DeadLetterConfig in target), the retry policy
> (RetryPolicy in target), and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the schedule:

```bash
aws scheduler create-schedule \
  --name weekday-etl \
  --schedule-expression "cron(0 9 ? * MON-FRI *)" \
  --target '{"Arn": "arn:aws:states:us-east-1:123456789012:stateMachine:etl-pipeline"}' \
  --region us-east-1
```

Set up retry and DLQ separately if needed.
