# Advanced Patterns — MSK Cost Optimizer

## Quick start — core heuristics

- **Graviton brokers (kafka.m7g) on Kafka 3.x are ~20% cheaper than the
  equivalent kafka.m5 generation.** Same vCPU and memory, full Kafka 3.x
  support. A cluster on `kafka.m5.large` ($0.276/h) migrates to
  `kafka.m7g.large` ($0.22/h) for ~20% off. Requires Kafka 3.x or later;
  Kafka 2.x does not support Graviton brokers.

- **MSK Serverless vs provisioned break-even is ~50 MB/s of ingress
  throughput.** Below 50 MB/s sustained, Serverless per-partition-hour +
  per-GB data pricing is usually cheaper. Above 50 MB/s steady, provisioned
  brokers are cheaper. Workloads with bursty traffic that idles for hours
  are prime Serverless candidates regardless of peak throughput.

- **Minimum 3 brokers for HA; more brokers are only justified by
  throughput or partition count.** A 6-broker cluster doing 10 MB/s total
  ingress is over-provisioned — 3 brokers can handle it with headroom.
  Kafka partitions must be distributed across brokers; the partition-to-
  broker ratio (aim < 400 partitions per broker) is the constraint.

- **EBS storage is the second-largest MSK cost after broker compute.**
  Each broker has an attached EBS volume. KafkaDataLogsDiskUsed below 30%
  means the volume is over-allocated. Storage auto-scaling (MSK storage
  auto-expand) or a manual right-size eliminates wasted EBS cost.

- **Log retention is the primary EBS cost driver over time.** A 7-day
  retention on a high-throughput topic consumes 7x the disk of a 1-day
  retention. Compacted topics (retention by key, not time) can reduce
  storage 10x for changelog or event-sourcing workloads.

## Mindset — MSK cost-structure fundamentals

MSK cost structure differs from databases in three ways: the cost is
dominated by broker compute + EBS storage (not per-request), partition
count adds broker overhead (metadata, leader election, rebalancing), and
data retention directly drives storage cost over time. The levers are
broker generation, broker count, EBS volume size, retention policy, and
Serverless fit. Most MSK waste comes from (a) legacy kafka.m5 brokers
that should be Graviton, (b) over-provisioned broker count for low-
throughput workloads, (c) oversized EBS volumes, or (d) long retention
on high-throughput topics that don't need it.

## Step 0: Non-obvious behaviours that change the recommendation

- **Graviton brokers require Kafka 3.x or later.** Kafka 2.x does not
  support Graviton (m7g/m6g) brokers. If the cluster is on Kafka 2.8 or
  earlier, the Graviton migration is gated on a Kafka version upgrade
  first. The upgrade itself is non-disruptive (rolling) but must be
  staged before the broker type change.

- **MSK broker count cannot be reduced without cluster recreation.**
  Kafka partition leadership is distributed across brokers; removing a
  broker requires reassigning its partitions first. MSK supports
  broker count changes via update-cluster but reducing below the
  original count requires creating a new cluster and migrating. Plan
  broker-count reduction as a blue/green migration, not an in-place
  change.

- **EBS storage can be increased online but not decreased.** MSK
  supports `update-broker-storage` to increase EBS volume size per
  broker (online, no downtime). Decreasing EBS size requires cluster
  recreation. If KafkaDataLogsDiskUsed < 30%, flag for the next
  blue/green migration rather than immediate reduction. Storage auto-
  scaling (MSK storage auto-expand) prevents over-allocation on new
  clusters.

- **MSK Serverless bills per partition-hour + per-GB data stored + per-
  PUT-hour.** There is no broker cost. A Serverless cluster with 10
  partitions, low throughput, and 5 GB data costs pennies per hour.
  The same workload on provisioned kafka.m5.large x 3 brokers costs
  $600+/month. The break-even is ~50 MB/s sustained ingress or ~1000
  partitions.

- **Partition count directly adds broker overhead.** Each partition has
  a leader, followers, and metadata that consumes broker CPU and memory.
  Kafka recommends < 4000 partitions per broker. Excessive partitions
  (e.g., 1000 partitions on a 3-broker cluster doing 1 MB/s) waste
  broker resources — the metadata overhead exceeds the data processing.
  Reducing partition count is an operational change (no direct cost)
  that can enable broker downsize.

- **Compacted topics reduce storage 10x for key-based workloads.** A
  compacted topic retains only the latest value per key, not all
  history. For changelog, event-sourcing, or state-store workloads,
  compaction can reduce disk usage from 500 GB to 50 GB, directly
  reducing EBS cost. Switch via topic-level `cleanup.policy=compact`.

- **MSK Express tier (2025+) provides high-throughput burstable brokers
  with credit-based performance.** Express brokers have a baseline
  throughput and burst credits for spikes. Cost is comparable to
  Standard provisioned but with better burst handling. Evaluate Express
  for workloads with variable throughput that don't justify more
  brokers full-time.

- **MSK with KRaft (2025+) eliminates ZooKeeper, reducing broker
  overhead.** KRaft mode uses an in-protocol consensus instead of
  separate ZooKeeper ensembles. This frees the broker CPU that was
  spent on ZooKeeper health checks and metadata sync, potentially
  enabling a broker downsize. KRaft is available on Kafka 3.5+ on MSK.

- **Log retention is the single biggest EBS cost driver.** A topic
  ingesting 10 MB/s with 7-day retention stores ~6 TB. With 1-day
  retention, it stores ~860 GB. The EBS cost difference at $0.08/GB-
  month is $400+/month for one topic. Always evaluate retention
  duration against the actual data-replay requirements.

## Expert heuristic — the 60-second triage

When handed an MSK bill and asked "why is this so high?", run this
60-second triage before deep-diving any single dimension:

1. **Pull CE MSK USAGE_TYPE breakdown.** If brokers are on kafka.m5
   generation, the Graviton migration (Step 5) is the first lever —
   flat ~20% cut (requires Kafka 3.x+).
2. **Pull broker count + total ingress.** Broker count > 3 with total
   ingress < 50 MB/s = broker-count reduction opportunity (Step 7).
3. **Pull KafkaDataLogsDiskUsed.** Disk used < 30% on 1 TB+ volumes =
   EBS over-allocation (Step 8). Enable auto-expand on new clusters.
4. **Pull retention per topic.** Retention > 168h on high-throughput
   non-compacted topics = retention-driven storage waste (Step 9).
5. **Pull partition count.** > 400 partitions/broker with low throughput
   = excessive partitions enabling broker downsize (Step 10).
6. **Pull Serverless vs provisioned split.** Provisioned clusters with
   ingress < 50 MB/s and idle periods = Serverless candidate (Step 6).

If any of the six checks hits, deep-dive the corresponding step. If all
six pass, the cluster is likely ALREADY_OPTIMAL — verify with the full
ordered process.

## Recent AWS features (2024-2026)

- **MSK Cluster Tier — Express (2025+):** High-throughput burstable
  broker tier with credit-based performance. Express brokers have a
  baseline throughput and burst credits for spikes. Evaluate for
  variable-throughput workloads that don't justify additional brokers
  full-time.
- **MSK with KRaft (2025+):** Eliminates ZooKeeper, using an in-protocol
  consensus (KRaft). Reduces broker overhead spent on ZooKeeper health
  checks and metadata sync, potentially enabling a broker downsize.
  Available on Kafka 3.5+ on MSK.
- **Graviton brokers — kafka.m7g (2024-2025):** ARM-based brokers ~20%
  cheaper than kafka.m5. Requires Kafka 3.x or later. Full Kafka feature
  parity including KRaft mode.
- **MSK Serverless (2022-2024 enhancements):** Auto-scaling partitions,
  no broker management. Per-partition-hour + per-GB data + per-PUT-hour
  pricing. Break-even against provisioned at ~50 MB/s sustained ingress.
- **MSK Cluster Linking (2024-2025):** Cross-cluster topic replication
  with offset preservation. Enables blue/green migrations for broker
  type and count changes without MirrorMaker2 overhead.
- **MSK storage auto-expand (2024):** Automatic EBS volume expansion
  when KafkaDataLogsDiskUsed exceeds threshold. Prevents volume
  exhaustion and enables starting with smaller volumes (right-sized
  from day one).

