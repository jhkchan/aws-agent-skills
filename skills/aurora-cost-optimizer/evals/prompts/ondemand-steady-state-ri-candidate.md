# Eval prompt: ondemand-steady-state-ri-candidate

Optimise the Aurora cluster cost. Walk the seven-dimension optimisation
logic and emit the standard optimisation block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: billing-prod-cluster (case ondemand-steady-state-ri-candidate)
Engine: aurora-postgresql (15)
Region: us-east-1
Instances:
  - writer: db.r6g.2xlarge — On-Demand
  - reader-1: db.r6g.2xlarge — On-Demand
Cluster uptime: 14 months steady
CloudWatch (last 30 days):
  - writer CPUUtilization: avg=42%, max=65% (no downsize candidate)
  - reader-1 CPUUtilization: avg=35%, max=55%
describe-reserved-db-instances: empty (no RI held)
Migration plans: none (mission-critical, long-term)
