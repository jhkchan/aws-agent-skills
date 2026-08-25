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
Deep-dive detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when this branch needs the full detail.

## Mindset

Deep-dive detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when this branch needs the full detail.

## Philosophy

Deep-dive detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when this branch needs the full detail.

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

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

### Cluster-state short-circuit

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

### Consumer-group-state short-circuit

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

## Process — Diagnostic decision tree (apply in symptom order)

Deep-dive detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when this branch needs the full detail.
**Never emit ROOT_CAUSE_IDENTIFIED without a failing probe that matches
the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

Deep-dive detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when this branch needs the full detail.

### Step 1: Symptom entry — pick the diagnostic branch

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

### Step 2: Consumer rate and fetch tuning

Symptom: RecordsLagMax climbing uniformly across partitions.
BytesInPerSec exceeds ConsumptionRate (BytesOutPerSec).

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

#### 2a: Consumer processing-bound

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CONSUMER_RATE`.

#### 2b: Consumer fetch-bound (micro-batch stall)

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CONSUMER_FETCH_TUNING`. Fix:
Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

### Step 3: Partition skew

Symptom: RecordsLagMax concentrated on one or few partitions; other
partitions near-zero lag. Consumer-group members are unevenly loaded.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PARTITION_SKEW`. Fix:
Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

### Step 4: ISR shrink — under-replicated partitions

Symptom: `UnderReplicatedPartitions > 0`, `ISRShrink` events,
possibly `OfflinePartitions > 0`.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Check the broker-level root cause of ISR shrink:

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Common ISR shrink causes:

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ISR_SHRINK`. Fix:
Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

### Step 5: Broker saturation

Symptom: CpuUser > 80%, disk usage > 85%, or
NetworkProcessorAvgIdlePercent < 0.3 on one or more brokers.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: BROKER_SATURATION`. Fix:
scale broker type, add brokers, add storage, or reduce load (retention,
compaction).

### Step 6: Producer config

Symptom: BytesInPerSec burst, or producer errors, or throughput lower
than expected. Consumer lag is a side effect of producer misbehaviour.

Key producer configs to check (from the producer application config):

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PRODUCER_CONFIG`.

### Step 7: Partition parallelism ceiling

Symptom: Consumer group members == partition count. Lag climbing
uniformly. Adding consumers does not help.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

If `members == partition_count`, the group has reached parallelism
ceiling. No additional consumer can receive a partition.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: PARTITION_PARALLELISM`. Fix:
Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

### Step 8: MSK Connect lag

Symptom: Lag on a connector-managed pipeline (source or sink).
Consumer group metrics are clean; the lag is in the connector.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MSK_CONNECT_LAG`. Fix:
increase `tasks.max`, scale the connector worker config, or address the
sink/source bottleneck.

### Step 9: MSK Serverless throttling

Symptom: MSK Serverless cluster; lag on specific partitions;
`ConsumedReadThroughput` or `ConsumedWriteThroughput` throttle.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MSK_SERVERLESS_THROTTLE`.
Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

### Step 10: Rebalance storm

Symptom: Lag sawtooth pattern; rebalance events correlate with spikes;
consumer logs show `Member ... sending JoinGroup request` frequently.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Consumer-side config to check:

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: REBALANCE_STORM`. Fix:
Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

### Step 11: ZooKeeper issues (ZK-based clusters only)

Symptom: ZooKeeper-based MSK cluster; `ZookeeperRequestLatencyMs` spike;
`ExpiredSessions`; controller instability; cascading leader elections.

Probe commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when this branch needs the full detail.

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: ZOOKEEPER_ISSUE`. Fix:
Pattern table and fixes moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when this branch needs the full detail.

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

Full example block moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when this branch needs the full detail.

### Worked example — Consumer fetch tuning on low-volume topic

Full example block moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when this branch needs the full detail.

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

Deep-dive detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when this branch needs the full detail.

## Deep reference: MSK lag layer model

Metric tables moved verbatim to [references/consumer-lag-metric-reference.md](references/consumer-lag-metric-reference.md).
Acks/ISR/cluster-mode matrices moved to [references/cluster-mode-and-partition-reference.md](references/cluster-mode-and-partition-reference.md).


## Recent AWS features (2024-2026)

Deep-dive detail moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when this branch needs the full detail.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples moved from this SKILL.md
- [references/error-handling.md](references/error-handling.md) — short-circuit, symptom-entry, and per-step pattern/fix tables moved from this SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight and per-step probe commands moved from this SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 gotchas, mindset/philosophy, remediation guidance, and recent AWS features moved from this SKILL.md
- [references/consumer-lag-metric-reference.md](references/consumer-lag-metric-reference.md) — CloudWatch metric semantics and fetch tuning matrices
- [references/cluster-mode-and-partition-reference.md](references/cluster-mode-and-partition-reference.md) — cluster-mode, ISR, and partition strategy rules

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

