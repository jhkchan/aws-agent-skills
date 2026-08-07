# Eval prompt: already-optimal-prod-postgres-ri

Optimise the RDS database configuration for cost. Walk the seven-dimension
analysis and emit the standard optimisation block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DBInstanceIdentifier: db-already-optimal-prod-postgres-ri
Engine: postgres (PostgreSQL 15.4)
DBInstanceClass: db.r6g.2xlarge (8 vCPU, 64 GB RAM, Graviton3)
Region: us-east-1
Multi-AZ: true
Storage: 1 TB gp3 (used: 800 GB)
Pricing: 3-year Standard Reserved Instance (No Upfront), active

CloudWatch metrics (last 30 days):
  - CPUUtilization: avg=55%, max=70%
  - FreeableMemory: avg=26 GB (of 64 GB), stable
  - DatabaseConnections: avg=120, max=200

Performance Insights:
  - DBLoad: avg=4, max=12 (healthy for 8 vCPUs)
  - Top SQL: well-distributed, no single dominant query

Workload context: production OLTP database for a SaaS platform.
Steady-state 24/7.
