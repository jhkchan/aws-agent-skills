# Eval prompt: rebalance-storm-no-static-membership

Diagnose the MSK consumer lag for the following cluster and topic. Walk
the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: consumer group `cg-order-processor` on topic `orders` shows a
sawtooth lag pattern. RecordsLagMax spikes every ~3-5 minutes, then
drops, then spikes again. The group is never stable long enough to
drain the backlog. Consumer logs show frequent "Member ... sending
JoinGroup request" entries.

```text
ClusterArn: arn:aws:kafka:us-east-1:111111111111:cluster/prod-msk/mno-345
ClusterType: PROVISIONED (3 brokers, kafka.m5.xlarge)
Topic: orders
Partitions: 24
ConsumerGroup: cg-order-processor
ConsumerGroupMembers: 24 (one consumer per partition)
ConsumerGroupState: oscillating between STABLE and PREPARING_REBALANCE

CloudWatch metrics (last hour):
  - RecordsLagMax: sawtooth pattern, peaks at 200000, valleys at 5000
  - BytesInPerSec: 8 MB/s (flat, no producer burst)
  - BytesOutPerSec: sawtooth (drops to near-zero during rebalance)
  - UnderReplicatedPartitions: 0
  - CpuUser: < 40% on all brokers

Per-partition lag:
  Lag is distributed across all 24 partitions (not skewed)
  All partitions spike during rebalance, then drain when STABLE

Consumer config:
  - session.timeout.ms: 45000 (default)
  - heartbeat.interval.ms: 3000 (default)
  - max.poll.interval.ms: 300000 (default 5 min)
  - group.instance.id: NOT SET (no static membership)
  - partition.assignment.strategy: RangeAssignor (default, stop-the-world)

Deployment context:
  - Rolling deployment of consumer pods every ~5 minutes during
    a canary rollout
  - Each pod restart triggers a full group rebalance (no static
    membership)

Producer context:
  - acks: all
  - Producer rate is steady (no burst)
```

The lag pattern is a sawtooth that correlates with rebalance events,
not with producer rate or consumer processing time. Each rebalance
pauses consumption for the entire group during the stop-the-world phase.
