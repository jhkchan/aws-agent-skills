# Eval: cross-account-anomaly

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — central monitoring account 111111111111 creates detector on source account 222222222222 RDS metric, resource policy for sharing noted, detector and alarm in monitoring account

## Prompt

Create a cross-account CloudWatch Anomaly Detection model. The
monitoring account is 111111111111, the source account is
222222222222. The metric is AWS/RDS DatabaseConnections for
DBInstanceIdentifier prod-db-001 in us-east-1. The metric has
been reporting for 60 days. Stat Average, period 300. Std dev 3.
The source account has a resource policy allowing the monitoring
account to read metrics. Create a band-breach alarm in the
monitoring account with SNS
arn:aws:sns:us-east-1:111111111111:central-alerts.
