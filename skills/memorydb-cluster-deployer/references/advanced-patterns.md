# MemoryDB Cluster Deployer — advanced patterns (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Mindset — provisioning misconceptions (extended detail)

Three misconceptions dominate MemoryDB misdesign at provisioning time:

- **"MemoryDB is just ElastiCache with a different name."** It is
  not. ElastiCache is a cache (data is disposable, durability is
  optional). MemoryDB is a durable database — it writes transactions
  to a Multi-AZ transaction log before acknowledging, so a node
  failure does NOT lose committed data. Pricing reflects this
  (MemoryDB is more expensive per node). Use MemoryDB when the data
  MUST survive node loss; use ElastiCache when the data is disposable.

- **"Skip ACLs for simplicity."** MemoryDB REQUIRES an ACL — there
  is no "open" mode. The default `open-access` ACL allows
  unrestricted access but should NEVER be used in production. Create
  named users with least-privilege access (read-only for analytics,
  read-write for the application).

- **"Data tiering is a free lunch."** Data tiering moves
  infrequently-accessed keys to an SSD tier, lowering cost — but
  tiered keys have 100x-1000x the access latency of in-memory keys.
  Enable tiering only for workloads with a clear hot/cold access
  pattern, not for general use.

## Expert heuristic: effective memory calculator

MemoryDB markets a node type by total memory, but the usable memory
for application data is significantly less. A baseline model quotes
the spec-sheet number; this heuristic gives the real figure.

```text
usable_per_shard = node_memory_bytes × 0.50
# 50% rule: Redis reserves ~50% for overhead, COPY-on-write fork
# during snapshot/failover, and the QUERY/Sort buffer.

total_usable = usable_per_shard × number_of_shards
max_item_size = 512 MB per single value (Redis hard limit)

# With data tiering (r6gd family):
#   hot_tier  = node_memory × 0.50   (in-memory; sub-ms)
#   cold_tier = ssd_size × 0.90      (SSD-backed; 100x-1000x latency)
```

**Concrete example — db.r6g.24xlarge (612.30 GiB nominal):**

| Topology | Calculation | Usable for application data |
|---|---|---|
| 3 shards × 1 primary + 1 replica each | 612.30 × 0.50 × 3 | **918.45 GiB** |
| 5 shards × 1 primary + 1 replica each | 612.30 × 0.50 × 5 | **1530.75 GiB** |
| 3 shards, data tiering (r6gd, ~612 GiB RAM + ~1224 GiB SSD) | (612.30 × 0.50 × 3) + (1224 × 0.90 × 3) | **4223.25 GiB** |

**Implication:** data tiering roughly 4-5x the usable budget for the
same node count — but cold-tier access is 100x-1000x slower.

## Expert heuristic: shard count estimator

MemoryDB cluster mode distributes writes across shards. Each shard is
a separate primary; the cluster hash-slots data across 16,384 slots.
The number of shards is the horizontal-write scaling factor.

```text
required_shards = ceil(sustained_writes_per_sec / (node_write_baseline × 0.60))
max_shards = 500   # MemoryDB hard limit (250 soft)

# db.r6g.24xlarge baseline: ~100,000 writes/sec per primary
# Example: 200,000 writes/sec sustained
# required_shards = ceil(200000 / (100000 × 0.60)) = 4 shards

# For durability, ALWAYS >=1 replica per shard (Multi-AZ failover)
```

**Why 60%:** MemoryDB baselines are measured with pipelined `SET` on
small values. Real-world workloads have larger values and non-
pipelined patterns. 40% headroom is the threshold observed in
production incident post-mortems.

## Expert heuristic: failover promotion semantics

A baseline model says "Multi-AZ gives you failover" without
explaining what gets promoted and how long it takes.

- **Cluster endpoint is stable.** The configuration endpoint always
  resolves to the cluster; clients route to the correct shard primary
  via MOVED/ASK redirection.
- **Failover is per-SHARD.** A 5-shard cluster can have up to 5
  simultaneous shard failovers during an AZ event.
- **Promotion time: ~10-30 seconds per shard** (replica promotion +
  endpoint update).
- **Data loss window: zero committed transactions.** MemoryDB writes
  to a Multi-AZ transaction log before acknowledging — a promoted
  replica sees all committed writes. In-flight writes during the
  failover window get errors and must be retried.
- **Multi-AZ requires replicas in a different AZ than the shard's
  primary.** A single-AZ subnet group silently blocks Multi-AZ.

**Practical implication:** MemoryDB's durability guarantee (zero
committed-transaction loss on failover) is what distinguishes it from
ElastiCache. If the workload tolerates data loss on failover,
ElastiCache is cheaper; if not, MemoryDB is the answer.

## Step 10 — Multi-Region / recent features (2023-2026)

**Multi-Region MemoryDB (2023-2024):**
- Cross-region replication with the Multi-Region engine.
- Writes go to the primary region; secondary regions serve local
  reads (async; typical lag < 1 second).
- Each region's cluster has its own node type, encryption, ACL.
- Use for: cross-region low-latency reads, DR.

**Recent AWS features (2023-2026):**
- **Data tiering (2022-2023):** SSD-backed cold tier for large
  datasets. One-way door — enable at creation.
- **Multi-Region (2023-2024):** Cross-region replication for DR /
  geo-distributed reads. Each region has its own cluster.
- **Graviton (r7g) node types (2023-2024):** ~10% better
  price/performance over r6g. Default to Graviton for new clusters.
- **Redis 7.x support (2023-2024):** Sharded pub/sub, functions (Lua
  enhancement), ACL improvements.
- **TLS-by-default enforcement (2023-2024):** MemoryDB now enforces
  TLS at-rest + in-transit by default. Disabling requires explicit
  opt-out and is NOT recommended.

