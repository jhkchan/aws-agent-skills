# Eval prompt: graviton-node-migration

Optimise the ElastiCache replication group cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Replication Group: orders-cache-rg (case graviton-node-migration)
Engine: redis (7.0)
Region: us-east-1
NodeType: cache.m5.2xlarge (8 vCPU, 26.36 GB) — $0.904/h
Shards: 3 (cluster mode enabled)
ReplicasPerShard: 1 (total 6 nodes)
Persistence: RDB snapshots (daily)
Pricing: On-Demand (no Reserved Node)
CloudWatch (last 30 days):
  - CPUUtilization: avg=35%, max=55%
  - EngineCPUUtilization: avg=28%, max=45%
  - CurrConnections: avg=500, max=800
Cost Explorer (last 30 days):
  - ElastiCache:NodeUsage: cache.m5.2xlarge x 6 nodes
