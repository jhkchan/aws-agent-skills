# Eval prompt: overprovisioned-postgres-rightsize-ri

Optimise the RDS database configuration for cost. Walk the seven-dimension
analysis (idle detection, right-sizing, pricing model, Multi-AZ, storage,
engine, Aurora ACU) and emit the standard optimisation block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

DBInstanceIdentifier: db-overprovisioned-postgres-rightsize-ri
Engine: postgres (PostgreSQL 15.4)
DBInstanceClass: db.r6i.2xlarge (8 vCPU, 64 GB RAM)
Region: us-east-1
Multi-AZ: true
Storage: 500 GB gp3
License model: postgresql-license (open-source)
Pricing: On-Demand (no RI/Savings Plan)

CloudWatch metrics (last 30 days):
  - CPUUtilization: avg=12%, max=25%
  - FreeableMemory: avg=28 GB (of 64 GB total), stable
  - DatabaseConnections: avg=15, max=30

Performance Insights:
  - DBLoad: avg=2, max=8 (low for 8 vCPUs)
  - Top SQL: evenly distributed, no single dominant query

Workload context: production OLTP database for an e-commerce platform.
Steady-state 24/7 with moderate peak during business hours.
