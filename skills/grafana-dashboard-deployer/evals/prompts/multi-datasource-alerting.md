# Eval: multi-datasource-alerting

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — multi data source, 3-tier dashboard, alert rules + notification policies + contact points

## Prompt

Create an Amazon Managed Grafana workspace in us-east-1 for full-stack
observability. Workspace name "fullstack-obs". IAM Identity Center auth.
Permission type CUSTOMER_MANAGED. Data sources: CloudWatch (us-east-1),
AMP/Prometheus (workspace ws-metrics-xyz, ACTIVE), and X-Ray. IAM role
"GrafanaFullStackRole" with read permissions for all three data source
types. Grafana version 10.4. Dashboard with 3-tier layout: status
overview (stat panels), time-series trends (CPU, latency, throughput
from CloudWatch and AMP), detail tables (X-Ray trace summaries).
Alert rules: CPU > 85% (CloudWatch), error rate > 1% (AMP PromQL),
trace error rate > 5% (X-Ray). Notification policies routing by
severity: critical -> sns-critical, warning -> sns-warning. Contact
points: SNS arn:aws:sns:us-east-1:123456789012:grafana-critical and
arn:aws:sns:us-east-1:123456789012:grafana-warning. Tags:
Environment=production, Workload=fullstack-observability.
Account ID: 123456789012.
