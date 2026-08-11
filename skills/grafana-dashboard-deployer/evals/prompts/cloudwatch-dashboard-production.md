# Eval: cloudwatch-dashboard-production

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — CloudWatch data source, customer-managed IAM role, IAM Identity Center auth, dashboard with templating, alerting

## Prompt

Create an Amazon Managed Grafana workspace in us-east-1 for production
observability. Workspace name "prod-observability". Use IAM Identity
Center (AWS_SSO) authentication. Permission type CUSTOMER_MANAGED with
a role "GrafanaDataSourceRole" that has CloudWatch read access
(cloudwatch:GetMetricData, cloudwatch:ListMetrics, logs:DescribeLogGroups).
Data source: CloudWatch for regions us-east-1 and us-west-2. Grafana
version 10.4. Dashboard with 12 panels covering EC2, Lambda, and RDS
metrics with templating variables for $region and $datasource. Alert
rules for CPU > 85% and Lambda errors > 5 with SNS notification to
arn:aws:sns:us-east-1:123456789012:grafana-alerts. Tags:
Environment=production, Workload=observability. Account ID: 123456789012.
