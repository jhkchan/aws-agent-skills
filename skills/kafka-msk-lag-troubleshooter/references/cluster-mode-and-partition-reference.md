# MSK Cluster Mode and Partition Strategy Reference

Supplementary reference for the Kafka MSK Lag Troubleshooter skill.
Loaded on-demand when a diagnostic needs cluster-mode differences
(Provisioned vs Serverless), partition strategy details, ISR and
replication health rules, or MSK Connect configuration guidance.

## MSK Provisioned vs Serverless comparison

| Dimension | Provisioned | Serverless |
|---|---|---|
| Broker management | Customer chooses broker type and count | AWS manages; auto-scales |
| Throttle basis | Broker resource (CPU, disk, network) | Per-partition CU (write, read) |
| Partition cap | Up to 307,200 per cluster (varies by broker type) | Up to 12,000 per cluster |
| Storage | Customer-managed EBS (adjustable per broker) | AWS-managed |
| ZooKeeper | ZK-based (Kafka 2.x/3.x) or KRaft (3.5+) | KRaft only (no ZK) |
| Scaling | Manual broker type update or add brokers | Automatic (partitions auto-scale) |
| Pricing | Per-broker-hour + storage | Per-CU (write CU + read CU) |
| Diagnostic focus | Broker-level CloudWatch (CPU, disk, network) | Partition-level CU throttle |

## MSK Serverless CU (Capacity Unit) model

MSK Serverless measures throughput in Capacity Units (CUs):

- **Write CU**: consumed by producer writes. Each partition has a
  per-partition write CU cap (region-specific; typically ~1 MB/s
  equivalent per partition).
- **Read CU**: consumed by consumer reads. Each partition has a
  per-partition read CU cap.
- **Cluster CU cap**: the aggregate across all partitions. Serverless
  auto-scales partitions (up to 12,000), but a single hot partition
  is throttled at its individual CU cap regardless of cluster capacity.

### Serverless throttle diagnosis

When `Throttle > 0` on a Serverless cluster:

1. Check which partition is hot (per-partition throughput via client
   metrics or CloudWatch `BytesInPerSec` with partition dimension).
2. Check `ConsumedWriteThroughput` or `ConsumedReadThroughput` against
   the partition CU cap.
3. The fix is partition-level scale-out (add partitions to the topic;
   re-key to redistribute the hot partition).

## Partition strategy

### Partition count and consumer parallelism

- A consumer group can have at most `partition_count` active consumers.
- The N+1th consumer is permanently idle.
- To increase parallelism: increase partitions (note: breaks key
  ordering for keyed messages; existing data stays on old partitions).

### Partition count sizing guidelines

| Workload profile | Recommended partitions | Rationale |
|---|---|---|
| Low volume (< 1 MB/s) | 1-3 per consumer | Minimal overhead |
| Medium volume (1-10 MB/s) | 3-6 per consumer | Allows consumer scaling |
| High volume (10-100 MB/s) | 6-12 per consumer | Parallelism headroom |
| Very high volume (> 100 MB/s) | 12+ per consumer | Scale-out consumer fleet |

### Key-based partitioning

The default partitioner: `partition = hash(key) % partition_count`.

- Same key always goes to the same partition → guarantees per-key
  ordering.
- A hot key (one key generating disproportionate traffic) causes
  partition skew → one partition is overloaded.
- Adding partitions changes the hash mapping → per-key ordering
  breaks for new messages.

### Re-keying for skew mitigation

| Strategy | How | Effect |
|---|---|---|
| Compound key | `device-id + epoch-minute` | Distributes hot key across partitions over time |
| Custom partitioner | Implement `Partitioner` interface; round-robin hot keys | Programmatically spread load |
| Salting | Prepend random suffix to key `device-id-N` where N is random | Random distribution; breaks ordering |

## ISR (In-Sync Replicas) health

### How ISR works

- Each partition has a leader and N-1 followers (N = replication
  factor).
- The ISR is the set of replicas that are fully caught up with the
  leader (`replica.lag.time.max.ms`, default 30 seconds on MSK).
- If a follower falls behind, it is removed from the ISR
  (`ISRShrink` event).
- When it catches up again, it is added back (`ISRExpand` event).

### `min.insync.replicas` and `acks=all`

| Configuration | Write succeeds when | Write fails when |
|---|---|---|
| RF=3, min.insync.replicas=2, acks=all | ISR ≥ 2 | ISR < 2 (1 broker fails + 1 slow follower) |
| RF=3, min.insync.replicas=1, acks=all | ISR ≥ 1 | All replicas fail (data loss risk) |
| RF=2, min.insync.replicas=2, acks=all | ISR = 2 (always) | 1 broker fails (no tolerance) |
| RF=3, acks=1 | Leader writes only | Leader fails (no ack) |

The recommended MSK production configuration: `RF=3`,
`min.insync.replicas=2`, `acks=all`. This tolerates one broker failure
without data loss.

### ISR shrink root causes

| Cause | Metric signal | Fix |
|---|---|---|
| Broker disk full (> 85%) | DiskUsage > 85%; DiskKBWrttnPerSec near limit | Add storage; reduce retention |
| Broker CPU saturated | CpuUser > 80% | Scale broker type; add brokers |
| Broker network saturated | NetworkProcessorAvgIdlePercent < 0.3 | Scale broker type |
| Long GC pause on follower | JVM GC logs; ISRShrink correlates with GC events | Tune JVM heap/GC |
| `replica.lag.time.max.ms` too aggressive | Follower catches up eventually but is removed first | Raise `replica.lag.time.max.ms` |
| `unclean.leader.election.enable=true` | Out-of-sync follower becomes leader | Keep `false` (MSK default) |

## Consumer group rebalance

### Rebalance triggers

| Trigger | How to detect | Fix |
|---|---|---|
| Consumer crash / OOM | Consumer app logs; `RebalanceRate` spike | Fix consumer stability |
| Long GC > session.timeout.ms | JVM GC logs | Tune GC |
| Processing time > max.poll.interval.ms | `time-between-polls` metric | Lower `max.poll.records` or speed up processing |
| Rolling deployment without static membership | Deploy timeline correlates with rebalance | Enable static membership |
| Consumer join/leave churn | Consumer logs show JoinGroup frequency | Enable static membership; cooperative rebalance |

### Static membership

Static membership (`group.instance.id`) gives each consumer a stable
identity. On restart, the consumer reclaims its partitions without a
full group rebalance — as long as it returns within
`session.timeout.ms`.

```properties
# Consumer config
group.instance.id=consumer-pod-1
session.timeout.ms=60000   # give time for restart
```

### Cooperative rebalance

The `CooperativeStickyAssignor` incrementally reassigns partitions
during rebalance, avoiding the stop-the-world pause:

```properties
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
```

## MSK Connect configuration

### Source connector lag

A source connector (Debezium, S3 Source, Kinesis Source) reads from
an external system and writes to Kafka. Lag = the connector is not
polling the source fast enough.

| Metric | Signal | Fix |
|---|---|---|
| `SourceTaskRecordPollRate` low | Source system slow or tasks under-provisioned | Increase `tasks.max`; scale worker |
| `TaskFailures > 0` | Connector task crashed | Check worker logs; common: auth failure, schema registry |
| `RecordLag` climbing | Connector behind source | Scale connector; increase `tasks.max` |

### Sink connector lag

A sink connector (S3 Sink, Elasticsearch Sink, Redshift Sink) reads
from Kafka and writes to an external system. Lag = the connector is
not writing to the sink fast enough.

| Metric | Signal | Fix |
|---|---|---|
| `SinkTaskRecordSendRate` low | Sink destination slow (S3, ES throttle) | Scale connector; check sink-side limits |
| `SinkTaskRecordPutFailures > 0` | Sink rejecting writes | Check destination permissions and capacity |
| `RecordLag` climbing | Connector behind Kafka | Scale connector; increase `tasks.max` |

### Connector auto-scaling

MSK Connect supports auto-scaling based on:
- `WorkerCpuUtilization` (scale when CPU > threshold)
- `WorkerMemoryUtilization`

If auto-scaling is not configured, the connector has a fixed worker
count and will not add capacity under load.

## KRaft vs ZooKeeper mode

| Dimension | ZooKeeper mode | KRaft mode |
|---|---|---|
| Metadata management | External ZK quorum (3 or 5 nodes) | Internal KRaft quorum (broker-embedded controllers) |
| Failure mode | ZK session expiry → controller failover | No ZK; controller quorum self-manages |
| Metrics | `ZooKeeperRequestLatencyMs`, `SessionExpireCount` | `KafkaController.*` metrics |
| MSK support | Kafka 2.x, 3.x (ZK-based) | Kafka 3.5+ (MSK with KRaft, 2024+) |
| Diagnostic branch | ZOOKEEPER_ISSUE applies | ZOOKEEPER_ISSUE does NOT apply; skip entirely |

On KRaft-mode clusters, the ZK metrics do not exist. Do not attempt to
diagnose ZK issues on a KRath cluster; route to BROKER_SATURATION or
controller metrics instead.

## Deep reference — producer acks, ISR/min.insync.replicas, Provisioned vs Serverless throttle model (moved from SKILL.md)

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
