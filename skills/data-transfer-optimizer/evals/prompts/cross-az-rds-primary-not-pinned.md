# Eval prompt: cross-az-rds-primary-not-pinned

Optimize the AWS account data transfer costs. Walk the seven-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Account: 123456789013 (case cross-az-rds-primary-not-pinned)
Region: us-east-1
Monthly data transfer costs (Cost Explorer, last 30 days):
  - DataTransfer-Regional-Bytes: 8,000 GB × $0.02 = $160
  - NatGateway-Bytes: minimal ($20/month)
  - DataTransfer-Out-Bytes: minimal ($30/month)
VPC topology:
  - VPC-A in us-east-1 (3 AZs)
  - RDS for PostgreSQL primary in us-east-1a, standby in 1b
    (Multi-AZ non-Aurora)
  - Worker ASG spread across 1a, 1b, 1c (3 AZs)
  - VPC Endpoints: S3 Gateway Endpoint deployed
Workload context: workers read ~265GB/day from RDS primary; 2/3 of
workers are in different AZ from primary.
