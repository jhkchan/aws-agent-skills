# Eval: dashboard-provisioning

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — API key creation (ADMIN, 86400s TTL), 3 dashboards imported via Grafana API, data source UID verification

## Prompt

Provision dashboards in existing Grafana workspace g-aaaa1111
in us-east-1. The workspace is ACTIVE with CloudWatch and
Prometheus data sources already configured. Create a workspace
API key named ci-cd-provisioning with ADMIN role and 86400 second
TTL. Import 3 dashboards from JSON files: overview.json,
metrics.json, logs.json. Ensure data source UIDs in dashboard
JSON match the workspace data source UIDs.
