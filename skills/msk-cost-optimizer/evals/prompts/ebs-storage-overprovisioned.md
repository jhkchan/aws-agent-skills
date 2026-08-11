# Eval prompt: ebs-storage-overprovisioned

Optimise the Amazon MSK cluster cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: logs-msk-prod (case ebs-storage-overprovisioned)
Kafka Version: 3.5.1
Region: us-east-1
Broker Type: kafka.m7g.large (2 vCPU, 8 GB) — $0.220/h
Broker Count: 3
EBS Volume: 2 TB gp3 per broker ($0.08/GB-month)
Partitions: 45 across 8 topics
Log Retention: 24 hours
Compacted Topics: none
Pricing: On-Demand
CloudWatch (last 30 days):
  - BytesInPerSec per broker: avg=8, max=15
  - KafkaDataLogsDiskUsed: avg=20%, max=25%
  - CpuUser: avg=25%, max=35%
Disk usage per broker: ~410 GB used of 2,000 GB allocated
