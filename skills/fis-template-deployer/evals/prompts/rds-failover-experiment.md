# Eval: rds-failover-experiment

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — aws:rds:failover-db-cluster action on aurora-prod-cluster by ARN, IAM role scoped to rds:FailoverDBCluster on the target cluster ARN, CloudWatch RDS-lag alarm stop condition

## Prompt

Create a FIS experiment template in us-east-1 account
123456789012. Action: aws:rds:failover-db-cluster. Target: RDS
DB cluster aurora-prod-cluster (ARN
arn:aws:rds:us-east-1:123456789012:cluster:aurora-prod-cluster),
selectionMode COUNT(1). Stop condition: CloudWatch alarm
FIS-RDS-Lag-High (ARN
arn:aws:cloudwatch:us-east-1:123456789012:alarm:FIS-RDS-Lag-High).
IAM role FISRDSRole with rds:FailoverDBCluster and
rds:DescribeDBClusters scoped to the target cluster ARN. Log
group /aws/fis/rds-failover. Tags: Environment=staging,
ExperimentType=RDS-Failover.
