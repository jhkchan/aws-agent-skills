# Eval prompt: node-rightsizing-low-engine-cpu

Optimise the ElastiCache replication group cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Replication Group: sessions-cache-rg (case node-rightsizing-low-engine-cpu)
Engine: redis (7.0)
Region: us-east-1
NodeType: cache.r6g.2xlarge (8 vCPU, 26.36 GB) — $0.664/h
Shards: 2 (cluster mode enabled)
ReplicasPerShard: 1 (total 4 nodes)
Persistence: RDB snapshots (daily)
Pricing: On-Demand
CloudWatch (last 30 days):
  - CPUUtilization: avg=10%, max=20%
  - EngineCPUUtilization: avg=8%, max=15%
  - CurrConnections: avg=80, max=150
  - FreeableMemory: avg=18 GB (of 26.36 GB)
Dataset size: ~6 GB total (3 GB per shard, fits in xlarge)
