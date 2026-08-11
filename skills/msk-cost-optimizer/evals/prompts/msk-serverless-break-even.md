# Eval prompt: msk-serverless-break-even

Optimise the Amazon MSK cluster cost. Walk the seven-dimension
optimisation logic and emit the standard optimisation block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

Cluster: notifications-msk-dev (case msk-serverless-break-even)
Kafka Version: 3.5.1
Region: us-east-1
Broker Type: kafka.m5.large (2 vCPU, 8 GB) — $0.276/h
Broker Count: 3
EBS Volume: 100 GB gp3 per broker
Partitions: 20 across 5 topics
Log Retention: 24 hours
Compacted Topics: none
Pricing: On-Demand
Total BytesInPerSec: avg=10 MB/s, max=15 (overnight drops to <1)
Data stored: ~5 GB total
Consumer lag: low (MaxOffsetLag avg <100)
Cost Explorer:
  - MSK:BrokerUsage: kafka.m5.large x 3 brokers = ~$604/month
  - MSK:EBSUsage: 300 GB x $0.08 = ~$24/month
