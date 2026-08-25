# Elasticache Cost Optimizer — advanced patterns (load on demand)

Expert-knowledge deep dives, edge cases, and recent features, moved verbatim from SKILL.md.

## Step-0 non-obvious behaviours (moved from SKILL.md lines 186-239)


- **Graviton (r6g/r7g) is a flat ~20% price cut vs m5/r5, not a
  performance trade-off.** The r6g and r7g generations use AWS Graviton
  processors; for Redis and Memcached workloads they deliver equivalent
  or better throughput at ~20% lower hourly cost. There is no reason to
  stay on m5/r5 unless a specific library or module lacks ARM support.

- **Redis EngineCPUUtilization is the engine's own CPU, not the OS
  total.** Redis is single-threaded for command processing; a node with
  8 vCPU but EngineCPUUtilization avg=60% is near saturation on one
  core. Downsize only when EngineCPUUtilization has clear headroom. For
  Memcached, use CPUUtilization (the engine uses all cores).

- **Each Redis replica is a full node billed at the same hourly rate.**
  ReplicasForShard=2 means 3 nodes per shard (1 primary + 2 replicas).
  The cost scales linearly: 3 shards × 3 nodes = 9 nodes. Most read-
  heavy workloads need only 1 replica per shard for failover; additional
  replicas are only justified when read QPS exceeds a single replica's
  capacity.

- **AOF (append-only file) persistence adds write amplification cost.**
  Every write is appended to the AOF on disk; for high-write workloads,
  this consumes network and I/O that could otherwise serve clients. AOF
  is billed as part of the node (no separate storage charge), but the
  performance tax may force a larger node than otherwise needed. RDB
  snapshots are periodic and lighter. If the cache is truly ephemeral,
  disable persistence entirely.

- **ElastiCache Serverless bills per-GB-hour of data and per-vCPU-hour
  of compute, with no minimum capacity fee.** A serverless cache sitting
  at 1 GB overnight pays only for 1 GB-hour. Provisioned nodes bill the
  full node-hour regardless of usage. The break-even is when the
  workload's steady-state data + compute exceeds ~60-70% of an
  equivalent provisioned node's cost.

- **Reserved Nodes are size-flexible within a family for Redis OSS.** A
  `cache.r6g.large` Redis RN applies to any `cache.r6g.*` Redis node of
  equal or smaller size. Memcached RNs are NOT size-flexible — they are
  tied to the specific node type purchased. Use `modify-reserved-cache-
  nodes-offering` to exchange an unused RN for a different offering
  within the same family (no penalty, pro-rated).

- **Data tiering (r6gd/r7gd) uses SSD-backed cold storage for values
  below a configurable threshold.** This halves the effective cost for
  large datasets with a cold tail (e.g., session stores where 80% of
  keys are inactive). The tiered nodes cost ~10% more per hour but hold
  2x the effective data, so per-GB cost drops ~45%.

- **Cluster mode (sharding) adds a cost: each shard is a full primary +
  replicas.** A 3-shard cluster with 1 replica each = 6 nodes. Sharding
  is for capacity (data doesn't fit one node) or throughput (single
  core saturated), not cost savings. If the dataset fits in one large
  node, non-cluster mode with 1 replica (2 nodes) is cheaper than 3
  shards × 1 replica (6 nodes).

## persistence deep dive (Step 9) (moved from SKILL.md lines 456-460)

AOF persists every write; RDB takes periodic snapshots. For a cache
that is rebuilt from the primary database on restart (e.g., session
store with DB backing), disable persistence entirely — the cache does
not need its own durability.


## the 60-second bill triage (moved from SKILL.md lines 650-672)


When handed an ElastiCache bill and asked "why is this so high?", run
this 60-second triage before deep-diving any single dimension:

1. **Pull CE ElastiCache USAGE_TYPE breakdown.** If nodes are on m5/r5
   generation, the Graviton migration (Step 5) is the first lever —
   flat ~20% cut.
2. **Pull cluster node types + shard count.** A cluster on r6g with
   EngineCPU < 20% = right-size opportunity (Step 4).
3. **Pull replica count per shard.** ReplicasPerShard > 1 with read
   QPS well under a single replica's capacity = topology waste
   (Step 7).
4. **Pull RN inventory.** Long-running clusters On-Demand with no RN =
   RN opportunity (Step 8).
5. **Pull persistence mode.** AOF on an ephemeral cache = persistence
   overhead (Step 9). RDB with long retention on a small dataset =
   backup cost.
6. **Pull Serverless vs provisioned split.** Provisioned clusters with
   overnight idle > 50% = Serverless candidate (Step 6).

If any of the six checks hits, deep-dive the corresponding step. If all
six pass, the cluster is likely ALREADY_OPTIMAL — verify with the full
ordered process.

## recent AWS features (2024-2026) (moved from SKILL.md lines 712-732)


- **ElastiCache Serverless (2024):** Auto-scaling, no node management.
  Per-GB-hour data + per-vCPU-hour compute billing. Break-even against
  provisioned at ~30% avg utilisation; cheaper for variable workloads.
- **Graviton-based nodes — cache.r7g generation (2024-2025):** Latest
  ARM-based nodes; ~8% cheaper than r6g, ~20-33% cheaper than m5/r5.
  Full Redis and Memcached engine support.
- **Data tiering — cache.r6gd / r7gd (2023-2024):** SSD-backed cold
  data offload for large datasets. Halves effective per-GB cost for
  workloads with a cold tail (e.g., session stores). Configurable
  tiering threshold.
- **ElastiCache for Redis 7.2+ (2024):** Native Redis functions,
  ACL improvements, and Sharded Pub/Sub. Verify RN product-description
  matches the new engine version before purchase.
- **Global Datastore cross-region (2024-2025):** Multi-region
  replication for Redis. Each secondary region bills full node cost;
  right-size DR-region clusters independently.
- **Reserved Node exchange via modify-reserved-cache-nodes-offering
  (2024+):** Exchange an active RN for a different offering within
  the same family — no penalty, pro-rated. Use when migrating between
  node generations with an active RN.
