# Eval prompt: serverless-candidate-variable-load

Optimise the ElastiCache replication group cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Replication Group: feature-flags-cache (case serverless-candidate-variable-load)
Engine: redis (7.0)
Region: us-east-1
NodeType: cache.r6g.large (2 vCPU, 6.05 GB) — $0.167/h
Shards: 1 (non-cluster mode)
ReplicasPerShard: 1 (total 2 nodes)
Persistence: none (ephemeral)
Pricing: On-Demand
Dataset size: 3 GB
CloudWatch (last 30 days):
  - CPUUtilization: avg=8%, max=35% (daytime spikes only)
  - EngineCPUUtilization: avg=5%, max=25%
  - CurrConnections: avg=20, max=100 (overnight drops to <5)
  - Overnight idle: 8 hours/day at near-zero load
Cost Explorer:
  - ElastiCache:NodeUsage: cache.r6g.large x 2 nodes = ~$244/month
