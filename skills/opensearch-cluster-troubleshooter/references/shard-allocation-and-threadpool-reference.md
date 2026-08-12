# Shard Allocation and Thread Pool Reference Guide

Supplementary reference for the OpenSearch Cluster Troubleshooter
skill. Loaded on-demand when a diagnostic needs shard allocation
decider reference, thread-pool sizing, circuit breaker defaults,
shard-count capacity rules, or snapshot-lifecycle semantics.

## Shard count and capacity

Each shard carries 50-200 MB of overhead — file handles, mapping
metadata, and a Lucene segment merge queue. A cluster with 30,000
shards is paying 1.5-6 GB of overhead alone, before any document
data.

- AWS guidance: **≤ 20 shards per GB of heap** (the inverse: 1
  shard per ~50 MB of heap for safety).
- Working approximation: **`(primary × replica) ≈ data node count
  × 20`** as a steady-state ceiling.
- `cluster.max_shards_per_node` default is **1000 on managed
  OpenSearch**. Raising the cap defers the problem; it does not add
  capacity.
- Per-node shard count > 1000 leads to slow cluster-state updates
  and elevated master-node CPU. The symptom is "the cluster is
  slow" when the cause is shard bloat.

### Shard sizing for ingestion

For a known ingestion rate (documents/sec) and average document
size:

```
shards_per_index ≈ (ingestion_gb_per_day × days_per_index) / 50
```

Where `50` is the recommended GB-per-shard ceiling. A 200 GB index
should be split into 4 shards, not 1.

## Allocation decider reference

`_cluster/allocation/explain` returns a list of deciders that voted
`NO` on placing the shard. **The FIRST decider is the binding
constraint; the rest cascade.** Reading past the first wastes
cycles.

| Decider | Default | Meaning | Fix |
|---|---|---|---|
| `disk_watermark.low` | 85% | Node above low watermark; new shards skipped | Free disk below 85% |
| `disk_watermark.high` | 90% | Node above high; shards being evacuated OFF | Free disk below 85% |
| `disk_watermark.flood` | 95% | Node above flood; read-only block active | Free disk below 95% |
| `max_shards_per_node` | 1000 | Node has reached the per-node shard cap | Raise cap OR add data nodes OR reduce shard count |
| `same_shard` | n/a | Replica and primary cannot colocate on the same node | Add data nodes; replica count exceeds node count |
| `filter` (require / include / exclude) | off | Allocation filter (`cluster.routing.allocation.require`) excludes all nodes | Fix `_cluster/settings` allocation attributes |
| `awareness` | off | Awareness attribute (`zone`, `rack`) missing on some nodes | Add nodes in the missing awareness attribute |
| `shard_size` | n/a | Shard too large to relocate | Split the index via `_split` |
| `recovery_after_time` / `recovery_after_nodes` | varies | Recovery gating; cluster waiting for nodes or time | Wait; check `_cat/recovery?v` |
| `data_after node left` | n/a | All data nodes that held a replica also left | Restore from snapshot (data loss) |

### Allocation filter pitfalls

`cluster.routing.allocation.require.<attribute>` settings persist
across node replacements. If the replacement node does not have the
required attribute (e.g., `zone: us-east-1a`), the cluster looks
healthy but no shards allocate to the replacement. Always verify
the node attributes:

```bash
curl -sS "https://<domain-endpoint>/_cat/nodeattrs?v" -H "Content-Type: application/json"
```

## Thread pool reference

Thread pools are per-node and bounded. On managed OpenSearch the
queue sizes are **not user-tunable** — overrides to
`thread_pool.search.queue_size` via `_cluster/settings` are
reverted by the managed service.

| Pool | Default queue | Default threads | Cause of rejection |
|---|---|---|---|
| `search` | 1000 | (int) available processors | Concurrent or slow searches |
| `write` | 10000 (varies by version) | (int) available processors | Bulk indexing rate exceeds shard capacity |
| `get` | 1000 | (int) available processors | High rate of multi-get by ID |
| `analyze` | 40 | 1 | Analyzer API rate |
| `refresh` | 10 | (int) min(proc/2, 10) | Refresh backlog |
| `management` | 5 | 5 | Cluster-state update backlog |

`EsRejectedExecutionException` is a 429 to the client. The `rejected`
column in `_cat/thread_pool/<pool>?v` counts rejections since node
start — a non-zero, growing count is positive evidence.

### Search rejection fix order

1. Identify the slow query in the slow logs (Step 9 of SKILL.md).
2. Rewrite or paginate the slow query.
3. Throttle the client (reduce concurrency).
4. Add data nodes.

### Write rejection fix order

1. Reduce bulk batch size (smaller batches = less time in queue).
2. Raise `index.refresh_interval` (default 1s) to reduce segment
   merge pressure.
3. Reduce replica count temporarily (writes fan out to replicas).
4. Add data nodes.

## Circuit breaker defaults

| Breaker | Default limit | Measured against |
|---|---|---|
| `parent` | 95% of heap | Sum of all child breakers + in-flight allocations |
| `fielddata` | 40% of heap | Fielddata cache for text/keyword fields |
| `request` | 60% of heap | Per-request allocations (aggregations, sorting) |
| `in_flight_requests` | 100% of heap | HTTP/transport in-flight buffers |
| `accounting` | 100% of heap | Lucene segment memory (off-heap accounted) |

The `parent` breaker wraps the others. A `parent` trip without a
named inner trip is rare — the inner breaker that pushed parent
over is the real cause. Use `_nodes/stats/breaker?pretty` to read
the estimated size of each breaker.

### Common breaker trip patterns

| Pattern | Cause | Fix |
|---|---|---|
| `[fielddata]` trip on a single field | `text` field with `fielddata: true` aggregated | Disable fielddata; use `keyword` multi-field |
| `[request]` trip on a large terms aggregation | `terms: {size: 10000}` on high-cardinality field | Reduce `size`; paginate; use composite aggregation |
| `[request]` trip on sorting | Sorting on a high-cardinality keyword field | Use `numeric` or `date` sort; pre-sort at index time |
| `[parent]` trip with multiple inner trips | Working set too large for heap | Reduce working set (close indices, reduce replicas) |

## Snapshot lifecycle on managed OpenSearch

- **Automated repository:** `cs-automated` (S3, managed by the
  service). The bucket and IAM role are managed automatically.
- **Automated snapshot cadence:** daily, between 00:00 and 01:00
  UTC (window varies by domain).
- **Snapshot duration:** scales with index count and size — large
  clusters see snapshots lasting hours.
- **Index deletion during snapshot:** blocked via
  `SnapshotInProgressException`. The snapshot repository holds a
  lock on the index until the snapshot completes.
- **Force-delete mid-snapshot:** risks repository corruption that
  requires AWS Support to repair. NEVER do this.
- **Manual repository registration:** `PUT /_snapshot/<repo>` with
  S3 bucket + IAM role (registered via the OpenSearch Dashboard
  snap-in or the Configuration API).

### Snapshot-related operations

```bash
# List registered repositories
curl -sS "https://<domain-endpoint>/_cat/repositories?v" -H "Content-Type: application/json"

# Snapshot status (active snapshots)
curl -sS "https://<domain-endpoint>/_snapshot/_status?pretty" -H "Content-Type: application/json"

# Cancel a snapshot (safe — does not corrupt the repository)
DELETE /_snapshot/<repository>/<snapshot_id>

# Restore a snapshot (creates new indices; consumes disk)
POST /_snapshot/<repository>/<snapshot_id>/_restore
```

## Cluster health states

| Status | Meaning | Severity | Action |
|---|---|---|---|
| `green` | All primaries and replicas allocated | Healthy | None |
| `yellow` | All primaries allocated; at least one replica not | Redundancy loss | P2 unless node-loss may cascade |
| `red` | At least one primary shard unallocated | Data unavailability | P0 |

`_cluster/health` fields:

| Field | Meaning |
|---|---|
| `number_of_nodes` | All nodes (data + master + warm) |
| `number_of_data_nodes` | Data nodes only |
| `active_primary_shards` | Primary shards currently allocated |
| `active_shards` | All allocated shards (primary + replica) |
| `relocating_shards` | Shards being moved between nodes |
| `initializing_shards` | Shards being newly created |
| `unassigned_shards` | Shards not allocated (replica or primary) |
| `unassigned_primary_shards` | Primary shards not allocated (red indicator) |
| `active_shards_percent_as_number` | % of shards allocated; < 100 = yellow or red |

## Recent AWS features (2024-2026)

- **OpenSearch 2.13+ default watermarks (2024-2025):** Managed
  domains ship with `low: 85%`, `high: 90%`, `flood_stage: 95%`
  and a frozen flood stage at 95% for reliability. The auto-clear
  on the flood block is now the default.
- **ISM (Index State Management) default-on for new domains
  (2024):** New managed domains ship with a default ISM policy that
  rolls indices at 100 GB or 30 days. Older domains still need ISM
  attached manually.
- **OpenSearch 2.15+ parent circuit breaker tuning (2025):** The
  parent breaker is now 95% by default (was 90% pre-2.13). Trips
  at 95% report the inner breaker that pushed parent over.
- **UltraWarm migration parallelism (2025):** Migrations now batch
  up to 5 indices concurrently.
- **Graceful shutdown for in-place upgrades (2024-2025):** Upgrades
  now drain shards off nodes being replaced, reducing the window
  where `_cat/shards` shows RELOCATING during an upgrade. A
  temporary yellow during upgrade is expected; red is not.
- **OpenSearch Serverless vs managed OpenSearch (2024-2026):**
  Serverless collections do NOT use the disk-watermark, JVM-heap,
  thread-pool failure model — they auto-scale. This skill targets
  managed OpenSearch Service only.

## AWS documentation references

- Cluster health and metrics: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/monitoring-cloudwatch.html
- Index State Management: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ism.html
- UltraWarm and cold storage: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ultrawarm.html
- Snapshots: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html
- In-place upgrades: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-maturity.html
