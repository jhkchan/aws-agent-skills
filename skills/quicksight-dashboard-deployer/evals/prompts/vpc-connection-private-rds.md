# Eval: vpc-connection-private-rds

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Enterprise edition, VPC connection for private RDS PostgreSQL, IAM role for ENI management, SPICE dataset with daily refresh

## Prompt

Create a QuickSight dashboard in us-east-1, aws-account-id
123456789012, Enterprise edition. Data source: private RDS
PostgreSQL at prod-db.cluster-abc123.us-east-1.rds.amazonaws.com
port 5432, database "analytics". VPC connection using subnets
subnet-aaa111, subnet-bbb222 and security group sg-quicksight.
IAM role arn:aws:iam::123456789012:role/QuickSightVpcRole.
Dataset "ops_metrics" with SPICE mode, daily refresh.
Tags: Environment=production.
