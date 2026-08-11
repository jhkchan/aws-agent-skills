# Eval prompt: already-optimal-graviton-rn-rightsized

Optimise the ElastiCache replication group cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Replication Group: prod-cache-rg (case already-optimal-graviton-rn-rightsized)
Engine: redis (7.2)
Region: us-east-1
NodeType: cache.r7g.large (2 vCPU, 6.67 GB) — $0.153/h
Shards: 3 (cluster mode enabled)
ReplicasPerShard: 1 (total 6 nodes)
Persistence: RDB snapshots (1-day retention)
Pricing: 1-yr No Upfront Reserved Node (all 6 nodes covered)
Dataset size: 8 GB total (~2.7 GB per shard, 40% of node memory)
CloudWatch (last 30 days):
  - CPUUtilization: avg=38%, max=55%
  - EngineCPUUtilization: avg=35%, max=50%
  - CurrConnections: avg=400, max=600
Reserved Nodes held:
  - cache.r7g.large redis 1-yr No Upfront x 6
AOF: disabled
