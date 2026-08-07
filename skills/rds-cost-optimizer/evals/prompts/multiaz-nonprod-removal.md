# Eval prompt: multiaz-nonprod-removal

Optimise the RDS database configuration for cost. Walk the seven-dimension
analysis and emit the standard optimisation block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DBInstanceIdentifier: db-multiaz-nonprod-removal
Engine: postgres (PostgreSQL 15.4)
DBInstanceClass: db.m6i.xlarge (4 vCPU, 16 GB RAM)
Region: us-east-1
Multi-AZ: true
Storage: 200 GB gp3
Pricing: On-Demand

CloudWatch metrics (last 30 days):
  - CPUUtilization: avg=35%, max=55%
  - FreeableMemory: avg=10 GB (of 16 GB)
  - DatabaseConnections: avg=25, max=50

Workload context: staging database for QA testing. Runs during business
hours only. No HA requirement — QA accepts downtime.
