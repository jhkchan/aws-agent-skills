# Baseline (no-skill) response: subscription-filter-cleanup

This file captures what a generic assistant produces WITHOUT the
log-retention-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, tier validation,
EventBridge automation, Firehose archival, cost estimation, expert
CloudWatch Logs knowledge).

---

To change the retention on that log group, just use
put-retention-policy with 7 days. The metric filters should
keep working since they evaluate at ingestion time.

```
aws logs put-retention-policy --log-group-name /aws/lambda/legacy-processor --retention-in-days 7
```

You might want to delete the subscription filter to OpenSearch
if you're decommissioning it. The 800 GB will get cleaned up
when you set the shorter retention.

For the export, you can use create-export-task to send 30 days
to S3 first.
