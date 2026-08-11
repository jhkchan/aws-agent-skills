# Eval prompt: already-optimal-graviton-compact-retention

Optimise the Amazon MSK cluster cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: analytics-msk-prod (case already-optimal-graviton-compact-retention)
Kafka Version: 3.5.1 (KRaft mode enabled)
Region: us-east-1
Broker Type: kafka.m7g.large (2 vCPU, 8 GB) — $0.220/h
Broker Count: 3
EBS Volume: 1 TB gp3 per broker
Partitions: 90 total (30 per broker)
Log Retention: 72 hours (3 days)
Compacted Topics: 3 changelog topics (cleanup.policy=compact)
Pricing: On-Demand
CloudWatch (last 30 days):
  - BytesInPerSec per broker: avg=18, max=28
  - BytesOutPerSec per broker: avg=35, max=50
  - KafkaDataLogsDiskUsed: avg=55%, max=65%
  - CpuUser: avg=40%, max=55%
  - MaxOffsetLag: avg=800 (healthy)
Partition-to-broker ratio: 30/broker (under 400 ceiling)
