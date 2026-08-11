# Eval: aurora-failover-dr-drill

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Aurora cluster AVAILABLE, alarm OK, role scoped

## Prompt

Provision an FIS experiment "aurora-failover-drill" in us-east-1.
Use aws:rds:failover-db-cluster against target cluster
arn:aws:rds:us-east-1:111111111111:cluster:api-prod-cluster
(cluster is AVAILABLE). Stop condition: alarm
"fis-stop-db-connections-dropped" (currently OK, role has
cloudwatch:DescribeAlarms). Log to CloudWatch Logs group
"/aws/fis/aurora-failover-drill". budgetDuration 5 minutes.
