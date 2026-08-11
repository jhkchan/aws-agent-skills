# Eval prompt: broker-count-overprovisioned

Optimise the Amazon MSK cluster cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: analytics-msk-dev (case broker-count-overprovisioned)
Kafka Version: 3.5.1
Region: us-east-1
Broker Type: kafka.m5.large (2 vCPU, 8 GB) — $0.276/h
Broker Count: 6
EBS Volume: 500 GB gp3 per broker
Partitions: 120 total (20 per broker)
Log Retention: 24 hours
Compacted Topics: none
Pricing: On-Demand
CloudWatch (last 30 days):
  - BytesInPerSec per broker: avg=2.5, max=5
  - Total BytesInPerSec: avg=15 MB/s
  - KafkaDataLogsDiskUsed: avg=30%, max=40%
  - CpuUser: avg=10%, max=20%
  - MaxOffsetLag: avg=200 (low consumer lag)
Partition-to-broker ratio: 20/broker (well under 400 ceiling)
