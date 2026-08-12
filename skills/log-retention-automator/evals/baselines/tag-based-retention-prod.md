# Baseline (no-skill) response: tag-based-retention-prod

This file captures what a generic assistant produces WITHOUT the
log-retention-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, tier validation,
EventBridge automation, Firehose archival, cost estimation, expert
CloudWatch Logs knowledge).

---

You can set retention on your log groups using
put-retention-policy. Just loop through all 150 log groups and
set the retention based on the Environment tag.

```
aws logs put-retention-policy --log-group-name <name> --retention-in-days 90
```

For prod use 90, staging use 30, dev use 7. You might want to
automate this with a script. Make sure your IAM role has
permissions to call put-retention-policy.

You should also set up something to catch new log groups. Maybe
a CloudWatch Events rule or a Lambda that runs periodically.
