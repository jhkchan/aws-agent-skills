---
description: Diagnoses Amazon MSK consumer lag through a ten-category diagnostic tree (partition skew, ISR shrink, broker saturation, consumer fetch tuning, producer config, partition parallelism, MSK Connect lag, Serverless CU throttle, rebalance storm, ZooKeeper) — emits ROOT_CAUSE_IDENTIFIED with the specific failure layer or INSUFFICIENT_DATA.
nl_triggers:
  - "MSK consumer lag"
  - "Kafka RecordsLagMax"
  - "consumer group lag climbing"
  - "Kafka partition skew"
  - "hot key Kafka"
  - "under-replicated partitions MSK"
  - "ISR shrink Kafka"
  - "broker disk full MSK"
  - "broker CPU high Kafka"
  - "Kafka fetch.min.bytes"
  - "fetch.max.wait.ms"
  - "Kafka micro-batch"
  - "producer acks Kafka"
  - "batch.size producer"
  - "compression.type Kafka"
  - "partition count too low"
  - "consumer parallelism"
  - "MSK Connect lag"
  - "source connector lag"
  - "sink connector lag"
  - "MSK Serverless throttled"
  - "ConsumedReadThroughput"
  - "Kafka rebalance storm"
  - "static membership Kafka"
  - "troubleshoot Kafka lag"
routes_to: kafka-msk-lag-troubleshooter
---

# /aws:troubleshoot-kafka-msk-lag

Activate the `kafka-msk-lag-troubleshooter` skill and diagnose an
Amazon MSK consumer-group lag incident through the ten-category
diagnostic tree.

## What it does

Reads a symptom description (RecordsLagMax climbing, consumer group
behind, "pipeline is lagging", throughput drop) plus the cluster/topic/
consumer-group context, then walks the symptom-driven diagnostic tree
to a root cause with positive evidence:

1. **Pre-flight** — cluster state (`describe-cluster-v2`), consumer
   group state (`describe-consumer-group`), broker health (CloudWatch
   CpuUser, DiskUsage, UnderReplicatedPartitions), AWS Health.
   Short-circuits on cluster `MAINTENANCE`/`FAILED`, OfflinePartitions
   > 0, or consumer group `DEAD`/`PREPARING_REBALANCE`.
2. **Symptom entry** — map the metric pattern to one of: uniform lag
   (rate), single-partition lag (skew), UnderReplicatedPartitions > 0
   (ISR), broker saturation (CPU/disk/network), producer burst, fetch
   tuning stall, partition parallelism ceiling, MSK Connect lag,
   Serverless CU throttle, rebalance storm, ZooKeeper instability.
3. **Layer-specific probes** —
   - Consumer rate: BytesInPerSec vs BytesOutPerSec; processing time
     per record.
   - Consumer fetch tuning: fetch.min.bytes, fetch.max.wait.ms vs
     topic volume (micro-batch stall on low-volume topics).
   - Partition skew: per-partition lag distribution; per-partition
     throughput; key distribution.
   - ISR shrink: UnderReplicatedPartitions, ISRShrink, broker disk/CPU,
     replica.lag.time.max.ms, min.insync.replicas + acks=all.
   - Broker saturation: CpuUser > 80%, DiskUsage > 85%,
     NetworkProcessorAvgIdlePercent < 0.3.
   - Producer config: acks, batch.size, linger.ms, compression.type.
   - Partition parallelism: consumer-group-members vs partition-count.
   - MSK Connect: SourceTaskRecordPollRate, SinkTaskRecordSendRate,
     RecordLag, worker task state.
   - Serverless throttle: Throttle metric, ConsumedReadThroughput,
     partition-level CU.
   - Rebalance storm: RebalanceRate, session.timeout.ms, static
     membership, cooperative rebalance protocol.
   - ZooKeeper: ZooKeeperRequestLatencyMs, SessionExpireCount (ZK
     clusters only; skip on KRaft).
4. **Verdict** — ROOT_CAUSE_IDENTIFIED (with failing probe that matches
   the symptom) or INSUFFICIENT_DATA (a probe requires data not
   provided).

Emits a deterministic diagnostic block per target:

```text
TARGET: <cluster / topic / consumer-group>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <CONSUMER_RATE | CONSUMER_FETCH_TUNING | PARTITION_SKEW |
        ISR_SHRINK | BROKER_SATURATION | ZOOKEEPER_ISSUE |
        PRODUCER_CONFIG | PARTITION_PARALLELISM | MSK_CONNECT_LAG |
        MSK_SERVERLESS_THROTTLE | REBALANCE_STORM | UNKNOWN>
EVIDENCE:
  - <observed symptom — metric pattern or error string>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command or config change>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "MSK consumer lag climbing"
- "RecordsLagMax is 8 million"
- "Kafka consumer group is behind"
- "MSK partition skew — one partition has all the lag"
- "UnderReplicatedPartitions on MSK"
- "MSK broker disk full"
- "fetch.min.bytes is causing lag"
- "MSK Serverless throttled"
- "Kafka rebalance storm"
- "MSK Connect connector is lagging"

A bare cluster ARN + topic name + "lag" or "behind" also routes here
via the orchestrator.

## Inputs

- Symptom description: metric pattern (uniform lag vs single-partition
  lag vs sawtooth), error strings (NOT_ENOUGH_REPLICAS, ImagePullFailure),
  observed behaviour.
- Cluster context: ClusterArn, ClusterType (PROVISIONED vs SERVERLESS),
  topic name, partition count, replication factor, consumer group name,
  consumer group members, consumer group state.
- Metrics snapshot: RecordsLagMax, BytesInPerSec, BytesOutPerSec,
  UnderReplicatedPartitions, CpuUser (per broker), Throttle (Serverless).
- For live-account diagnosis: the skill uses `describe-cluster-v2`,
  `describe-consumer-group`, `get-metric-statistics` on AWS/Kafka
  and AWS/MSKConnect.

## Outputs

- One diagnostic block per target cluster/topic/consumer-group.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: re-key producer, add storage, scale broker
  type, tune fetch config, enable static membership, configure
  partition projection, or reconfigure the connector.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for MSK consumer lag).
- `/aws:audit-msk-cluster` for configuration posture audits on the
  same cluster (broker type sizing, replication factor, retention).
- `/aws:troubleshoot-kafka-connect` for deeper diagnosis when the lag
  is in an MSK Connect connector pipeline.
