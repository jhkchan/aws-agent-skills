# Eval prompt: consumer-fetch-microbatch-stall

Diagnose the MSK consumer lag for the following cluster and topic. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: consumer group `cg-user-svc` on topic `user-events` shows
RecordsLagMax climbing steadily. The consumer is NOT CPU-bound (CPU <
10%); downstream DB writes are fast (< 2ms). The lag appears to be
artificial — the consumer is waiting between polls.

```text
ClusterArn: arn:aws:kafka:us-east-1:111111111111:cluster/dev-msk/ghi-789
ClusterType: PROVISIONED (3 brokers, kafka.t3.small)
Topic: user-events
Partitions: 6
ConsumerGroup: cg-user-svc
ConsumerGroupMembers: 6
ConsumerGroupState: STABLE

CloudWatch metrics (last hour):
  - RecordsLagMax: 500 → 45000 (climbing)
  - BytesInPerSec: 0.1 MB/s (~100 KB/s)
  - BytesOutPerSec: 0.05 MB/s
  - UnderReplicatedPartitions: 0
  - CpuUser: < 20% on all brokers

Per-partition lag:
  All 6 partitions show similar lag (~7000-8000 each)
  Distribution is even — no skew

Consumer config:
  - fetch.min.bytes: 10485760 (10 MB)
  - fetch.max.wait.ms: 500
  - max.poll.records: 500

Consumer processing:
  - CPU utilization: < 10%
  - Downstream DB write latency: < 2ms
  - Records per poll: ~50 (waiting full 500ms each time)
```

The consumer is not CPU-bound and downstream is fast. The lag is
artificial — caused by the fetch configuration introducing latency on
each poll cycle.
