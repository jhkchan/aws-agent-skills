---
name: kafka-msk-lag-troubleshooter
description: 'Diagnoses Amazon MSK consumer lag through a ten-category diagnostic tree: consumer-group lag (RecordsLagMax) vs consumer processing rate, partition skew / hot-key imbalance, broker CPU/disk/network saturation, under-replicated partitions and ISR shrink/expansion, ZooKeeper session expiry, consumer fetch.min.bytes / fetch.max.wait.ms micro-batch tuning, producer acks / batch.size / compression.type throughput, topic partition count vs consumer parallelism, MSK Connect source/sink connector lag, MSK Serverless vs Provisioned partition throughput throttling (ConsumedReadThroughput, BytesPerSec), and rebalance storms from missing static membership. Walks symptoms to a verified root cause with evidence-backed probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted consumer-group metrics and CloudWatch dashboards. Live-account diagnosis uses aws kafka describe-cluster, aws kafka describe-cluster-operation, aws cloudwatch get-metric-statistics on AWS/Kafka and AWS/MSKConnect namespaces, aws kafka list-consumer-groups, aws kafka describe-consumer-group, aws kafka get-client-metrics, and aws logs get-query-results (AWS CLI v2...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing Amazon MSK consumer-group lag (RecordsLagMax climbing, consumer processing rate below producer rate, partition skew where one partition holds the majority of messages, under-replicated partitions with ISR shrink, broker CPU/disk/network saturation, ZooKeeper session instability, consumer fetch.min.bytes or fetch.max.wait.ms set too high for low-volume topics, producer acks/batch.size/compression misconfigured for throughput, topic partition count lower than consumer-group member count, MSK Connect source/sink connector lag, MSK Serverless ConsumedReadThroughput throttling, or rebalance storms from missing static membership), walking a symptom to the failed layer with verify commands, validating why a consumer group shows growing lag, or triaging a "the pipeline is behind" page where the root cause may be producer rate, consumer rate, partition distribution, broker health, or cluster throttling — not necessarily the consumer application code itself.
  when_not_to_use: Application-code-level debugging of the consumer's process() handler (use the consumer logs and a profiler), Kafka client library upgrade or compatibility testing (use the client library docs), cross-cluster MirrorMaker2 topology design (use the MSK documentation), KRaft mode migration planning (use the MSK Multi-AZ KRaft guide), or MSK cluster capacity sizing for a greenfield workload (use the msk-cluster-auditor skill). This skill diagnoses lag incidents; it does not size clusters or tune for steady-state throughput optimization.
  activation_triggers: MSK consumer lag, Kafka RecordsLagMax, consumer group lag climbing, Kafka partition skew, hot key Kafka, under-replicated partitions MSK, ISR shrink Kafka, broker disk full MSK, broker CPU high Kafka, ZooKeeper session expired, Kafka fetch.min.bytes, fetch.max.wait.ms, Kafka micro-batch, producer acks Kafka, batch.size producer, compression.type Kafka, partition count too low, consumer parallelism, MSK Connect lag, source connector lag, sink connector lag, MSK Serverless throttled, ConsumedReadThroughput, Kafka rebalance storm, static membership Kafka, group.session.timeout.ms, troubleshoot Kafka lag
  invocation_schema: 'Input: either (a) a symptom description (RecordsLagMax climbing, consumer group behind, "pipeline is lagging", throughput drop), optionally paired with the MSK cluster ARN, topic name, consumer group name, and CloudWatch/Kafka metrics snapshots, OR (b) a cluster ARN plus consumer group name and topic for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {CONSUMER_RATE, CONSUMER_FETCH_TUNING, PARTITION_SKEW, ISR_SHRINK, BROKER_SATURATION, ZOOKEEPER_ISSUE, PRODUCER_CONFIG, PARTITION_PARALLELISM, MSK_CONNECT_LAG, MSK_SERVERLESS_THROTTLE, MSK_PROVISIONED_THROTTLE, REBALANCE_STORM, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"consumer group cg-payments-processor on topic tx-events shows\nRecordsLagMax climbing from 10K to 8M over 4 hours; the pipeline is\nfalling behind.\"\nClusterArn: arn:aws:kafka:us-east-1:111111111111:cluster/prod-msk/abc-123\nTopic: tx-events\nConsumerGroup: cg-payments-processor\nPartitions: 12\nConsumerGroupMembers: 12\nCloudWatch (last 4h):\n  - RecordsLagMax: 10000 → 8000000\n  - ConsumptionRate (BytesPerSec): flat at 5 MB/s\n  - BytesInPerSec: 12 MB/s\n  - UnderReplicatedPartitions: 0\n  - CpuUser / CpuSystem: 35% / 5%\nInvocation type: poll-based consumer (kafka-clients), commit manual"
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: MSK, Kafka, consumer lag, RecordsLagMax, partition skew, hot key, under-replicated partitions, ISR, ISR shrink, broker saturation, broker disk, ZooKeeper, fetch.min.bytes, fetch.max.wait, micro-batch, producer acks, batch.size, compression.type, partition count, consumer parallelism, MSK Connect, source connector, sink connector, MSK Serverless, ConsumedReadThroughput, BytesPerSec, rebalance storm, static membership, group.session.timeout, troubleshooting
  tags: kafka, msk, analytics, troubleshooting, consumer-lag, partition-skew, isr, broker, producer, consumer, serverless
---

# Kafka MSK Lag Troubleshooter

## Quick start

- **The lag equation (memorise this):** consumer lag grows when
  `producer_rate > consumer_rate`. But consumer_rate is not a single
  number — it is the product of `(consumers × per-consumer throughput)`
  further degraded by `partition_skew` (consumers idle while one
  drowns) and `ISR_loss` (replicas fall behind, leader throttles
  writes, end-to-end latency climbs). A senior Kafka engineer
  decomposes lag into producer rate, consumer rate, partition
  distribution, ISR health, and broker saturation BEFORE touching the
  consumer config.
- **Symptom → layer map (first plausible match drives the first probe):**
  RecordsLagMax climbing on ALL partitions uniformly → CONSUMER_RATE /
  CONSUMER_FETCH_TUNING; lag climbing on ONE partition while others are
  near-zero → PARTITION_SKEW; UnderReplicatedPartitions > 0 with ISR
  shrinking → ISR_SHRINK; broker CpuUser > 80% or disk usage > 85% →
  BROKER_SATURATION; producer throughput (BytesInPerSec) jumped while
  consumer rate is flat → PRODUCER_CONFIG or producer-side burst;
  rebalance events correlate with lag spikes → REBALANCE_STORM;
  MSK Serverless and ConsumedReadThroughput throttle →
  MSK_SERVERLESS_THROTTLE.
- **fetch.min.bytes is a micro-batch knob, not a throughput knob.**
  Setting `fetch.min.bytes=10485760` (10 MB) makes the consumer wait
  until 10 MB accumulates OR `fetch.max.wait.ms` (default 500 ms)
  elapses. On a high-volume topic this batches efficiently; on a
  low-volume topic the consumer waits the full `fetch.max.wait.ms` on
  every poll, adding hundreds of ms of latency per record and
  cratering throughput. Operators who "raise fetch.min.bytes for
  throughput" on a low-volume topic cause the lag they are trying to
  fix.
- **Partition count is the parallelism ceiling.** A topic with 12
  partitions can have at most 12 consumers in a group processing in
  parallel. Adding a 13th consumer does nothing — it sits idle. If
  lag is high and `consumer-group-members == partition-count`, the
  fix is to increase partitions (which requires a new topic or
  partition-assignment rebuild for keyed messages), NOT to add
  consumers.
- **MSK Serverless throttles on ConsumedReadThroughput (CU), not just
  raw bytes.** Each partition has a write CU and read CU cap. A single
  hot partition hitting its CU cap is throttled even when the cluster
  overall has spare capacity. Operators who see "lag on one partition
  only" on Serverless should check partition-level CU, not cluster
  aggregate throughput.

## Mindset

Consumer lag is a rate-mismatch incident with a confounding factor:
the rate on each side is not uniform across partitions. The producer
side may be bursting, the consumer side may be under-provisioned, the
partition assignment may route 80% of traffic to one partition, or the
broker side may be degrading (ISR loss, disk pressure) in a way that
throttles the leader and inflates end-to-end latency. Treat the
consumer application as innocent until producer rate, consumer rate,
partition distribution, ISR health, and broker saturation are each
proven clean. Senior Kafka engineers start with the lag distribution
across partitions — a uniform climb points one direction, a single-
partition spike points another.

## Philosophy

Four behaviours separate a senior MSK engineer from a generalist:

- **Read the lag distribution across partitions first, not the
  aggregate.** `RecordsLagMax` is the maximum lag across all
  partitions; `RecordsLag` (per-partition, available via
  `kafka-consumer-groups --describe` or MSK client metrics) shows the
  distribution. A uniform climb (all partitions lagging equally) is a
  rate problem. A single-partition spike (one partition at 8M, others
  at 10K) is a skew problem. Treating a skew problem as a rate problem
  — "add more consumers" — does nothing because the skewed partition
  is already assigned to one consumer and cannot be parallelised.
- **ISR loss is a data-availability risk, not just a performance
  issue.** When the In-Sync Replica set shrinks (`ISRShrink`), the
  leader writes to fewer replicas. With `acks=all` (the MSK default
  for provisioned clusters with `min.insync.replicas=2`), if ISR drops
  below `min.insync.replicas`, the producer receives
  `NOT_ENOUGH_REPLICAS` and writes fail. The lag you see may be the
  producer unable to write, not the consumer unable to read.
- **MSK Serverless and MSK Provisioned fail for different reasons.**
  Provisioned clusters fail on broker resource saturation (CPU, disk,
  network) and ZooKeeper instability (on ZK-based clusters). Serverless
  clusters fail on partition-level CU throttling
  (`ConsumedReadThroughput`, `ConsumedWriteThroughput`) — the cluster
  auto-scales, but each partition has a hard CU cap that does not
  scale. Operators who apply Provisioned-mode diagnostics (check CPU,
  check disk) to a Serverless cluster waste time on metrics that do
  not govern throttling.
- **Rebalance storms look like consumer lag but are caused by group
  membership churn.** Each rebalance pauses consumption for the entire
  group during the stop-the-world phase. If members join and leave
  repeatedly (consumer crash, long GC pause exceeding
  `session.timeout.ms`, deployment rolling restart without static
  membership), the group never reaches steady state. The symptom is
  lag climbing in a sawtooth pattern that correlates with rebalance
  events, not with producer rate or consumer processing time.

## Quick reference — symptom triage table

| Symptom / metric pattern | Most likely layer | First probe |
|---|---|---|
| RecordsLagMax climbing uniformly across all partitions; ConsumptionRate flat; BytesInPerSec climbing | CONSUMER_RATE | Consumer processing time per record; add consumers or increase partitions |
| RecordsLagMax climbing on ONE partition; others near-zero | PARTITION_SKEW | Per-partition BytesInPerSec; key distribution; partitioner |
| UnderReplicatedPartitions > 0; ISRShrink events; OfflinePartitions > 0 | ISR_SHRINK | `kafka.topics.isr.shrinks`, broker disk, network, `unclean.leader.election` |
| CpuUser > 80% or disk usage > 85% on broker; NetworkProcessorAvgIdlePercent < 0.3 | BROKER_SATURATION | `CpuUser`, `BytesInPerSec` per broker, disk `kBRead/s` + `kBWrttn/s` |
| Producer receives NOT_ENOUGH_REPLICAS or latency spikes; acks=0 or 1 | PRODUCER_CONFIG | `acks`, `batch.size`, `compression.type`, `linger.ms` |
| fetch.min.bytes set high (≥1 MB) on a low-volume topic; consumer poll latency > fetch.max.wait.ms | CONSUMER_FETCH_TUNING | `fetch.min.bytes`, `fetch.max.wait.ms`, per-partition volume |
| Consumer group members == partition count; lag still climbing | PARTITION_PARALLELISM | `partition count`, `consumer group members`; cannot add parallelism |
| ConnectorSourceTask or ConnectorSinkTask lag metric climbing; MSK Connect | MSK_CONNECT_LAG | `SourceTaskRecordPollRate`, `SinkTaskRecordSendRate`, worker task state |
| MSK Serverless; ConsumedReadThroughput or ConsumedWriteThroughput throttle on hot partition | MSK_SERVERLESS_THROTTLE | Partition-level CU, `Throttle` metric in AWS/Kafka |
| Lag sawtooth pattern; rebalance events correlate with spikes; session timeouts in consumer logs | REBALANCE_STORM | `RebalanceRate`, consumer session.timeout.ms, heartbeat, static membership |
| ZooKeeper-based MSK; ZookeeperRequestLatencyMs spike;ExpiredSessions; controller instability | ZOOKEEPER_ISSUE | `ZooKeeperRequestLatencyMs`, `ExpiredSessions`, `KafkaController` metrics |
| None of the above cleanly; insufficient partition-level data | INSUFFICIENT_DATA | Ask for per-partition lag, per-partition BytesInPerSec, broker-level metrics |

## Pre-flight: cluster state and gather-info gate

Before running symptom-specific probes, gather the cluster state and
short-circuit on cluster-wide conditions that mimic consumer lag.

### Account-wide pre-flight commands

```bash
# 1. Cluster description (broker count, version, broker type, mode)
aws kafka describe-cluster-v2 \
  --cluster-arn <arn> --output json

# 2. Consumer group description (members, state, partition assignment)
aws kafka describe-consumer-group \
  --cluster-arn <arn> \
  --consumer-group-id <group> \
  --region <region> --output json

# 3. Topic summary (partition count, replication factor, ISR)
aws kafka describe-topic \
  --cluster-arn <arn> \
  --topic-arn <topic-arn> --output json 2>/dev/null || \
  echo "Use kafka-consumer-groups.sh via client machine for partition-level detail"

# 4. CloudWatch: aggregate lag and throughput (5-min periods)
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name RecordsLagMax \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum,Average --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name BytesInPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum,Average --output json

# 5. CloudWatch: broker saturation (per-broker CPU, disk, network)
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name CpuUser \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# 6. CloudWatch: ISR and replication health
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name UnderReplicatedPartitions \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name BytesOutPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

### Cluster-state short-circuit

| Cluster state / metric | Effect on diagnosis |
|---|---|
| `ACTIVE` + no recent maintenance operation | Proceed with symptom-driven diagnosis. |
| `MAINTENANCE` / `UPDATING` | A broker rotation or version upgrade is in flight. Consumers may see brief leader elections and rebalances. Note in REMEDIATION; wait for `ACTIVE` before drawing conclusions. |
| `FAILED` | The cluster is in a failed state. Escalate to AWS Support; customer-side consumer tuning will not help. |
| UnderReplicatedPartitions > 0 sustained | ISR shrink is in progress; jump to ISR_SHRINK diagnosis. Producer may already be failing if `acks=all` and ISR < `min.insync.replicas`. |
| OfflinePartitions > 0 | One or more partitions have no available leader. The cluster is in a partial outage. Escalate immediately. |
| ZooKeeper-based cluster (`zookeeper.3` or earlier), ZookeeperRequestLatencyMs spike | ZK instability cascades into controller failures and leader elections; check ZOOKEEPER_ISSUE before consumer-side diagnosis. |

### Consumer-group-state short-circuit

| Consumer group state | Effect |
|---|---|
| `STABLE` | Group has reached steady-state partition assignment. Proceed with rate-based diagnosis. |
| `PREPARING_REBALANCE` / `COMPLETING_REBALANCE` | Group is mid-rebalance; consumption is paused. If this state persists or recurs, route to REBALANCE_STORM. |
| `DEAD` | The group has no active members; partitions are unassigned and lag will climb. Check whether consumers crashed. |
| `EMPTY` | Group has no members and no offsets; this is normal for a new or reset group. |

If the input is malformed (missing cluster ARN, absent topic, absent
consumer group name, no metrics snapshot for offline classification),
emit INSUFFICIENT_DATA with the specific gaps.

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed metric pattern, then walk the layer-specific probes in order.
Each layer ends with either a positive root-cause confirmation (failing
probe that matches the symptom) or a pass that moves to the next layer.
**Never emit ROOT_CAUSE_IDENTIFIED without a failing probe that matches
the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

These are the operational gotchas a senior MSK engineer knows from
incident experience. Each one routes a diagnosis away from the obvious
layer to a less obvious one:

- **RecordsLagMax is the MAX, not the SUM or average.** A topic with 12
  partitions where 11 are at zero lag and one is at 8M shows
  `RecordsLagMax = 8000000`. Operators who read the aggregate and
  assume "the whole topic is lagging" misdiagnose a skew problem as a
  rate problem. Always request per-partition lag
  (`kafka-consumer-groups --describe --group <g> --bootstrap-server <b>`).

- **A keyed producer with a bad partitioner causes skew that no amount
  of consumer tuning fixes.** If 80% of messages have the same key
  (e.g., a "device-id" key where one device generates a burst), the
  default partitioner hashes the key and sends all messages to the
  same partition. Adding partitions, consumers, or fetch tuning does
  nothing — the skew is on the producer side. The fix is a custom
  partitioner or re-keying (e.g., compound key `device-id + epoch`).

- **Increasing partitions on a topic with keyed messages breaks
  ordering and may not redistribute existing data.** Kafka assigns a
  partition by hashing the key; adding partitions changes the hash
  mapping. Existing messages stay on their original partition. New
  messages with the same key may now route to a different partition,
  breaking per-key ordering. Only NEW messages benefit from the added
  partitions. Operators who "add partitions to fix lag" on a keyed
  topic may break downstream consumers that rely on per-key ordering.

- **`min.insync.replicas=2` with `acks=all` means ISR loss stops the
  producer.** If a broker fails and ISR for a partition drops below
  `min.insync.replicas`, the producer receives
  `NOT_ENOUGH_REPLICAS (errorCode: 19)`. The symptom looks like
  "producer can't write" — but the root cause is replica health, not
  producer config. The lag downstream is a side effect of the producer
  failing intermittently.

- **Consumer rebalance is stop-the-world.** During a rebalance, ALL
  consumers in the group stop consuming until the new assignment is
  computed and propagated. A group that rebalances every 30 seconds
  spends a significant fraction of time not consuming. The symptom is
  a sawtooth lag pattern: lag climbs during rebalance, drops after the
  group stabilises, climbs again at the next rebalance.

- **`fetch.min.bytes` interacts with `fetch.max.wait.ms`.** The consumer
  fetches when EITHER threshold is met. With `fetch.min.bytes=10MB`
  and `fetch.max.wait.ms=500ms`, a low-volume partition produces, say,
  100 KB in 500 ms — the consumer waits the full 500 ms, fetches the
  100 KB, and processes it. Effective poll latency is 500 ms per
  cycle. On a high-volume partition (10 MB in 50 ms), the consumer
  fetches at the 50 ms mark. The SAME config behaves well on
  high-volume partitions and badly on low-volume ones.

- **MSK Serverless CU throttling is per-partition, not per-cluster.**
  Each partition on Serverless has a write CU and read CU limit. The
  cluster can scale to thousands of partitions, but a single hot
  partition is throttled at its individual CU cap. The fix is
  partition-level scale-out (more partitions for the same logical
  stream), not cluster-level scale.

- **`compression.type` must match between producer and broker.** If
  the producer sends `compression.type=snappy` and the broker is
  configured `compression.type=producer` (pass-through), the broker
  stores compressed batches and consumers must decompress. If the
  consumer client does not support the codec, it fails silently or
  with a cryptic error. `lz4` and `zstd` require client library
  support; very old consumers may not have it.

- **MSK Connect lag is separate from consumer-group lag.** A source
  connector (e.g., Debezium, S3 Source) has its own offset tracking;
  a sink connector (e.g., S3 Sink, Elasticsearch Sink) has its own
  commit semantics. The consumer group metrics
  (`kafka.consumer.records-lag-max`) do NOT capture connector lag.
  Use the `AWS/MSKConnect` namespace metrics
  (`SinkTaskRecordSendRate`, `SourceTaskRecordPollRate`,
  `RecordLag`) for connector-specific lag.

- **ZooKeeper session expiry on a broker causes a controller failover
  and cascading leader elections.** On ZK-based MSK clusters
  (Kafka 2.x / 3.x with ZK), a broker that loses its ZK session is
  removed from the cluster; all partitions it led get new leaders.
  This manifests as a burst of leader elections, ISR fluctuations, and
  transient producer/consumer errors. KRaft-mode clusters (MSK with
  KRaft, 2024+) eliminate ZK entirely; this failure mode does not
  apply.

### Step 1: Symptom entry — pick the diagnostic branch

| Symptom / metric pattern | Branch |
|---|---|
| RecordsLagMax climbing uniformly; ConsumptionRate flat or below BytesInPerSec | Step 2 — Consumer rate / fetch tuning |
| RecordsLagMax concentrated on one or few partitions | Step 3 — Partition skew |
| UnderReplicatedPartitions > 0; ISRShrink/ISRExpand events | Step 4 — ISR shrink |
| Broker CpuUser > 80%, disk > 85%, or NetworkProcessorAvgIdlePercent < 0.3 | Step 5 — Broker saturation |
| Producer throughput (BytesInPerSec) burst or producer errors; acks config | Step 6 — Producer config |
| Consumer group members == partition count; cannot add parallelism | Step 7 — Partition parallelism |
| MSK Connect; connector lag metric climbing | Step 8 — MSK Connect lag |
| MSK Serverless; ConsumedReadThroughput / ConsumedWriteThroughput throttle | Step 9 — MSK Serverless throttling |
| Rebalance events correlate with lag sawtooth | Step 10 — Rebalance storm |
| ZooKeeper-based cluster; ZK latency or session instability | Step 11 — ZooKeeper issue |
| None of the above | Step 12 — INSUFFICIENT_DATA |

### Step 2: Consumer rate and fetch tuning

Symptom: RecordsLagMax climbing uniformly across partitions.
BytesInPerSec exceeds ConsumptionRate (BytesOutPerSec).

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name BytesOutPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

If BytesInPerSec (consumer read rate) is consistently below
BytesInPerSec (producer write rate), the consumer cannot keep up.
Two sub-causes:

#### 2a: Consumer processing-bound

Each `poll()` returns records; the consumer processes them
synchronously; if processing time per record exceeds the inter-arrival
time, lag grows. Check:

```bash
# Consumer-side metrics (if Dropwizard / Micrometer exposed)
# records-consumed-rate vs records-lag-max
# Consumer fetch metrics via client JMX or CloudWatch:
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name ConsumedReadThroughput \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

If consumers are processing-bound (high CPU, slow downstream DB write),
the fix is to add consumers (if partitions > current members) or
optimize the processing path (batch DB writes, async I/O).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CONSUMER_RATE`.

#### 2b: Consumer fetch-bound (micro-batch stall)

If consumers are NOT CPU-bound but still cannot keep up, the fetch
config may be introducing artificial latency. Check the consumer
config:

```bash
# From the consumer application config or describe-configs on the client
# (requires kafka-configs.sh access to the cluster)
# Key properties to inspect:
#   fetch.min.bytes       (default 1)
#   fetch.max.wait.ms     (default 500)
#   max.poll.records      (default 500)
#   fetch.max.bytes       (default 57671680 = 55 MB)
```

| Config pattern | Effect |
|---|---|
| `fetch.min.bytes = 10485760` (10 MB) on a low-volume topic | Consumer waits up to `fetch.max.wait.ms` each poll cycle; effective poll rate drops; lag climbs on low-volume partitions |
| `fetch.max.wait.ms = 5000` | Consumer waits up to 5 seconds per fetch; on bursty traffic this adds 5 s of latency per batch |
| `max.poll.records = 10` | Consumer fetches tiny batches; overhead per poll dominates; throughput drops |
| `fetch.min.bytes = 1` (default) on a high-volume topic | Consumer fetches too frequently; network overhead rises; may not keep up with producer on very high-volume topics |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CONSUMER_FETCH_TUNING`. Fix:
align fetch tuning to topic volume — low-volume topics want
`fetch.min.bytes=1`, `fetch.max.wait.ms=100`; high-volume topics
benefit from `fetch.min.bytes=1048576` (1 MB) or higher.

### Step 3: Partition skew

Symptom: RecordsLagMax concentrated on one or few partitions; other
partitions near-zero lag. Consumer-group members are unevenly loaded.

```bash
# Per-partition lag (requires client machine with kafka-consumer-groups)
# kafka-consumer-groups.sh --bootstrap-server <b> --describe --group <g>
#
# CloudWatch: per-partition BytesInPerSec is not directly exposed;
# use the topic-level metric and infer from consumer-side per-partition
# records-lag-max (Micrometer/Dropwizard on the consumer).
```

| Pattern | Cause |
|---|---|
| 80% of messages on one partition; key is `device-id` with one device bursting | Key skew — default partitioner hashes the key; one key = one partition |
| Skew across brokers but not partitions | Broker-level leadership imbalance; preferred leader election needed |
| Skew appeared after adding partitions | Hash mapping changed; existing keys redistributed unevenly |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PARTITION_SKEW`. Fix:
- Re-key with a compound key (e.g., `device-id + epoch-minute`) to
  distribute load.
- Or use a custom partitioner that round-robins hot keys.
- Or increase partition count AND accept that existing keyed data
  stays on old partitions (only new data redistributes).

### Step 4: ISR shrink — under-replicated partitions

Symptom: `UnderReplicatedPartitions > 0`, `ISRShrink` events,
possibly `OfflinePartitions > 0`.

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name UnderReplicatedPartitions \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name OfflinePartitions \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum --output json
```

Check the broker-level root cause of ISR shrink:

```bash
# Broker disk usage (the #1 cause of ISR shrink)
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name DiskKBReadPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name DiskKBWrttnPerSec \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

Common ISR shrink causes:

| Cause | How to verify |
|---|---|
| Broker disk full (>85%) | Disk usage metric; broker log directory at capacity |
| Broker network saturated | NetworkProcessorAvgIdlePercent < 0.3 |
| Broker CPU saturated | CpuUser > 80% sustained |
| Broker GC pause (long stop-the-world) | JVM GC logs; `kafka.server:type=BrokerTopicMetrics` latency spike |
| `replica.lag.time.max.ms` too aggressive | Follower cannot fetch within the window; gets removed from ISR |
| `unclean.leader.election.enable=true` with a slow follower | Out-of-sync follower becomes leader; data loss + ISR chaos |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ISR_SHRINK`. Fix:
- Broker disk full: add storage (MSK broker storage update) or delete
  old log segments (topic retention).
- Broker CPU/network: scale to a larger broker type (MSK broker type
  update).
- `replica.lag.time.max.ms` too low: raise to accommodate follower
  fetch latency.
- `min.insync.replicas` check: if ISR < min.insync.replicas and
  acks=all, producer fails; either fix the broker or temporarily
  lower min.insync.replicas (with data-loss risk).

### Step 5: Broker saturation

Symptom: CpuUser > 80%, disk usage > 85%, or
NetworkProcessorAvgIdlePercent < 0.3 on one or more brokers.

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name CpuUser \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name NetworkProcessorAvgIdlePercent \
  --dimensions Name=Cluster,Value=<cluster-name> Name=Broker,Value=<broker-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Minimum --output json
```

| Resource | Threshold | Fix |
|---|---|---|
| CpuUser | > 80% sustained | Scale broker type (e.g., kafka.m5.large → kafka.m5.xlarge); add brokers |
| Disk usage | > 85% | Add storage; reduce retention; compact topics |
| NetworkProcessorAvgIdlePercent | < 0.3 (30%) | Scale broker type (network thread bottleneck); increase `num.network.threads` |
| Disk queue depth | high `kBRead/s` + `kBWrttn/s` near device limit | Scale to faster disk (MSK provisioned IOPS); add brokers |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: BROKER_SATURATION`. Fix:
scale broker type, add brokers, add storage, or reduce load (retention,
compaction).

### Step 6: Producer config

Symptom: BytesInPerSec burst, or producer errors, or throughput lower
than expected. Consumer lag is a side effect of producer misbehaviour.

Key producer configs to check (from the producer application config):

| Config | Effect on lag |
|---|---|
| `acks` | `acks=0` — fire and forget; high throughput but data loss on broker failure. `acks=1` — leader write only. `acks=all` — ISR write; safest, slowest. Mismatch with `min.insync.replicas` causes NOT_ENOUGH_REPLICAS. |
| `batch.size` | Small batch (e.g., 16384 = 16 KB default) on high-volume producer means too many small requests. Raise to 131072 (128 KB) or higher for throughput. |
| `linger.ms` | 0 (default) sends immediately. Raising to 5-20 ms batches more records per request, increasing throughput at the cost of latency. |
| `compression.type` | `none` (default) — no compression, more bytes. `lz4`, `snappy`, `zstd`, `gzip` — compressed batches; less network/disk but consumers must decompress. |
| `buffer.memory` | If too small, producer blocks on `max.block.ms`; throughput drops. Default 33554432 (32 MB). |
| `max.in.flight.requests.per.connection` | High value (e.g., 5+) improves throughput but risks reordering on retries if `enable.idempotence=false`. |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PRODUCER_CONFIG`.

### Step 7: Partition parallelism ceiling

Symptom: Consumer group members == partition count. Lag climbing
uniformly. Adding consumers does not help.

```bash
# Topic partition count
aws kafka describe-topic --cluster-arn <arn> \
  --topic-arn <topic-arn> --output json | \
  jq '.TopicInfo.PartitionCount'

# Consumer group members
aws kafka describe-consumer-group \
  --cluster-arn <arn> \
  --consumer-group-id <group> --output json | \
  jq '.ConsumerGroupDescription.Members | length'
```

If `members == partition_count`, the group has reached parallelism
ceiling. No additional consumer can receive a partition.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PARTITION_PARALLELISM`. Fix:
- Increase partition count (note: breaks key ordering for keyed
  messages; existing data stays on old partitions).
- Or increase per-consumer throughput (multi-threaded processing,
  async I/O).
- Or shard the topic into multiple topics and consumer groups.

### Step 8: MSK Connect lag

Symptom: Lag on a connector-managed pipeline (source or sink).
Consumer group metrics are clean; the lag is in the connector.

```bash
# MSK Connect connector state and lag
aws kafkaconnect describe-connector \
  --connector-arn <arn> --output json

aws cloudwatch get-metric-statistics --namespace AWS/MSKConnect \
  --metric-name RecordLag \
  --dimensions Name=ConnectorName,Value=<connector-name> \
  --start-time $(date -u -d '-4 hours' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Maximum,Average --output json

aws cloudwatch get-metric-statistics --namespace AWS/MSKConnect \
  --metric-name SinkTaskRecordSendRate \
  --dimensions Name=ConnectorName,Value=<connector-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average --output json
```

| Connector pattern | Cause |
|---|---|
| Source connector (e.g., Debezium) lag; `SourceTaskRecordPollRate` low | Source DB slow; connector task under-provisioned; increase `tasks.max` |
| Sink connector (e.g., S3 Sink) lag; `SinkTaskRecordSendRate` low | Sink destination slow (S3, ES); increase `tasks.max`; check sink-side throttling |
| Connector task in `FAILED` state | Check connector worker logs; common causes: auth failure, schema registry unreachable, sink-side permission denied |
| Connector auto-scaling not triggering | `worker.microvolume.tasks` vs `worker.cpu.utilization` thresholds; MSK Connect auto-scaling needs explicit configuration |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MSK_CONNECT_LAG`. Fix:
increase `tasks.max`, scale the connector worker config, or address the
sink/source bottleneck.

### Step 9: MSK Serverless throttling

Symptom: MSK Serverless cluster; lag on specific partitions;
`ConsumedReadThroughput` or `ConsumedWriteThroughput` throttle.

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name Throttle \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name ConsumedReadThroughput \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

MSK Serverless CU (Capacity Units) are per-partition:
- Each partition has a write CU cap (default varies by region).
- Read CU is consumed per consumer read.
- A single hot partition hitting its CU cap is throttled even when the
  cluster overall has capacity.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MSK_SERVERLESS_THROTTLE`.
Fix:
- Redistribute load across more partitions (add partitions to the
  topic; note Serverless supports up to 12,000 partitions per cluster).
- Reduce per-partition throughput by re-keying.
- For read throttle: reduce consumer poll rate or batch size;
  scale-out is limited by partition-level CU.

### Step 10: Rebalance storm

Symptom: Lag sawtooth pattern; rebalance events correlate with spikes;
consumer logs show `Member ... sending JoinGroup request` frequently.

```bash
# Rebalance rate (if exposed via client metrics or CloudWatch)
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name RebalanceRate \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

Consumer-side config to check:

| Config | Effect |
|---|---|
| `session.timeout.ms` (default 45000 on MSK) | If consumer GC pauses exceed this, broker considers the consumer dead and triggers rebalance |
| `heartbeat.interval.ms` (default 3000) | Must be < session.timeout.ms / 3; if heartbeats are missed, rebalance fires |
| `max.poll.interval.ms` (default 300000 = 5 min) | If processing a batch takes longer than this, consumer is kicked out of the group → rebalance |
| Static membership (`group.instance.id`) | Not set → every consumer restart triggers a rebalance. Set → consumer reclaims its partitions after restart without full rebalance |

| Rebalance trigger | How to verify |
|---|---|
| Consumer crash / OOM | Consumer application logs; `Errors` metric on consumer |
| Long GC pause > session.timeout.ms | JVM GC logs; `jvm.gc.pause` Micrometer metric |
| Processing time > max.poll.interval.ms | `time-between-polls` metric; reduce `max.poll.records` or speed up processing |
| Deployment rolling restart without static membership | Deploy timeline correlates with rebalance events |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: REBALANCE_STORM`. Fix:
- Enable static membership (`group.instance.id` per consumer instance).
- Raise `max.poll.interval.ms` if processing legitimately takes long.
- Tune GC to avoid stop-the-world pauses.
- Use cooperative rebalance protocol (`partition.assignment.strategy=
  CooperativeStickyAssignor`) to avoid stop-the-world rebalances.

### Step 11: ZooKeeper issues (ZK-based clusters only)

Symptom: ZooKeeper-based MSK cluster; `ZookeeperRequestLatencyMs` spike;
`ExpiredSessions`; controller instability; cascading leader elections.

```bash
aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name ZooKeeperRequestLatencyMs \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
  --metric-name SessionExpireCount \
  --dimensions Name=Cluster,Value=<cluster-name> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum --output json
```

ZK instability cascades: broker loses session → removed from cluster →
leader elections on all partitions it led → ISR fluctuations →
producer/consumer errors → lag.

| ZK issue | Cause |
|---|---|
| ZK disk I/O bottleneck | ZK requires low-latency disk; shared with Kafka log directory contention |
| ZK ensemble size 3 with one node down | Quorum = 2; if another node is slow, writes stall |
| Network partition between broker and ZK | Check VPC routing, security groups, ENI |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ZOOKEEPER_ISSUE`. Fix:
- Escalate to AWS Support for ZK infrastructure issues (customer
  cannot modify ZK config on MSK).
- Migrate to KRaft mode (MSK with KRaft) to eliminate ZK entirely.
- Check broker-to-ZK network path.

### Step 12: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, OR the input
lacks per-partition lag, per-partition throughput, or broker-level
metrics, emit INSUFFICIENT_DATA with the specific gaps. A
ROOT_CAUSE_IDENTIFIED verdict requires a failing probe that matches the
symptom; without the data to run the probe, the skill cannot conclude.

## Output format

```text
TARGET: <cluster-arn shortname / topic / consumer-group>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <CONSUMER_RATE | CONSUMER_FETCH_TUNING | PARTITION_SKEW |
        ISR_SHRINK | BROKER_SATURATION | ZOOKEEPER_ISSUE |
        PRODUCER_CONFIG | PARTITION_PARALLELISM | MSK_CONNECT_LAG |
        MSK_SERVERLESS_THROTTLE | MSK_PROVISIONED_THROTTLE |
        REBALANCE_STORM | UNKNOWN>
EVIDENCE:
  - <observed symptom — metric pattern or error string>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command or config change>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <cluster> in <region>. Proceed?
  (yes/no)"
```

### Worked example — Partition skew, hot key

```text
TARGET: prod-msk / tx-events / cg-payments-processor
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: RecordsLagMax is 8M but 11 of 12 partitions show near-zero lag;
  partition 7 alone holds 8M lag. Per-partition BytesInPerSec shows
  partition 7 receiving 9.6 MB/s while the other 11 average 0.2 MB/s
  each. The producer uses a device-id key; one device (device-abc123)
  is generating 80% of the traffic. The default partitioner hashes
  device-id to partition 7 (Step 3).
LAYER: PARTITION_SKEW
EVIDENCE:
  - Symptom: RecordsLagMax climbing from 10K to 8M over 4 hours; the
    consumer group has 12 members on 12 partitions; only the member
    assigned to partition 7 shows lag.
  - Probe: kafka-consumer-groups --describe --group cg-payments-processor
    shows partition 7 at CURRENT-OFFSET 4.2M, LOG-END-OFFSET 12.2M,
    LAG 8.0M; all other partitions LAG < 100.
  - Probe: Per-partition throughput (client-side Micrometer) shows
    partition 7 at 9.6 MB/s; others at 0.1-0.3 MB/s.
  - Passing: BytesInPerSec cluster-wide is 12 MB/s; broker CpuUser is
    35%; UnderReplicatedPartitions is 0; no rebalance events; consumer
    fetch config is default (fetch.min.bytes=1).
REMEDIATION:
  1. Re-key the producer to distribute the hot device: compound key
     "device-id + epoch-minute" so the default partitioner spreads
     the burst across partitions over time.
  2. Alternatively, implement a custom partitioner that detects hot
     keys and round-robins them.
  3. Verify after re-key: per-partition lag should equalize within
     one retention window; RecordsLagMax should drop below 100K.
CONFIRM: Before deploying the producer re-key, emit and await:
  "CONFIRM: About to deploy re-keyed producer for tx-events on prod-msk.
   This changes partition assignment for new messages. Proceed? (yes/no)"
```

### Worked example — ISR shrink from broker disk saturation

```text
TARGET: prod-msk / tx-events / cg-payments-processor
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: UnderReplicatedPartitions is 14 (sustained for 2 hours);
  ISRShrink events correlate with broker-2 disk usage hitting 92%.
  Broker-2 cannot fetch replicas fast enough; replicas are removed
  from ISR for 14 partitions. With min.insync.replicas=2 and acks=all,
  the producer receives intermittent NOT_ENOUGH_REPLICAS; downstream
  consumer lag is a side effect of producer write failures (Step 4).
LAYER: ISR_SHRINK
EVIDENCE:
  - Symptom: RecordsLagMax climbing; producer logs show
    NOT_ENOUGH_REPLICAS errors intermittently; consumer is healthy.
  - Probe: aws cloudwatch get-metric-statistics on
    UnderReplicatedPartitions returns Maximum=14 sustained.
  - Probe: aws cloudwatch get-metric-statistics on
    DiskKBWrttnPerSec for broker-2 shows sustained write near device
    limit; disk usage at 92%.
  - Probe: ISRShrink events correlate with broker-2 disk pressure
    window.
  - Passing: broker-1 and broker-3 CpuUser < 40%, disk < 60%;
    ZooKeeper stable; no rebalance events.
REMEDIATION:
  1. Add storage to broker-2 (MSK broker storage update):
     aws kafka update-broker-storage --cluster-arn <arn> \
       --broker-ids 2 --target-broker-ebs-volume-gib 2000 \
       --region <region>
  2. Reduce topic retention to free disk space on broker-2 while the
     storage update propagates.
  3. Verify after storage update: UnderReplicatedPartitions drops to 0;
     ISRExpand events appear; producer NOT_ENOUGH_REPLICAS stops.
CONFIRM: Before updating broker storage, emit and await operator
  approval.
```

### Worked example — Consumer fetch tuning on low-volume topic

```text
TARGET: prod-msk / user-events / cg-user-svc
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: RecordsLagMax climbing on topic user-events (low-volume, ~100
  records/min). Consumer config has fetch.min.bytes=10485760 (10 MB)
  and fetch.max.wait.ms=500. The topic produces ~100 KB per second;
  the consumer waits the full 500 ms fetch.max.wait.ms every poll
  cycle, fetching only 50 KB each time. Effective poll rate is 2/sec;
  consumer cannot keep up with even modest traffic (Step 2b).
LAYER: CONSUMER_FETCH_TUNING
EVIDENCE:
  - Symptom: RecordsLagMax climbing steadily; consumer CPU is < 10%;
    downstream is fast; consumer is NOT processing-bound.
  - Probe: Consumer config shows fetch.min.bytes=10485760,
    fetch.max.wait.ms=500.
  - Probe: Client-side metric records-per-sec is ~2 poll cycles ×
    ~50 records = 100 records/sec capacity; topic produces 120
    records/sec.
  - Passing: partitions are evenly distributed (no skew); broker
    healthy; no rebalance; ISR stable.
REMEDIATION:
  1. Set fetch.min.bytes=1 (or 1024 for minor batching) for the
    low-volume topic consumer group.
  2. Set fetch.max.wait.ms=100 to reduce idle wait.
  3. Verify: records-consumed-rate should match producer rate within
    one minute; RecordsLagMax should stabilise and begin draining.
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" diagnosis erodes
  operator trust when the real cause is on a different layer.

- NEVER treat RecordsLagMax (the MAX across partitions) as if it
  represents the average. Always request per-partition lag before
  concluding a rate problem; the max may be one skewed partition.

- NEVER add consumers beyond the partition count. A topic with N
  partitions supports at most N consumers in a group. The N+1th
  consumer is permanently idle and wastes resources.

- NEVER increase partitions on a keyed topic without warning about
  ordering breakage. Adding partitions changes the key-to-partition
  hash mapping; existing data stays put, new data may land on
  different partitions, breaking per-key ordering guarantees.

- NEVER set fetch.min.bytes high on a low-volume topic. The consumer
  will wait up to fetch.max.wait.ms on every poll cycle, cratering
  throughput. fetch.min.bytes is a micro-batch knob; it helps
  high-volume topics and hurts low-volume ones.

- NEVER assume broker CPU is the saturation signal. Kafka is I/O
  bound; check disk read/write rates, disk queue depth, and
  NetworkProcessorAvgIdlePercent before concluding CPU is the
  bottleneck. A broker at 40% CPU can still be saturated on disk I/O.

- NEVER ignore UnderReplicatedPartitions. Sustained URP > 0 means the
  cluster is losing replica health; with acks=all and
  min.insync.replicas=2, the producer will start failing. The
  consumer lag you see may be a symptom of the producer being unable
  to write.

- NEVER conflate MSK Serverless throttling with MSK Provisioned
  saturation. Serverless throttles per-partition on CU; Provisioned
  saturates on broker-level CPU/disk/network. The metrics and fixes
  are entirely different. Applying Provisioned diagnostics to a
  Serverless cluster wastes time.

- NEVER treat MSK Connect lag as consumer-group lag. Connectors have
  their own offset tracking and metrics (AWS/MSKConnect namespace).
  The standard consumer-group metrics do not capture connector
  pipelines.

- NEVER enable `unclean.leader.election.enable=true` to "fix" ISR
  shrink. This allows an out-of-sync replica to become leader,
  causing acknowledged data loss. The MSK default is false; keep it
  that way.

- NEVER diagnose a ZooKeeper issue on a KRaft-mode cluster. MSK with
  KRaft (2024+) has no ZooKeeper; the ZK metrics do not exist. If
  the cluster is KRaft, skip the ZK diagnostic branch entirely.

- NEVER conclude "the consumer is slow" without checking the producer
  rate. If BytesInPerSec doubled (producer burst) and the consumer
  rate is unchanged, the consumer is fine — the producer is
  overwhelming it. The fix is on the producer side (rate limit,
  batch) or cluster side (add partitions), not the consumer.

- NEVER trigger a consumer group rebalance during an incident to
  "redistribute load." Rebalance is stop-the-world; it pauses all
  consumption and will worsen the lag spike.

- NEVER assume `compression.type=lz4` or `zstd` works with all
  consumers. Old consumer clients may not support newer codecs; verify
  consumer library version before changing compression.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-broker-storage`, `update-broker-type`, `update-cluster-
  configuration`, topic config changes, consumer group reset), emit
  and await operator approval. Do NOT execute the CLI until the
  operator confirms.

- **Read-only first.** Every probe in the diagnostic tree is
  read-only (`describe-cluster`, `get-metric-statistics`,
  `describe-consumer-group`, `describe-topic`). Do not perform
  state-changing operations as diagnostic probes.

- **Broker storage update** is online and non-disruptive; MSK adds
  EBS volume capacity without broker restart. Allow 10-30 minutes for
  the operation to complete.

- **Broker type update** triggers a rolling broker restart; each
  broker is drained and replaced. Plan for brief leader elections
  during the rolling restart. Avoid during traffic peaks.

- **Topic partition count increase** is irreversible and breaks
  key-ordering for keyed messages. Confirm the downstream consumers
  do not rely on per-key ordering before proceeding.

- **Consumer group offset reset** (`--reset-offsets`) skips or
  replays messages. This is a data-affecting operation; always confirm
  and document the reset position (earliest, latest, specific offset).

- **Cluster configuration update** (`update-cluster-configuration`)
  changes broker-level configs (`num.network.threads`,
  `log.retention.hours`, `default.replication.factor`, etc.). Some
  configs require a broker restart to take effect; check the config's
  `read-only` / `dynamic` status.

- **MSK Connect connector update** may restart all tasks; plan for a
  brief lag spike during the connector redeployment.

- **Bulk remediation batch limit.** If the diagnosis identifies the
  same root cause across multiple topics or consumer groups, batch
  remediation into groups of at most 5, emit a single CONFIRM per
  batch, and verify between batches.

## Remediation guidance

### For CONSUMER_RATE

- Add consumers (if partition count > current members).
- Optimize processing path (batch DB writes, async I/O, reduce
  per-record compute).
- Increase `max.poll.records` to process more records per poll (if
  processing is fast enough to handle the batch within
  `max.poll.interval.ms`).

### For CONSUMER_FETCH_TUNING

- Low-volume topic: `fetch.min.bytes=1`, `fetch.max.wait.ms=100`.
- High-volume topic: `fetch.min.bytes=1048576` (1 MB) or higher;
  `fetch.max.wait.ms=500` (default).
- Verify with client-side records-consumed-rate metric.

### For PARTITION_SKEW

- Re-key with a compound key (`hot-key + epoch-minute` or
  `hot-key + hash(suffix)`).
- Custom partitioner that round-robins hot keys.
- Increase partitions (note: breaks ordering for keyed messages).

### For ISR_SHRINK

- Broker disk full: `aws kafka update-broker-storage --cluster-arn
  <arn> --broker-ids <id> --target-broker-ebs-volume-gib <gib>`.
- Broker CPU saturated: `aws kafka update-broker-type --cluster-arn
  <arn> --broker-ids <ids> --target-instance-type <type>`.
- Raise `replica.lag.time.max.ms` if followers are slow but
  eventually catch up.
- Check `min.insync.replicas` alignment with `acks` setting.

### For BROKER_SATURATION

- Scale broker type (CPU, network, memory).
- Add brokers (increase cluster size).
- Add storage (disk-bound).
- Reduce retention or enable log compaction (disk-bound).

### For PRODUCER_CONFIG

- `acks=all` for durability; `acks=1` for latency-sensitive.
- `batch.size` ≥ 131072 (128 KB) for throughput.
- `linger.ms` 5-20 for batching.
- `compression.type=lz4` or `zstd` for network/disk efficiency.
- Verify `buffer.memory` is sufficient for the producer rate.

### For PARTITION_PARALLELISM

- Increase topic partitions (note ordering impact for keyed messages).
- Shard into multiple topics with separate consumer groups.
- Increase per-consumer throughput (multi-threaded processing).

### For MSK_CONNECT_LAG

- Increase `tasks.max` on the connector.
- Scale the connector worker config (CPU, memory).
- Address the sink/source bottleneck (S3 throttle, DB connection pool).
- Enable connector auto-scaling if not configured.

### For MSK_SERVERLESS_THROTTLE

- Redistribute load across more partitions (up to 12,000 per cluster).
- Re-key to spread hot partitions.
- For read throttle: reduce consumer poll rate or batch size.

### For REBALANCE_STORM

- Enable static membership (`group.instance.id` per consumer).
- Raise `max.poll.interval.ms` if processing is slow.
- Use cooperative rebalance (`CooperativeStickyAssignor`).
- Tune JVM GC to avoid stop-the-world pauses exceeding
  `session.timeout.ms`.
- Stagger deployment rolling restarts.

### For ZOOKEEPER_ISSUE

- Escalate to AWS Support (customer cannot modify ZK on MSK).
- Migrate to KRaft mode (MSK with KRaft) to eliminate ZK.
- Check broker-to-ZK network path.

## Deep reference: MSK lag layer model

### CloudWatch metrics (AWS/Kafka namespace)

| Metric | What it measures | Diagnostic use |
|---|---|---|
| `RecordsLagMax` | Max records-lag across all partitions in a consumer group | Primary lag signal; climbing = consumer behind |
| `BytesInPerSec` | Producer write rate (bytes/sec) | Compare to BytesOutPerSec; if In > Out, consumer lags |
| `BytesOutPerSec` | Consumer read rate (bytes/sec) | Consumer throughput; compare to BytesInPerSec |
| `ConsumedReadThroughput` | MSK Serverless read CU consumed | Serverless throttle detection |
| `MessagesInPerSec` | Messages/sec written | Producer message rate (not bytes) |
| `UnderReplicatedPartitions` | Partitions with ISR < replication factor | ISR health; > 0 = replica degradation |
| `OfflinePartitions` | Partitions with no available leader | Cluster outage; > 0 = immediate escalation |
| `ISRShrink` / `ISRExpand` | ISR membership changes | ISR instability; correlate with broker health |
| `CpuUser` | Broker CPU user time (%) | Broker saturation; > 80% sustained = scale |
| `DiskKBReadPerSec` / `DiskKBWrttnPerSec` | Broker disk I/O | I/O-bound saturation |
| `NetworkProcessorAvgIdlePercent` | Broker network thread idle (%) | < 0.3 = network thread saturation |
| `RebalanceRate` | Consumer group rebalance events/sec | Rebalance storm detection |
| `ZooKeeperRequestLatencyMs` | ZK request latency (ZK clusters only) | ZK instability |
| `Throttle` | Serverless CU throttle count | Serverless partition throttle |

### MSK Connect metrics (AWS/MSKConnect namespace)

| Metric | What it measures |
|---|---|
| `RecordLag` | Connector lag (records) |
| `SourceTaskRecordPollRate` | Source connector poll rate |
| `SinkTaskRecordSendRate` | Sink connector send rate to destination |
| `TaskStartUps` / `TaskFailures` | Connector task lifecycle |

### Consumer fetch tuning matrix

| Topic volume | fetch.min.bytes | fetch.max.wait.ms | Effect |
|---|---|---|---|
| Low (< 1 MB/s) | 1 (default) | 100 | Immediate fetch; no artificial latency |
| Medium (1-10 MB/s) | 1024-65536 | 500 (default) | Minor batching; balances latency and overhead |
| High (> 10 MB/s) | 1048576 (1 MB)+ | 500 (default) | Large batches; network-efficient |

### Producer acks matrix

| acks | Durability | Throughput | Latency | Use case |
|---|---|---|---|---|
| 0 | Lowest (data loss on failure) | Highest | Lowest | Fire-and-forget telemetry |
| 1 | Medium (leader write only) | Medium | Medium | Balanced latency/durability |
| all (or -1) | Highest (ISR write) | Lowest | Highest | Financial, transactional |

### ISR and min.insync.replicas matrix

| Cluster RF | min.insync.replicas | acks | Tolerates | Write fails when |
|---|---|---|---|---|
| 3 | 2 | all | 1 broker failure | 2+ brokers fail (ISR < 2) |
| 3 | 1 | all | 2 broker failures | All replicas fail (data loss risk) |
| 2 | 2 | all | 0 broker failures | 1 broker fails (no tolerance) |
| 2 | 1 | all | 1 broker failure | Both fail |

### MSK Provisioned vs Serverless throttle model

| Dimension | Provisioned | Serverless |
|---|---|---|
| Throttle basis | Broker resource (CPU, disk, network) | Per-partition CU (write, read) |
| Scale | Add brokers, scale broker type | Auto-scales partitions (up to 12,000) |
| Partition CU cap | n/a | Per-partition hard cap (region-specific) |
| ZooKeeper | ZK-based (2.x/3.x) or KRaft (3.5+) | KRaft only (no ZK) |
| Diagnostic focus | Broker-level CloudWatch | Partition-level CU throttle |

## Recent AWS features (2024-2026)

- **MSK KRaft mode (2024-2025):** MSK clusters can now run in KRaft
  mode without ZooKeeper. KRaft clusters eliminate ZK session expiry
  as a failure mode; the ZOOKEEPER_ISSUE diagnostic branch does not
  apply. Diagnostically, KRaft clusters expose controller metrics
  under `KafkaController` rather than ZK metrics.
- **MSK Serverless partition scale (2024-2025):** Serverless clusters
  support up to 12,000 partitions per cluster. The per-partition CU
  cap remains; scaling means more partitions, not higher per-partition
  throughput. Diagnostically, partition-level CU throttle is the
  primary Serverless failure mode.
- **MSK Client Metrics (2024-2025):** MSK exposes client-side metrics
  (per-consumer records-lag-max, per-producer throughput) via
  CloudWatch. These complement the broker-side AWS/Kafka namespace
  and enable per-partition lag diagnosis without a client-side
  Micrometer setup.
- **MSK Connect auto-scaling (2024-2025):** Connectors can auto-scale
  worker capacity based on CPU utilization and record lag. Diagnostically,
  a connector without auto-scaling enabled will not add capacity under
  load; check the connector's auto-scaling configuration.
- **Cooperative rebalance protocol (2024-2025):** The
  `CooperativeStickyAssignor` is the recommended assignor for MSK
  consumer groups on modern client libraries. It avoids the
  stop-the-world rebalance by incrementally reassigning partitions.
  Operators on the legacy `RangeAssignor` or `RoundRobinAssignor` see
  full stop-the-world rebalances.
- **Tiered storage (2024-2026):** MSK Provisioned clusters support
  tiered storage (move cold log segments to S3). Diagnostically, a
  broker with tiered storage enabled shows lower disk usage but may
  show higher read latency for cold segments fetched from S3.

## Domain

AWS CloudOps / Amazon MSK (Managed Streaming for Apache Kafka),
Consumer Lag Diagnostics, Broker Health, Partition Strategy, MSK
Connect, MSK Serverless.

## AWS documentation

- **Amazon MSK Developer Guide** — https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
- **MSK metrics in CloudWatch** — https://docs.aws.amazon.com/msk/latest/developerguide/metrics-dimensions.html
- **MSK Serverless** — https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html
- **MSK Connect** — https://docs.aws.amazon.com/msk/latest/developerguide/msk-connect.html
- **MSK KRaft mode** — https://docs.aws.amazon.com/msk/latest/developerguide/kraft.html
- **Apache Kafka consumer configuration** — https://kafka.apache.org/documentation/#consumerconfigs
- **Apache Kafka producer configuration** — https://kafka.apache.org/documentation/#producerconfigs
- **MSK broker storage updates** — https://docs.aws.amazon.com/msk/latest/developerguide/msk-update-storage.html
- **MSK broker type updates** — https://docs.aws.amazon.com/msk/latest/developerguide/msk-update-broker-instance-type.html
- **MSK cluster operations** — https://docs.aws.amazon.com/msk/latest/developerguide/operations.html
