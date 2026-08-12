# Baseline (no-skill) — sns-one-time-schedule

> This is the response a model produces **without** the skill
> definition. It creates the schedule but misses the one-time
> schedule syntax (at() expression), the auto-delete-after-
> completion feature, the retry policy configuration, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the schedule:

```bash
aws scheduler create-schedule \
  --name campaign-launch \
  --schedule-expression "cron(0 14 1 9 ? 2026)" \
  --target '{"Arn": "arn:aws:sns:us-east-1:123456789012:marketing-alerts"}' \
  --region us-east-1
```

That should work for a one-time trigger.
