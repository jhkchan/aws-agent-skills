# Eval: missing-workspace-role-permissions

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — workspace IAM role has cloudwatch:ListMetrics but is missing cloudwatch:GetMetricData, GetMetricStatistics, and logs:StartQuery

## Prompt

Create a Managed Grafana workspace named prod-grafana in
us-east-1 with CloudWatch data source. Use IAM Identity Center
authentication. Workspace IAM role GrafanaWorkspaceRole exists
but only has cloudwatch:ListMetrics — it is missing
cloudwatch:GetMetricData, cloudwatch:GetMetricStatistics, and
logs:StartQuery permissions.
