# Eval: cloudwatch-data-source

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CloudWatch data source, AWS_SSO auth, workspace IAM role with cloudwatch:GetMetricData + logs:StartQuery, SERVICE_MANAGED permissions

## Prompt

Create a Managed Grafana workspace named prod-observability
in us-east-1, account 123456789012. Use IAM Identity Center
authentication with SERVICE_MANAGED permissions. Data source:
CloudWatch (default region us-east-1). Workspace IAM role
GrafanaWorkspaceRole with CloudWatch metrics and logs read
permissions. Tags: Environment=production, Team=ops.
