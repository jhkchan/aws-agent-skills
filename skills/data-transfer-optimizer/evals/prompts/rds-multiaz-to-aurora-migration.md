# Eval prompt: rds-multiaz-to-aurora-migration

Optimize the AWS account data transfer costs. Walk the seven-dimension
optimization logic and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Account: 123456789015 (case rds-multiaz-to-aurora-migration)
Region: us-east-1
Monthly data transfer costs (Cost Explorer, last 30 days):
  - RDS-DataTransfer: 5,000 GB × $0.01 = $50
    (Multi-AZ synchronous replication)
  - Other data transfer costs: minimal
RDS inventory:
  - db.r6i.2xlarge Multi-AZ, PostgreSQL 15
  - 5TB write volume per month (high-write OLTP workload)
  - 3 read replicas (consumers in same region)
Workload context: e-commerce OLTP with strict ACID requirements.
Multi-AZ for HA. Read replicas for read scaling.
