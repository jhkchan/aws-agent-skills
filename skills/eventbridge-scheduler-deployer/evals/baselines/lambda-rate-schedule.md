# Baseline (no-skill) — lambda-rate-schedule

> This is the response a model produces **without** the skill
> definition. It creates the schedule but misses the flexible time
> window trade-off (OFF = exact-time vs MAXIMUM = cost batching),
> the Scheduler-managed IAM role concept (tries to pre-create a role),
> the constant JSON input field, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the schedule:

```bash
aws scheduler create-schedule \
  --name hourly-report \
  --schedule-expression "rate(1 hour)" \
  --target '{"Arn": "arn:aws:lambda:us-east-1:123456789012:function:report-generator"}' \
  --region us-east-1
```

You might need to create a role first.
