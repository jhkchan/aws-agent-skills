# Eval prompt: writer-reader-rightsize-mirrored-replicas

Optimise the Aurora cluster cost. Walk the seven-dimension optimisation
logic and emit the standard optimisation block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: orders-prod-cluster
  (case writer-reader-rightsize-mirrored-replicas)
Engine: aurora-mysql (8.0)
Region: us-east-1
Instances:
  - writer: db.r6g.2xlarge (8 vCPU, 64 GB) — $1.16/h
  - reader-1: db.r6g.2xlarge — $1.16/h
  - reader-2: db.r6g.2xlarge — $1.16/h
CloudWatch (last 30 days):
  - writer CPUUtilization: avg=15%, max=28%
  - reader-1 CPUUtilization: avg=8%, max=18%
  - reader-2 CPUUtilization: avg=7%, max=15%
Performance Insights:
  - writer DBLoad: avg=1.2, max=4.5 (low for 8 vCPU)
Storage tier: Standard, 200 GB used
Pricing: On-Demand
