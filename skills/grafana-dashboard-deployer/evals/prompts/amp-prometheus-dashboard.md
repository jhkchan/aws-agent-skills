# Eval: amp-prometheus-dashboard

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — AMP workspace verified ACTIVE, PromQL dashboard with alerting

## Prompt

Create an Amazon Managed Grafana workspace in us-east-1 for application
monitoring. Workspace name "app-monitoring". IAM Identity Center auth.
Permission type CUSTOMER_MANAGED. Data source: AMP/Prometheus. The AMP
workspace "prod-metrics" (workspace ID ws-abc123def) is already ACTIVE.
Customer-managed IAM role "GrafanaDataSourceRole" with aps:QueryMetrics
on the AMP workspace ARN. Grafana version 10.4. Dashboard with service-
level metrics (request rate, error rate, latency p99) using PromQL queries
against the AMP workspace. Alert on error rate > 1% with SNS notification.
Tags: Environment=production, Workload=app-monitoring.
Account ID: 123456789012.
