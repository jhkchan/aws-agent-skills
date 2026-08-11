# Baseline (no-skill) response: cur-athena-top-spenders-scheduled

This file captures what a generic assistant produces WITHOUT the
cost-anomaly-response-automator skill loaded.

---

You can write an Athena query like:

```sql
SELECT * FROM cur_table ORDER BY cost DESC LIMIT 20
```

Schedule it with EventBridge and have a Lambda post the result to
Slack. That should work.
