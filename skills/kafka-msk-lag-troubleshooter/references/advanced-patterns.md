# Advanced patterns — kafka-msk-lag-troubleshooter

Step-0 gotchas, mindset/philosophy deep dives, remediation guidance, and recent AWS features, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Quick start — symptom→layer map and key knobs (moved from SKILL.md)

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

## Mindset (moved from SKILL.md)

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

## Philosophy — what separates a senior MSK engineer (moved from SKILL.md)

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

## Diagnostic tree traversal rules (moved from SKILL.md)

The diagnostic tree is symptom-driven. Pick the entry point based on the
observed metric pattern, then walk the layer-specific probes in order.
Each layer ends with either a positive root-cause confirmation (failing
probe that matches the symptom) or a pass that moves to the next layer.

## Step 0: Non-obvious behaviours that change diagnosis (moved from SKILL.md)

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

## Remediation guidance (moved from SKILL.md)

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

## Recent AWS features (2024-2026) (moved from SKILL.md)

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
