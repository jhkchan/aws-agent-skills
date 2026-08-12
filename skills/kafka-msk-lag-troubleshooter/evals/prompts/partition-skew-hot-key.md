# Eval prompt: partition-skew-hot-key

Diagnose the MSK consumer lag for the following cluster and topic. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: consumer group `cg-payments-processor` on topic `tx-events`
shows RecordsLagMax climbing from 10K to 8M over 4 hours. The payments
pipeline is falling behind; downstream alerting fired at the 8M lag
threshold.

```text
ClusterArn: arn:aws:kafka:us-east-1:111111111111:cluster/prod-msk/abc-123
ClusterType: PROVISIONED (3 brokers, kafka.m5.xlarge)
Topic: tx-events
Partitions: 12
ReplicationFactor: 3
ConsumerGroup: cg-payments-processor
ConsumerGroupMembers: 12
ConsumerGroupState: STABLE

CloudWatch metrics (last 4 hours, AWS/Kafka namespace):
  - RecordsLagMax: 10000 → 8000000
  - BytesInPerSec (cluster): 12 MB/s (flat)
  - BytesOutPerSec (cluster): 5 MB/s (flat)
  - UnderReplicatedPartitions: 0
  - CpuUser (per broker): broker-1 35%, broker-2 38%, broker-3 33%
  - NetworkProcessorAvgIdlePercent: 0.65

Per-partition lag (kafka-consumer-groups --describe):
  Partition 0:  LAG 12
  Partition 1:  LAG 5
  Partition 2:  LAG 8
  Partition 3:  LAG 3
  Partition 4:  LAG 10
  Partition 5:  LAG 7
  Partition 6:  LAG 4
  Partition 7:  LAG 8000000
  Partition 8:  LAG 9
  Partition 9:  LAG 6
  Partition 10: LAG 11
  Partition 11: LAG 2

Per-partition throughput (client-side Micrometer, last 10 min):
  Partition 7:  9.6 MB/s
  All others:   0.1 - 0.3 MB/s each

Producer context:
  - Keyed by device-id (string key)
  - One device (device-abc123) generating a burst (80% of volume)
  - Default partitioner (hash of key modulo partitions)

Consumer config:
  - fetch.min.bytes: 1 (default)
  - fetch.max.wait.ms: 500 (default)
  - max.poll.records: 500 (default)
```

Distinguish uniform lag (rate problem) from single-partition lag (skew
problem). Adding consumers will not help because the skewed partition
is already assigned to one consumer and cannot be parallelised.
