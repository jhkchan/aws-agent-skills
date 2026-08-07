# Eval prompt: idle-database-deletion

Optimise the RDS database configuration for cost. Walk the seven-dimension
analysis and emit the standard optimisation block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DBInstanceIdentifier: db-idle-database-deletion
Engine: mysql (MySQL 8.0)
DBInstanceClass: db.m6i.large (2 vCPU, 8 GB RAM)
Region: us-east-1
Multi-AZ: false (Single-AZ)
Storage: 100 GB gp3
Pricing: On-Demand

CloudWatch metrics (last 30 days):
  - CPUUtilization: avg=0.2%, max=1% (near-zero)
  - FreeableMemory: avg=7.8 GB (of 8 GB) — no memory pressure
  - DatabaseConnections: avg=0, max=0 for ALL 30 days

Performance Insights:
  - DBLoad: 0 for entire 30-day window
  - No SQL statements recorded

Workload context: database was created for a feature that was deprecated
6 months ago. No application is configured to connect.
