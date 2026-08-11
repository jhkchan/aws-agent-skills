# Eval prompt: graviton-broker-migration

Optimise the Amazon MSK cluster cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: events-prod-msk (case graviton-broker-migration)
Kafka Version: 3.5.1
Region: us-east-1
Broker Type: kafka.m5.large (2 vCPU, 8 GB) — $0.276/h
Broker Count: 3
EBS Volume: 1 TB gp3 per broker
Partitions: 60 across 10 topics
Log Retention: 72 hours (3 days)
Compacted Topics: none
Pricing: On-Demand
CloudWatch (last 30 days):
  - BytesInPerSec per broker: avg=12, max=20
  - BytesOutPerSec per broker: avg=25, max=40
  - KafkaDataLogsDiskUsed: avg=45%, max=55%
  - CpuUser: avg=30%, max=45%
  - MaxOffsetLag: avg=500 (low consumer lag)
Cost Explorer (last 30 days):
  - MSK:BrokerUsage: kafka.m5.large x 3 brokers
