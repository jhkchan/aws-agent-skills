# Eval: per-query-error-slack

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — per-query monitor, error count aggregation, threshold trigger severity 1, Slack destination, every 5 minutes

## Prompt

Create an OpenSearch alerting monitor named error-count-monitor
on the cluster at https://search-prod.example.com. Monitor type
per-query. Target index application-logs-*. Query: match
level=error, range @timestamp >= now-5m, aggregate value_count.
Trigger when error_count > 100, severity 1. Action: notify
Slack destination ops-alerts-slack (already configured).
Schedule every 5 minutes. Tags: Environment=production,
Team=ops.
