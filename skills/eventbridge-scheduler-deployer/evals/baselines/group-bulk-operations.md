# Baseline (no-skill) — group-bulk-operations

> This is the response a model produces **without** the skill
> definition. It creates the schedules but misses the schedule group
> concept (bulk enable/disable capability), the flexible time window
> MAXIMUM setting for cost optimization, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the schedules:

```bash
aws scheduler create-schedule \
  --name daily-cleanup \
  --schedule-expression "rate(1 day)" \
  --target '{"Arn": "arn:aws:lambda:us-east-1:123456789012:function:cleanup-function"}' \
  --region us-east-1

aws scheduler create-schedule \
  --name weekly-audit \
  --schedule-expression "cron(0 0 ? * SUN *)" \
  --target '{"Arn": "arn:aws:lambda:us-east-1:123456789012:function:audit-function"}' \
  --region us-east-1
```

Two schedules created.
