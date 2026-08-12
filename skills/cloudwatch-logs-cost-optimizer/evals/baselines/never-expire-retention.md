# Baseline (no-skill) response: never-expire-retention

This file captures what a generic assistant produces WITHOUT the
cloudwatch-logs-cost-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, storage accumulation
math, retention tier selection, CONFIRM gate, deletion warning).

---

Your CloudWatch Logs group `/aws/lambda/never-expire-retention` has
no retention policy set (Never expire) and has accumulated over 10,000
GB of logs. That's a lot of storage cost — at $0.03/GB/month, you're
paying around $300/month just for storage.

You should set a retention policy. 30 days is probably fine for
application logs. You can do this with:

```
aws logs put-retention-policy --log-group-name /aws/lambda/never-expire-retention --retention-in-days 30
```

This will delete logs older than 30 days, which should cut your storage
cost significantly.
