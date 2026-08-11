# Eval prompt: ondemand-steady-state-rn-candidate

Optimise the ElastiCache replication group cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Replication Group: billing-cache-rg (case ondemand-steady-state-rn-candidate)
Engine: redis (7.0)
Region: us-east-1
NodeType: cache.r6g.2xlarge (8 vCPU, 26.36 GB)
Shards: 2 (cluster mode enabled)
ReplicasPerShard: 1 (total 4 nodes)
Persistence: RDB snapshots (daily)
Pricing: On-Demand (no Reserved Node)
Cluster uptime: 12 months steady
CloudWatch (last 30 days):
  - CPUUtilization: avg=40%, max=60%
  - EngineCPUUtilization: avg=32%, max=50%
  - CurrConnections: avg=300, max=450
describe-reserved-cache-nodes: empty (no RN held)
Migration plans: none (mission-critical, long-term)
