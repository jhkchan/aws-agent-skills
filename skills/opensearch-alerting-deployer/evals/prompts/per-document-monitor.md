# Eval: per-document-monitor

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — per-document monitor, error log per-row alerting, custom webhook destination, every 10 minutes

## Prompt

Create an OpenSearch per-document monitor named
per-user-error-monitor on cluster
https://search-prod.example.com. Target index
application-logs-*. Query: match level=error, range
@timestamp >= now-5m. Each matching document should trigger
a custom webhook notification to destination
per-user-webhook (already configured). Schedule every 10
minutes. Tags: Environment=production, Type=per-doc.
