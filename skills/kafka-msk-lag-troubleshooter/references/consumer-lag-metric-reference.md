# MSK Consumer Lag Metric Reference Guide

Supplementary reference for the Kafka MSK Lag Troubleshooter skill.
Loaded on-demand when a diagnostic needs CloudWatch metric semantics,
per-partition lag distribution detail, or broker-level saturation
thresholds.

## AWS/Kafka namespace — broker and topic metrics

### Lag metrics

| Metric | Dimensions | What it measures | Diagnostic use |
|---|---|---|---|
| `RecordsLagMax` | Cluster, Topic | Maximum records-lag across all partitions in a consumer group | Primary lag signal; climbing = consumer behind. NOTE: this is the MAX, not the average. |
| `RecordsLag` | Cluster, Topic, Partition (via client metrics) | Per-partition records-lag | Skew detection; compare per-partition values to identify hot partitions |
| `MaxOffsetLag` | Cluster, Topic | Maximum offset-lag across partitions | Lag measured in offsets (not records); useful when records are large |

### Throughput metrics

| Metric | Dimensions | What it measures |
|---|---|---|
| `BytesInPerSec` | Cluster, Topic | Producer write rate (bytes/sec) |
| `BytesOutPerSec` | Cluster, Topic | Consumer read rate (bytes/sec) |
| `MessagesInPerSec` | Cluster, Topic | Messages/sec written by producers |
| `ConsumedReadThroughput` | Cluster, Topic (Serverless) | MSK Serverless read CU consumed |
| `ConsumedWriteThroughput` | Cluster, Topic (Serverless) | MSK Serverless write CU consumed |

### Broker health metrics

| Metric | Dimensions | Threshold | Diagnostic use |
|---|---|---|---|
| `CpuUser` | Cluster, Broker | > 80% sustained | Broker CPU saturation |
| `CpuSystem` | Cluster, Broker | > 20% sustained | Kernel-time saturation |
| `DiskKBReadPerSec` | Cluster, Broker | Near device limit | Disk read saturation |
| `DiskKBWrttnPerSec` | Cluster, Broker | Near device limit | Disk write saturation |
| `DiskUsage` | Cluster, Broker | > 85% | Disk filling; ISR shrink risk |
| `NetworkProcessorAvgIdlePercent` | Cluster, Broker | < 0.3 (30%) | Network thread saturation |
| `NetworkRxDrop` / `NetworkTxDrop` | Cluster, Broker | > 0 | Packet drops; NIC or buffer exhaustion |

### ISR and replication metrics

| Metric | Dimensions | What it measures | Diagnostic use |
|---|---|---|---|
| `UnderReplicatedPartitions` | Cluster | Partitions with ISR < RF | > 0 = replica degradation; ISR shrink in progress |
| `OfflinePartitions` | Cluster | Partitions with no leader | > 0 = immediate escalation; partial outage |
| `ISRShrink` | Cluster | ISR membership shrink events | Replica removed from ISR; correlate with broker health |
| `ISRExpand` | Cluster | ISR membership expand events | Replica rejoined ISR; recovery signal |
| `ActiveControllerCount` | Cluster | Number of active controllers | Should be exactly 1; 0 or 2+ = controller instability |
| `LeaderElectionRate` | Cluster | Leader election events/sec | High rate = instability; correlate with ZK or broker restarts |

### Consumer group metrics

| Metric | Dimensions | What it measures |
|---|---|---|
| `RebalanceRate` | Cluster, ConsumerGroup | Rebalance events per second |
| `RebalanceLatencyAvg` | Cluster, ConsumerGroup | Average time to complete a rebalance |
| `ConsumedBytesPerSec` | Cluster, ConsumerGroup | Bytes consumed per second by the group |
| `CommitLatencyInMs` | Cluster, ConsumerGroup | Offset commit latency |

### ZooKeeper metrics (ZK-based clusters only)

| Metric | What it measures | Diagnostic use |
|---|---|---|
| `ZooKeeperRequestLatencyMs` | ZK request latency | Spike = ZK instability; cascading leader elections |
| `SessionExpireCount` | ZK session expirations | > 0 = broker losing ZK session; controller failover risk |
| `ZooKeeperDisconnects` | ZK connection drops | Network partition between broker and ZK |

### MSK Serverless-specific metrics

| Metric | What it measures | Diagnostic use |
|---|---|---|
| `Throttle` | CU throttle count | > 0 = per-partition CU throttle; check partition-level CU |
| `ConsumedReadThroughput` | Read CU consumed | At cap = read throttle |
| `ConsumedWriteThroughput` | Write CU consumed | At cap = write throttle |
| `ProvisionedThroughput` | Provisioned CU | Compare to consumed; if provisioned = consumed, throttle is near |

NOTE: MSK Serverless clusters do NOT expose `CpuUser`, `DiskKB*PerSec`,
or `ZooKeeper*` metrics. The cluster auto-manages these. Diagnostic
focus is on `Throttle`, `ConsumedReadThroughput`, and
`ConsumedWriteThroughput`.

## AWS/MSKConnect namespace — connector metrics

| Metric | Dimensions | What it measures |
|---|---|---|
| `RecordLag` | ConnectorName | Connector lag (records behind source) |
| `SourceTaskRecordPollRate` | ConnectorName | Source connector poll rate (records/sec) |
| `SinkTaskRecordSendRate` | ConnectorName | Sink connector send rate to destination |
| `SinkTaskRecordPutFailures` | ConnectorName | Failed sends to destination |
| `TaskStartUps` / `TaskFailures` | ConnectorName | Connector task lifecycle events |
| `WorkerMessageDeliveryFailures` | ConnectorName | DLQ or delivery failure count |

## Per-partition lag distribution

`RecordsLagMax` reports the single highest-lag partition. To diagnose
skew, request the per-partition lag distribution:

```bash
# Via kafka-consumer-groups.sh (requires client machine with access)
kafka-consumer-groups.sh \
  --bootstrap-server <broker-endpoint> \
  --describe \
  --group <consumer-group>
```

Output columns:
- `TOPIC`: topic name
- `PARTITION`: partition number
- `CURRENT-OFFSET`: last committed offset
- `LOG-END-OFFSET`: current high-water mark (latest offset)
- `LAG`: `LOG-END-OFFSET - CURRENT-OFFSET`
- `CONSUMER-ID`: consumer instance assigned to this partition

Interpretation:
- All partitions similar lag → rate problem (CONSUMER_RATE or
  CONSUMER_FETCH_TUNING).
- One partition dominates → skew problem (PARTITION_SKEW).
- Lag spikes correlate across all partitions simultaneously → rebalance
  (REBALANCE_STORM) or broker restart.

## Broker saturation thresholds (MSK Provisioned)

| Resource | Warning | Critical | Action |
|---|---|---|---|
| CpuUser | > 60% sustained | > 80% sustained | Scale broker type; add brokers |
| Disk usage | > 70% | > 85% | Add storage; reduce retention |
| Disk I/O | > 70% of device limit | > 90% of device limit | Scale to faster disk; add brokers |
| NetworkProcessorAvgIdlePercent | < 50% | < 30% | Scale broker type; increase num.network.threads |
| Heap usage after GC | > 70% of Xmx | > 85% of Xmx | Tune JVM heap / GC; scale broker type |

## MSK Provisioned broker type reference

| Broker type | vCPU | RAM (GB) | Typical throughput | Network |
|---|---|---|---|---|
| kafka.t3.small | 2 | 2 | Low (< 50 MB/s in) | Up to 5 Gbps |
| kafka.m5.large | 2 | 8 | Medium (< 100 MB/s in) | Up to 10 Gbps |
| kafka.m5.xlarge | 4 | 16 | High (< 200 MB/s in) | Up to 10 Gbps |
| kafka.m5.2xlarge | 8 | 32 | Very high (< 400 MB/s in) | Up to 10 Gbps |
| kafka.m5.4xlarge | 16 | 64 | Enterprise (< 800 MB/s in) | Up to 10 Gbps |
| kafka.m7g.large | 2 | 8 | Medium (Graviton) | Up to 12 Gbps |
| kafka.m7g.2xlarge | 8 | 32 | Very high (Graviton) | Up to 15 Gbps |

## Consumer fetch tuning quick reference

| Parameter | Default | Effect | When to change |
|---|---|---|---|
| `fetch.min.bytes` | 1 | Min bytes per fetch request | Raise for high-volume topics (1 MB+); keep at 1 for low-volume |
| `fetch.max.wait.ms` | 500 | Max wait if fetch.min.bytes not met | Lower to 100 for low-latency low-volume; keep default for high-volume |
| `fetch.max.bytes` | 57671680 (55 MB) | Max bytes per fetch response | Raise if partitions are many and each has large messages |
| `max.poll.records` | 500 | Max records per poll() | Raise if processing is fast; lower if max.poll.interval.ms is tight |
| `max.poll.interval.ms` | 300000 (5 min) | Max time between poll() calls | Raise if processing a batch takes long (prevents rebalance kick-out) |

## Producer throughput quick reference

| Parameter | Default | Effect | When to change |
|---|---|---|---|
| `acks` | all (on MSK default config) | Write durability | `acks=1` for latency-sensitive; `acks=all` for durability |
| `batch.size` | 16384 (16 KB) | Max batch size per partition | Raise to 131072+ for throughput |
| `linger.ms` | 0 | Wait time to batch | Raise to 5-20 for batching (trades latency for throughput) |
| `compression.type` | none | Batch compression | Set to `lz4` or `zstd` for network/disk efficiency |
| `buffer.memory` | 33554432 (32 MB) | Producer send buffer | Raise if producer blocks on max.block.ms |
| `max.in.flight.requests.per.connection` | 5 | Concurrent unacknowledged batches | Keep ≤ 5 with idempotence; higher risks reordering without idempotence |
