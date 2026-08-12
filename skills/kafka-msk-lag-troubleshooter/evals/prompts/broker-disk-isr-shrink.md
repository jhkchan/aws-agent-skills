# Eval prompt: broker-disk-isr-shrink

Diagnose the MSK consumer lag for the following cluster and topic. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: consumer group `cg-event-processor` on topic `events` shows
RecordsLagMax climbing. Producer logs show intermittent
NOT_ENOUGH_REPLICAS (errorCode: 19). The consumer is healthy but
starved for data because the producer cannot write.

```text
ClusterArn: arn:aws:kafka:us-east-1:111111111111:cluster/prod-msk/def-456
ClusterType: PROVISIONED (3 brokers, kafka.m5.large, 1 TB EBS each)
Topic: events
Partitions: 30
ReplicationFactor: 3
min.insync.replicas: 2
ConsumerGroup: cg-event-processor

CloudWatch metrics (last 2 hours, AWS/Kafka namespace):
  - RecordsLagMax: 50000 → 1200000
  - UnderReplicatedPartitions: 0 → 14 (sustained for 90 min)
  - OfflinePartitions: 0
  - ISRShrink: 14 events at the start of the window
  - ISRExpand: 0
  - CpuUser: broker-1 40%, broker-2 82%, broker-3 38%
  - DiskKBWrttnPerSec (broker-2): near device limit
  - Disk usage (broker-2): 92%
  - Disk usage (broker-1): 55%
  - Disk usage (broker-3): 58%

Producer context:
  - acks: all
  - batch.size: 131072
  - compression.type: lz4

Consumer context:
  - Consumer is NOT CPU-bound (processing time < 5ms per record)
  - Consumer fetch config is default
```

The consumer lag is a side effect of the producer being unable to
write. With `acks=all` and `min.insync.replicas=2`, if ISR drops below
2 for a partition, the producer receives NOT_ENOUGH_REPLICAS.
