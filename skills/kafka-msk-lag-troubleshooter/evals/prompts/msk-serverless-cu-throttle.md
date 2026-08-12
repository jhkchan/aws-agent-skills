# Eval prompt: msk-serverless-cu-throttle

Diagnose the MSK consumer lag for the following cluster and topic. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: consumer group `cg-iot-processor` on topic `sensor-data` shows
RecordsLagMax climbing on partition 2 only. MSK Serverless cluster; the
Throttle metric shows sustained throttling on partition 2. Other
partitions are near-zero lag.

```text
ClusterArn: arn:aws:kafka:us-east-1:111111111111:cluster/serverless-msk/jkl-012
ClusterType: SERVERLESS
Topic: sensor-data
Partitions: 4
ConsumerGroup: cg-iot-processor
ConsumerGroupMembers: 4
ConsumerGroupState: STABLE

CloudWatch metrics (last hour, AWS/Kafka namespace):
  - RecordsLagMax: 1000 → 500000
  - Throttle (Sum): sustained 50+ per 5-min period
  - ConsumedReadThroughput: at partition-level CU cap on partition 2
  - BytesInPerSec: flat at 2 MB/s (cluster aggregate)
  - UnderReplicatedPartitions: 0 (Serverless uses KRaft)
  - (No CpuUser or disk metrics — Serverless manages these)

Per-partition lag:
  Partition 0: LAG 15
  Partition 1: LAG 8
  Partition 2: LAG 500000
  Partition 3: LAG 12

Per-partition throughput:
  Partition 2: 1.4 MB/s (70% of traffic)
  Others: 0.2 MB/s each

Producer context:
  - Keyed by device-id; one device model dominates traffic
  - Hash routes to partition 2

Consumer config:
  - fetch.min.bytes: 1 (default)
  - fetch.max.wait.ms: 500 (default)
```

MSK Serverless throttles per-partition on CU (Capacity Units), not at
the cluster level. A single hot partition hitting its CU cap is
throttled even when the cluster has spare capacity.
