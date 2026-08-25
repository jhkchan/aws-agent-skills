# Error handling — kafka-msk-lag-troubleshooter

Short-circuit tables and per-step symptom/cause/fix tables, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Cluster-state short-circuit (moved from SKILL.md)

| Cluster state / metric | Effect on diagnosis |
|---|---|
| `ACTIVE` + no recent maintenance operation | Proceed with symptom-driven diagnosis. |
| `MAINTENANCE` / `UPDATING` | A broker rotation or version upgrade is in flight. Consumers may see brief leader elections and rebalances. Note in REMEDIATION; wait for `ACTIVE` before drawing conclusions. |
| `FAILED` | The cluster is in a failed state. Escalate to AWS Support; customer-side consumer tuning will not help. |
| UnderReplicatedPartitions > 0 sustained | ISR shrink is in progress; jump to ISR_SHRINK diagnosis. Producer may already be failing if `acks=all` and ISR < `min.insync.replicas`. |
| OfflinePartitions > 0 | One or more partitions have no available leader. The cluster is in a partial outage. Escalate immediately. |
| ZooKeeper-based cluster (`zookeeper.3` or earlier), ZookeeperRequestLatencyMs spike | ZK instability cascades into controller failures and leader elections; check ZOOKEEPER_ISSUE before consumer-side diagnosis. |

## Consumer-group-state short-circuit (moved from SKILL.md)

| Consumer group state | Effect |
|---|---|
| `STABLE` | Group has reached steady-state partition assignment. Proceed with rate-based diagnosis. |
| `PREPARING_REBALANCE` / `COMPLETING_REBALANCE` | Group is mid-rebalance; consumption is paused. If this state persists or recurs, route to REBALANCE_STORM. |
| `DEAD` | The group has no active members; partitions are unassigned and lag will climb. Check whether consumers crashed. |
| `EMPTY` | Group has no members and no offsets; this is normal for a new or reset group. |

## Malformed input short-circuit (moved from SKILL.md)

If the input is malformed (missing cluster ARN, absent topic, absent
consumer group name, no metrics snapshot for offline classification),
emit INSUFFICIENT_DATA with the specific gaps.

## Step 1: Symptom entry — branch map (moved from SKILL.md)

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

## Step 2b: Fetch config patterns (moved from SKILL.md)

| Config pattern | Effect |
|---|---|
| `fetch.min.bytes = 10485760` (10 MB) on a low-volume topic | Consumer waits up to `fetch.max.wait.ms` each poll cycle; effective poll rate drops; lag climbs on low-volume partitions |
| `fetch.max.wait.ms = 5000` | Consumer waits up to 5 seconds per fetch; on bursty traffic this adds 5 s of latency per batch |
| `max.poll.records = 10` | Consumer fetches tiny batches; overhead per poll dominates; throughput drops |
| `fetch.min.bytes = 1` (default) on a high-volume topic | Consumer fetches too frequently; network overhead rises; may not keep up with producer on very high-volume topics |

## Step 2b: Fix detail (moved from SKILL.md)

align fetch tuning to topic volume — low-volume topics want
`fetch.min.bytes=1`, `fetch.max.wait.ms=100`; high-volume topics
benefit from `fetch.min.bytes=1048576` (1 MB) or higher.

## Step 3: Skew patterns (moved from SKILL.md)

| Pattern | Cause |
|---|---|
| 80% of messages on one partition; key is `device-id` with one device bursting | Key skew — default partitioner hashes the key; one key = one partition |
| Skew across brokers but not partitions | Broker-level leadership imbalance; preferred leader election needed |
| Skew appeared after adding partitions | Hash mapping changed; existing keys redistributed unevenly |

## Step 3: Fixes (moved from SKILL.md)

- Re-key with a compound key (e.g., `device-id + epoch-minute`) to
  distribute load.
- Or use a custom partitioner that round-robins hot keys.
- Or increase partition count AND accept that existing keyed data
  stays on old partitions (only new data redistributes).

## Step 4: Common ISR shrink causes (moved from SKILL.md)

| Cause | How to verify |
|---|---|
| Broker disk full (>85%) | Disk usage metric; broker log directory at capacity |
| Broker network saturated | NetworkProcessorAvgIdlePercent < 0.3 |
| Broker CPU saturated | CpuUser > 80% sustained |
| Broker GC pause (long stop-the-world) | JVM GC logs; `kafka.server:type=BrokerTopicMetrics` latency spike |
| `replica.lag.time.max.ms` too aggressive | Follower cannot fetch within the window; gets removed from ISR |
| `unclean.leader.election.enable=true` with a slow follower | Out-of-sync follower becomes leader; data loss + ISR chaos |

## Step 4: Fixes (moved from SKILL.md)

- Broker disk full: add storage (MSK broker storage update) or delete
  old log segments (topic retention).
- Broker CPU/network: scale to a larger broker type (MSK broker type
  update).
- `replica.lag.time.max.ms` too low: raise to accommodate follower
  fetch latency.
- `min.insync.replicas` check: if ISR < min.insync.replicas and
  acks=all, producer fails; either fix the broker or temporarily
  lower min.insync.replicas (with data-loss risk).

## Step 5: Saturation thresholds and fixes (moved from SKILL.md)

| Resource | Threshold | Fix |
|---|---|---|
| CpuUser | > 80% sustained | Scale broker type (e.g., kafka.m5.large → kafka.m5.xlarge); add brokers |
| Disk usage | > 85% | Add storage; reduce retention; compact topics |
| NetworkProcessorAvgIdlePercent | < 0.3 (30%) | Scale broker type (network thread bottleneck); increase `num.network.threads` |
| Disk queue depth | high `kBRead/s` + `kBWrttn/s` near device limit | Scale to faster disk (MSK provisioned IOPS); add brokers |

## Step 6: Producer config effects (moved from SKILL.md)

| Config | Effect on lag |
|---|---|
| `acks` | `acks=0` — fire and forget; high throughput but data loss on broker failure. `acks=1` — leader write only. `acks=all` — ISR write; safest, slowest. Mismatch with `min.insync.replicas` causes NOT_ENOUGH_REPLICAS. |
| `batch.size` | Small batch (e.g., 16384 = 16 KB default) on high-volume producer means too many small requests. Raise to 131072 (128 KB) or higher for throughput. |
| `linger.ms` | 0 (default) sends immediately. Raising to 5-20 ms batches more records per request, increasing throughput at the cost of latency. |
| `compression.type` | `none` (default) — no compression, more bytes. `lz4`, `snappy`, `zstd`, `gzip` — compressed batches; less network/disk but consumers must decompress. |
| `buffer.memory` | If too small, producer blocks on `max.block.ms`; throughput drops. Default 33554432 (32 MB). |
| `max.in.flight.requests.per.connection` | High value (e.g., 5+) improves throughput but risks reordering on retries if `enable.idempotence=false`. |

## Step 7: Fixes (moved from SKILL.md)

- Increase partition count (note: breaks key ordering for keyed
  messages; existing data stays on old partitions).
- Or increase per-consumer throughput (multi-threaded processing,
  async I/O).
- Or shard the topic into multiple topics and consumer groups.

## Step 8: Connector lag patterns (moved from SKILL.md)

| Connector pattern | Cause |
|---|---|
| Source connector (e.g., Debezium) lag; `SourceTaskRecordPollRate` low | Source DB slow; connector task under-provisioned; increase `tasks.max` |
| Sink connector (e.g., S3 Sink) lag; `SinkTaskRecordSendRate` low | Sink destination slow (S3, ES); increase `tasks.max`; check sink-side throttling |
| Connector task in `FAILED` state | Check connector worker logs; common causes: auth failure, schema registry unreachable, sink-side permission denied |
| Connector auto-scaling not triggering | `worker.microvolume.tasks` vs `worker.cpu.utilization` thresholds; MSK Connect auto-scaling needs explicit configuration |

## Step 9: Serverless CU model (moved from SKILL.md)

MSK Serverless CU (Capacity Units) are per-partition:
- Each partition has a write CU cap (default varies by region).
- Read CU is consumed per consumer read.
- A single hot partition hitting its CU cap is throttled even when the
  cluster overall has capacity.

## Step 9: Fixes (moved from SKILL.md)

Fix:
- Redistribute load across more partitions (add partitions to the
  topic; note Serverless supports up to 12,000 partitions per cluster).
- Reduce per-partition throughput by re-keying.
- For read throttle: reduce consumer poll rate or batch size;
  scale-out is limited by partition-level CU.

## Step 10: Consumer config effects (moved from SKILL.md)

| Config | Effect |
|---|---|
| `session.timeout.ms` (default 45000 on MSK) | If consumer GC pauses exceed this, broker considers the consumer dead and triggers rebalance |
| `heartbeat.interval.ms` (default 3000) | Must be < session.timeout.ms / 3; if heartbeats are missed, rebalance fires |
| `max.poll.interval.ms` (default 300000 = 5 min) | If processing a batch takes longer than this, consumer is kicked out of the group → rebalance |
| Static membership (`group.instance.id`) | Not set → every consumer restart triggers a rebalance. Set → consumer reclaims its partitions after restart without full rebalance |

## Step 10: Rebalance triggers (moved from SKILL.md)

| Rebalance trigger | How to verify |
|---|---|
| Consumer crash / OOM | Consumer application logs; `Errors` metric on consumer |
| Long GC pause > session.timeout.ms | JVM GC logs; `jvm.gc.pause` Micrometer metric |
| Processing time > max.poll.interval.ms | `time-between-polls` metric; reduce `max.poll.records` or speed up processing |
| Deployment rolling restart without static membership | Deploy timeline correlates with rebalance events |

## Step 10: Fixes (moved from SKILL.md)

- Enable static membership (`group.instance.id` per consumer instance).
- Raise `max.poll.interval.ms` if processing legitimately takes long.
- Tune GC to avoid stop-the-world pauses.
- Use cooperative rebalance protocol (`partition.assignment.strategy=
  CooperativeStickyAssignor`) to avoid stop-the-world rebalances.

## Step 11: ZK instability cascade (moved from SKILL.md)

ZK instability cascades: broker loses session → removed from cluster →
leader elections on all partitions it led → ISR fluctuations →
producer/consumer errors → lag.

## Step 11: ZK issue causes (moved from SKILL.md)

| ZK issue | Cause |
|---|---|
| ZK disk I/O bottleneck | ZK requires low-latency disk; shared with Kafka log directory contention |
| ZK ensemble size 3 with one node down | Quorum = 2; if another node is slow, writes stall |
| Network partition between broker and ZK | Check VPC routing, security groups, ENI |

## Step 11: Fixes (moved from SKILL.md)

- Escalate to AWS Support for ZK infrastructure issues (customer
  cannot modify ZK config on MSK).
- Migrate to KRaft mode (MSK with KRaft) to eliminate ZK entirely.
- Check broker-to-ZK network path.
