# Topology and Tiering Guide — MemoryDB Cluster Deployer

Deep reference on MemoryDB shard/replica math, Multi-AZ failover
internals, data-tiering latency tradeoffs, ACL interactions, and the
MemoryDB vs ElastiCache boundary. Loaded on demand by the skill —
kept out of the main SKILL.md body so the provisioning procedure
stays scannable.

## Node type families

MemoryDB offers `db.r6g`, `db.r6gd` (data-tiering), and `db.r7g`
(latest Graviton) families. Avoid `t-series` burstable for production.

| Family | Optimized for | Use when |
|---|---|---|
| `db.r6g.large` ... `.24xlarge` | Memory, Graviton | General-purpose MemoryDB; production |
| `db.r6gd.large` ... `.24xlarge` | Memory + SSD tiering | Large datasets with hot/cold access pattern (cost optimization) |
| `db.r7g.large` ... `.24xlarge` | Memory, Graviton (latest) | New clusters; ~10% better perf over r6g |

**Memory by size (representative):**
- `db.r6g.large`: 13.10 GiB nominal
- `db.r6g.8xlarge`: 208.74 GiB nominal
- `db.r6g.16xlarge`: 417.05 GiB nominal
- `db.r6g.24xlarge`: 612.30 GiB nominal
- `db.r6gd.24xlarge`: 612.30 GiB RAM + ~1224 GiB SSD

**Graviton (r6g, r7g) note:** ~10-15% better price/performance over
previous gen. Default to Graviton for new clusters.

## Writer/reader scaling math

MemoryDB has cluster mode always-on. Writes scale with shards; reads
scale with shards × (1 + replicas).

```text
write_capacity = shards × node_write_baseline
read_capacity  = shards × (1 + replicas_per_shard) × node_read_baseline

# db.r6g.24xlarge (representative):
#   ~100k writes/sec per primary
#   ~100k reads/sec per node (primary or replica)

# 3 shards × 1 primary + 1 replica each:
#   write capacity = 3 × 100k = 300k writes/sec
#   read capacity  = 3 × 2 × 100k = 600k reads/sec
```

**Implication:** add shards to scale writes; add replicas per shard
to scale reads. Replicas do NOT add usable memory — they hold copies.

## Buffer cache budget (the 50% rule)

MemoryDB is memory-bound. The working set MUST fit in ~50% of the
node's nominal memory.

```text
usable_per_shard = node_memory × 0.50
# ~50% is the operating budget. Redis reserves the rest for:
#   - OS + Redis internal state
#   - Connection state + query buffers
#   - Copy-on-write overhead during snapshot/failover

total_usable = usable_per_shard × shards

# With data tiering (r6gd family):
#   hot_tier  = node_memory × 0.50   (in-memory; sub-ms)
#   cold_tier = ssd_size × 0.90      (SSD-backed; 100x-1000x latency)
```

### Worked sizing example

```text
Dataset: 1.5 TB total, hot/cold split ~30%/70%
Hot working set: 450 GB  -> must fit in memory
Cold set:        1050 GB -> SSD tier acceptable

Option A: no tiering (db.r6g.24xlarge, 612.30 GiB nominal)
  usable_per_shard = 612.30 × 0.50 = 306 GiB
  shards needed for 450 GB hot set = ceil(450 / 306) = 2 shards
  But total data (1.5 TB) needs to fit too: ceil(1500 / 306) = 5 shards
  5 shards × 1 replica = 10 nodes of db.r6g.24xlarge

Option B: with tiering (db.r6gd.24xlarge, 612 GiB RAM + 1224 GiB SSD)
  hot_budget  = 612 × 0.50 = 306 GiB per shard
  cold_budget = 1224 × 0.90 = 1101.6 GiB per shard
  shards for hot set  = ceil(450 / 306) = 2
  shards for cold set = ceil(1050 / 1101.6) = 1 (binding: 2 from hot)
  2 shards × 1 replica = 4 nodes of db.r6gd.24xlarge
  # 60% fewer nodes; cold-key latency is 100x-1000x
```

## Multi-AZ failover internals

- **Configuration endpoint is stable.** Always resolves to the
  cluster; clients route via MOVED/ASK redirection.
- **Failover is per-SHARD.** A 5-shard cluster can have up to 5
  simultaneous shard failovers during an AZ event.
- **Promotion time: ~10-30 seconds per shard** (replica promotion +
  endpoint update).
- **Data loss window: zero committed transactions.** MemoryDB writes
  to a Multi-AZ transaction log before acknowledging — a promoted
  replica sees all committed writes.
- **In-flight writes** during the failover window get connection
  errors and must be retried by the application.

### Anti-pattern: all shard primaries in one AZ

If all shard primaries happen to be in AZ-a (possible with poor AZ
placement), an AZ-a failure takes down ALL writes. MemoryDB attempts
to spread primaries across AZs, but verify placement after creation
via `describe-clusters --show-shard-node-info`.

### Recommended topologies

| Workload | Topology | Notes |
|---|---|---|
| Dev / test | 1 shard × 1 primary (no replicas) | No failover; functional testing |
| Small prod (read-heavy) | 2 shards × 1 primary + 1 replica | Multi-AZ failover |
| Mid prod (mixed) | 3-5 shards × 1 primary + 1 replica | Write + read scaling, Multi-AZ |
| Large prod (deep pipeline) | 5+ shards × 1 primary + 2 replicas | Read scaling for heavy fan-out |
| Large cost-optimized | 3 shards db.r6gd + data tiering | Hot/cold access pattern |

## Data tiering tradeoffs (deep detail)

Data tiering is a one-way door set at creation. It moves cold
(least-recently-used) keys to an SSD tier.

### Latency profile

| Key location | Typical latency | Use for |
|---|---|---|
| In-memory (hot) | sub-ms | Real-time application reads |
| SSD tier (cold) | 100x-1000x of in-memory | Analytics, batch, rarely-accessed data |

### When tiering helps

- Dataset >> available RAM, with a clear hot/cold split (e.g., 80/20).
- Cold keys are accessed rarely (analytics, historical lookups).
- Cost optimization is the primary constraint.

### When tiering hurts

- Uniform access patterns (no hot/cold split) — all keys eventually
  tier, latency degrades across the board.
- Latency-sensitive workloads (all keys must be sub-ms).
- Small datasets that fit in memory without tiering (the SSD overhead
  adds cost without benefit).

### Migrating to/from tiering

Data tiering CANNOT be enabled or disabled post-creation. To migrate:
1. Create a NEW cluster with `db.r6gd.<size>` and `--data-tiering=true`
   (or a non-tiered `db.r6g.<size>` cluster to move OFF tiering).
2. Snapshot the old cluster.
3. Restore into the new cluster, OR run a dual-write cutover.

## MemoryDB vs ElastiCache (boundary detail)

| Property | MemoryDB | ElastiCache (Redis) |
|---|---|---|
| Use case | Durable in-memory DATABASE | In-memory CACHE |
| Multi-AZ durability | Transaction log (zero committed loss) | Async replication (may lose in-flight) |
| TLS at-rest / in-transit | ON by default | Optional (set at creation) |
| ACLs (user-based auth) | REQUIRED | Optional (AUTH token or ACL) |
| Snapshots | YES (automated + manual) | YES (Redis only) |
| Data tiering | YES (r6gd family) | NO |
| Multi-Region | YES (Multi-Region engine) | YES (Global Datastore) |
| Node types | db.r6g, db.r6gd, db.r7g | cache.r6g, cache.m6g, cache.t4g, etc. |
| Pricing | Higher (durability overhead) | Lower |

**Decision rule:** if the workload requires durability (committed
data MUST survive node/AZ failure), use MemoryDB. If data is
disposable (cache-miss acceptable), use ElastiCache.

## ACL + TLS interactions

- MemoryDB REQUIRES an ACL — there is no "open" mode. The default
  `open-access` ACL allows unrestricted access and should NEVER be
  used in production.
- ACLs use Redis 6+ ACL syntax: `on ~* +@all` (full access),
  `on ~* -@all +@read` (read-only), etc.
- ACLs are cluster-scoped. A cluster has one ACL at a time; changing
  the ACL applies to all connections immediately.
- TLS is ON by default and RECOMMENDED. ACLs use the same auth
  pathway — disabling TLS is not recommended.

## Common sizing pitfalls

1. **Sizing by spec-sheet memory.** Plan for 50% usable; the rest is
   overhead.
2. **Adding replicas to scale writes.** Replicas scale reads only.
   Add shards to scale writes.
3. **Assuming replicas add memory.** Replicas hold copies — they add
   READ capacity and availability, NOT storage.
4. **Enabling data tiering for uniform-access workloads.** Cold-tier
   latency is 100x-1000x; use tiering only for hot/cold splits.
5. **Single-AZ subnet group for Multi-AZ.** Multi-AZ cannot place
   the replica in a different AZ. Verify >=2 AZs before create.
6. **Using the default `open-access` ACL.** Create a named ACL with
   least-privilege users.
