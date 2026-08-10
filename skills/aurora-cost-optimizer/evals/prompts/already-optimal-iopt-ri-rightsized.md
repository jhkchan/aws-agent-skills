# Eval prompt: already-optimal-iopt-ri-rightsized

Optimise the Aurora cluster cost. Walk the seven-dimension optimisation
logic and emit the standard optimisation block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: reporting-cluster-prod
  (case already-optimal-iopt-ri-rightsized)
Engine: aurora-postgresql (15)
Region: us-east-1
Storage tier: Aurora I/O-Optimized (aurora-iopt1)
Storage used: 800 GB
I/O requests (last 30 days): 750,000,000 (well above break-even)
Instances:
  - writer: db.r6g.xlarge — 1-yr No Upfront RI
  - reader-1: db.r6g.large — 1-yr No Upfront RI
  - reader-2 (analytics): db.r6g.xlarge — On-Demand (spiky)
CloudWatch (last 30 days):
  - writer CPUUtilization: avg=45%, max=60%
  - reader-1 CPUUtilization: avg=40%, max=55%
  - reader-2 CPUUtilization: avg=35%, max=80% (analytics spikes)
Performance Insights:
  - writer DBLoad: avg=2.0, top-SQL evenly distributed
  - No single SQL > 15% of DBLoad
Reserved Instances held:
  - db.r6g.xlarge aurora-postgresql 1-yr No Upfront (covers writer)
  - db.r6g.large aurora-postgresql 1-yr No Upfront (covers reader-1)
Global DB: not in use
Backtrack: disabled
