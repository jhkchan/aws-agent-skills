# Instance and Topology Guide — Neptune DB Cluster Deployer

Deep reference on Neptune DB instance-class selection, writer/reader
math, Multi-AZ failover internals, encryption/IAM interactions, and
the Neptune Analytics boundary. Loaded on demand by the skill — kept
out of the main SKILL.md body so the provisioning procedure stays
scannable.

## Instance class families

Neptune offers several instance families. Memory-bound graph workloads
favor the `r` (memory-optimized) and `x2gdb` (max-memory) families.

| Family | Classes | Memory (representative) | Use when |
|---|---|---|---|
| `db.r6g.large` / `.xlarge` / `.2xlarge` | Graviton, memory | 16 / 32 / 64 GB | Small-medium graphs (< 100 GB working set); dev/test |
| `db.r6g.4xlarge` / `.8xlarge` / `.12xlarge` / `.16xlarge` | Graviton, memory | 128 / 256 / 384 / 512 GB | Mid-to-large production graphs (100-500 GB) |
| `db.r5.large` ... `.24xlarge` | Legacy gen, memory | up to 768 GB | Existing r5 footprints; new clusters prefer r6g |
| `db.x2gdb.16xlarge` / `.24xlarge` | Graviton, max memory | 1024 / 1536 GB | Very large graphs (500 GB+ working set) |
| `db.r6i.large` ... `.32xlarge` | Intel, balanced | up to 1024 GB | Read-heavy with deep traversals needing CPU |

**Graviton (r6g, x2gdb) note (2022-2024):** ~15% better price/performance
over r5. Default to Graviton for new clusters. Verify your region
supports the chosen class before provisioning.

**Burstable (`t3`, `t4g`):** NOT recommended for production. Neptune
is not supported on burstable in some regions; CPU credits deplete
under sustained traversal load. Use `r6g.large` as the floor.

## Writer/reader math

Neptune has exactly **one writer per cluster**. Readers scale reads
and provide failover targets; they do NOT scale writes.

```text
write_capacity  = single_writer_baseline   # does NOT scale with readers
read_capacity   = writer_baseline + (reader_count × reader_baseline)

# For db.r6g.8xlarge (representative):
#   ~80k traversal reads/sec per instance
#   ~10k mixed writes/sec per writer (write throughput is one writer only)
#
# 1 writer + 2 readers (db.r6g.8xlarge):
#   read capacity  ≈ 3 × 80k = 240k reads/sec
#   write capacity ≈ 10k writes/sec (single writer)
```

**Implication:** for write-heavy workloads, scale UP the writer
instance class (more memory + CPU per write) — not out. For read-heavy
workloads, add readers.

## Buffer cache budget (the 60% rule)

Neptune is memory-bound. The graph working set (vertices + edges +
indexes) MUST fit in the buffer cache for sub-second traversals.

```text
usable_buffer_cache = instance_memory × 0.60
# ~60% is the operating budget. Neptune reserves the rest for:
#   - OS + JVM internal state
#   - Connection state + query buffers
#   - Copy-on-write overhead during snapshot

working_set = vertices_bytes + edges_bytes + (3 × indexes_bytes)
# Neptune maintains property + edge indexes consuming ~3x the raw
# edge data. Indexes make traversals fast; never size them out.

# Working set MUST be <= usable_buffer_cache, or traversals slow 10-100x
# as cache misses fall through to the storage layer.
```

### Worked sizing example

```text
200M vertices (200 B avg) + 1B edges (80 B avg):
  vertices_bytes  = 200e6 × 200 = 40 GB
  edges_bytes     = 1e9 × 80    = 80 GB
  indexes_bytes   = 3 × 80      = 240 GB
  working_set     = 360 GB

Usable budget by instance class:
  db.r6g.8xlarge  (256 GB × 0.60 = 154 GB)  — TOO SMALL
  db.r6g.12xlarge (384 GB × 0.60 = 230 GB)  — TOO SMALL
  db.r6g.16xlarge (512 GB × 0.60 = 307 GB)  — TOO SMALL (just under)
  db.x2gdb.16xlarge (1024 GB × 0.60 = 614 GB) — FITS with headroom

# For this graph, db.x2gdb.16xlarge is the floor.
```

## Multi-AZ failover internals

- **Cluster endpoint is stable.** Always points to the current writer.
  On failover, the endpoint repoints automatically; clients reconnect
  via the cluster endpoint without code change.
- **Promotion time: ~30 seconds** (instance detection + reader
  promotion + endpoint DNS update).
- **Data loss window: zero committed transactions.** Neptune storage
  is cluster-shared (6-way storage replication across AZs); a promoted
  reader sees all writes the old writer committed.
- **In-flight writes during the ~30s window** get connection errors
  and must be retried by the application.

### Anti-pattern: writer + readers all in one AZ

If the writer is in AZ-a and all readers are also in AZ-a, failover
cannot move the writer out of AZ-a (no promotion target in a
different AZ). Spread readers across at least 2 AZs distinct from the
writer's AZ.

### Recommended topologies

| Workload | Topology | Notes |
|---|---|---|
| Dev / test | 1 writer (1 AZ) | No failover; for functional testing only |
| Small prod (read-heavy) | 1 writer + 1 reader (2 AZs) | Minimum production with Multi-AZ |
| Mid prod (mixed) | 1 writer + 2 readers (3 AZs) | Read scaling + Multi-AZ + AZ-spread |
| Large prod (deep traversals) | 1 writer + 3+ readers (3+ AZs) | Read scaling for deep traversals + Multi-AZ |

## Neptune DB vs Neptune Analytics (boundary detail)

These two services share query languages but NOT the data plane.
Picking the wrong service is the single most common Neptune design
error.

| Property | Neptune DB | Neptune Analytics |
|---|---|---|
| Service type | Transactional (OLTP) | Analytical (OLAP) |
| API namespace | `aws neptune` | `aws graph` |
| Create call | `create-db-cluster` | `create-graph` |
| Topology | writer + reader replicas (Multi-AZ) | single graph (no writer/reader split) |
| Failover | YES (writer promotion ~30s) | N/A (recreate on failure) |
| Gremlin transactions | YES | NO (read-only analytic queries) |
| SPARQL | YES | NO |
| openCypher | YES | YES |
| Built-in graph algorithms | NO (write your own Gremlin) | YES (PageRank, BFS, connected-components, etc.) |
| Storage | cluster-shared (6-way) | ephemeral snapshot-loaded |
| Pricing | instance-hour + storage + IO | GB-hour (memory) + snapshot |
| Latency | sub-ms to ms (real-time app) | seconds to minutes (batch) |

**Decision rule:** OLTP workload (point lookups, short traversals,
real-time app queries, frequent writes) → Neptune DB. OLAP workload
(PageRank, community detection, large-graph batch analysis) → Neptune
Analytics. Both → Neptune DB for transactions + scheduled export to
Neptune Analytics for batch.

## Encryption + IAM interactions

- **Encryption at rest** is immutable: set at creation via
  `--storage-encrypted` + optional `--kms-key-id`. Adding it later
  requires snapshot → restore into a new encrypted cluster.
- **TLS** is controlled via `neptune_enforce_ssl=1` in the cluster
  parameter group. Changing it requires an instance reboot; enable at
  creation to avoid dropping plaintext clients.
- **IAM database auth** uses SigV4 tokens (~15 min lifetime). Most
  modern Gremlin/SPARQL drivers refresh automatically; verify your
  client lib. IAM auth and password auth can coexist — to enforce
  IAM-only, do NOT set a password.
- IAM auth requires TLS — pair `--enable-iam-database-authentication`
  with `neptune_enforce_ssl=1`.

## Reader endpoint vs cluster endpoint

- **Cluster endpoint** — always points to the current writer. Use for
  write traffic and read-after-write consistency.
- **Reader endpoint** — round-robins across readers. Use for read-
  scaling traffic (traversals that tolerate eventual consistency).
- **Instance endpoints** — point to individual instances. Use for
  debugging; do NOT hardcode in applications (instances come and go).

## Common sizing pitfalls

1. **Sizing by spec-sheet memory.** Plan for 60% usable; the rest is
   reserved for overhead.
2. **Forgetting the 3x index multiplier.** Edges cost 1x in storage
   but their property indexes cost ~3x. Size for vertices + edges +
   3x indexes.
3. **Adding readers to scale writes.** Readers scale reads only. There
   is exactly one writer per cluster.
4. **Using burstable (`t3`/`t4g`) instances.** CPU credits deplete
   under sustained traversal load. Use `r6g.large` as the floor.
5. **Single-AZ subnet group for Multi-AZ.** Multi-AZ cannot place the
   reader in a different AZ. Verify the subnet group spans >=2 AZs
   before `create-db-cluster`.
