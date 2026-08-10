# Topology and Indexing Guide — OpenSearch Domain Deployer

Deep reference on managed-cluster vs Serverless tradeoffs, Multi-AZ
topology math, dedicated-master sizing, EBS-vs-instance-store
selection, shard and replica count heuristics, UltraWarm / cold
storage lifecycle, and vector search collection sizing. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Managed cluster vs Serverless — full feature matrix

The deployment type is the highest-impact OpenSearch decision and is
**immutable** without a full migration (different APIs, different
endpoints, different feature sets).

| Feature / property | Managed cluster | OpenSearch Serverless |
|---|---|---|
| Capacity management | YES (instance type, count, EBS) | NO (auto-scaling) |
| Billing | per instance-hour (always-on) | per OCU consumed (pay-per-use) |
| Scaling | manual / via `update-domain-config` | automatic |
| Text search | YES | YES |
| Vector search (k-NN) | YES (via plugin) | YES (VECTORSEARCH collection) |
| Aggregations | full | subset |
| Anomaly detection | YES | subset |
| Index State Management (ISM) | YES | subset |
| Cross-cluster search | YES | NO (Serverless lacks cross-cluster) |
| UltraWarm (warm tier) | YES | NO |
| Cold storage | YES | NO |
| Dedicated master nodes | YES | NO (managed automatically) |
| Custom plugins | subset (via package installation) | NO |
| VPC-only access | YES | YES |
| Public access | YES (not recommended for production) | YES |
| Encryption at rest | YES (KMS, at creation) | YES (AWS-managed default; customer CMK limited) |
| FGAC | YES (IAM or Cognito) | YES (IAM Identity Center; Cognito not directly) |
| Automated snapshots | daily to AWS-managed S3 | continuous (point-in-time recovery) |
| Manual snapshots to S3 | YES (register repository) | YES (separate API) |
| Streaming ingestion | YES | YES |
| Endpoint per collection | single domain endpoint | per-collection endpoint |

**Decision rule:**
- Predictable steady-state workload needing UltraWarm / cold storage /
  dedicated masters → managed cluster.
- Unknown / bursty / unpredictable workload → Serverless.
- Vector search only → Serverless VECTORSEARCH collection (simpler,
  cheaper for pure k-NN).
- Cross-cluster search needed → managed cluster (Serverless lacks
  cross-cluster).

## Multi-AZ topology math

Multi-AZ (3-zone) is the primary resilience control for managed
clusters. **Instance count must be a multiple of 3** for even AZ
distribution.

### Zone awareness

- `ZoneAwarenessEnabled=true` + `AvailabilityZoneCount=3` enables
  Multi-AZ.
- OpenSearch places primary and replica shards in different AZs.
- A 3-node cluster with `replica=1` tolerates one AZ loss.

### Instance count alignment

```text
required_data_nodes = ceil(total_storage_needed / per_node_storage)

# Round UP to next multiple of 3 for Multi-AZ
required_data_nodes_multi_az = ceil(required_data_nodes / 3) × 3

# Examples:
#   required = 5 → round up to 6 (2 per AZ)
#   required = 7 → round up to 9 (3 per AZ)
#   required = 11 → round up to 12 (4 per AZ)
```

### Node-count to replica-count relationship

For Multi-AZ to provide meaningful failover, replica count must be >= 1
so that a copy of each shard exists in a different AZ:

| Topology | replica=0 | replica=1 | replica=2 |
|---|---|---|---|
| 3 nodes (1 per AZ) | NO failover (data loss on AZ loss) | Tolerates 1 AZ loss | Tolerates 2 AZ losses |
| 6 nodes (2 per AZ) | NO failover | Tolerates 1 AZ loss | Tolerates 2 AZ losses |
| 9 nodes (3 per AZ) | NO failover | Tolerates 1 AZ loss | Tolerates 2 AZ losses |

**Hard rule:** for Multi-AZ production, set `replica >= 1`. With
`replica=0`, losing one AZ loses primary shards with no fallback.

## Dedicated master node sizing

Masters handle cluster-state updates (new index, shard allocation,
node loss). Without dedicated masters, this work happens on data
nodes, spiking query latency.

### When to use dedicated masters

```text
if data_nodes > 10:
    → MANDATORY dedicated masters (3 — one per AZ for Multi-AZ)
elif data_nodes <= 10 AND workload is latency-sensitive (p99 < 100ms):
    → RECOMMENDED dedicated masters
else:
    → optional (small dev/test clusters can use data-node masters)
```

### Master instance type sizing

| Data node count | Recommended master type | Why |
|---|---|---|
| 3-10 | not required (or `c6g.large.search`) | Small cluster; data nodes handle master work |
| 10-15 | `c6g.large.search` (3 × masters) | Moderate cluster-state; CPU is the bottleneck |
| 15-30 | `c6g.2xlarge.search` (3 × masters) | Large cluster-state; more CPU for consensus |
| 30-60 | `c6g.4xlarge.search` (3 × masters) | Very large cluster-state |
| 60-80 | `r6g.4xlarge.search` (3 × masters) | Memory becomes the bottleneck |

**Masters are CPU-bound, not memory-bound.** Use the `c6g` family for
masters (compute-optimized), not `r6g` (memory-optimized). The exception
is very large clusters (> 60 data nodes) where cluster-state size
demands more memory — switch to `r6g.4xlarge.search`.

### Multi-AZ master placement

Always provision 3 masters (one per AZ). This ensures master quorum
survives AZ loss:

- 3 masters across 3 AZs: tolerates 1 AZ loss (2 of 3 masters survive;
  quorum = 2).
- 3 masters in 1 AZ: single-AZ loss loses all masters — cluster goes
  down.

## Storage: EBS vs instance-store

### EBS (default for most instance types)

| Volume type | IOPS | Throughput | Use when |
|---|---|---|---|
| `gp3` (default since 2022) | 3,000 baseline, up to 16,000 provisioned | 125 MB/s baseline, up to 1,000 MB/s | General-purpose. DEFAULT CHOICE. |
| `io1` | up to 64,000 IOPS provisioned | up to 1,000 MB/s | Consistent high IOPS; latency-sensitive |
| `io2` | up to 64,000 IOPS | up to 1,000 MB/s | High IOPS + high durability (Block Express) |
| `standard` (magnetic) | low | low | DO NOT USE — legacy |

**gp3 vs gp2:** gp3 has 3,000 baseline IOPS vs gp2's 250 baseline (gp2
scales IOPS by volume size). gp3 is cheaper and faster at small sizes.
Always use gp3.

**EBS size limits:** 10 GB - 6 TB (gp3); up to 16 TB (io2 Block Express).

### Instance-store (NVMe) — specific instance types

| Instance type | NVMe size | Use when |
|---|---|---|
| `i3.large.search` | 1 × 1.9 TB NVMe | High-IOPS; bypass EBS network hop |
| `i3.2xlarge.search` | 1 × 3.8 TB NVMe | High-IOPS at larger scale |
| `i3en.large.search` | 1 × 2.3 TB NVMe | Higher throughput than i3 |
| `i3en.2xlarge.search` | 2 × 2.3 TB NVMe (4.6 TB total) | Very high throughput |

**Instance-store tradeoffs:**
- Higher IOPS than EBS (no network hop).
- Ephemeral — data is LOST if the instance fails. Always use
  `replica >= 1` for durability.
- Cannot resize storage without changing instance type.
- Use for: log analytics at massive scale, where EBS IOPS are the
  bottleneck.

### Free-space watermark

OpenSearch blocks writes at 85% disk full
(`cluster.routing.allocation.disk.watermark.high`):
- 85%: blocks new shard allocation.
- 90%: starts relocating shards away from the node.
- 95%: blocks all writes to indices on that node.

**Plan for 15% free space** in capacity calculations:

```text
usable_disk_gb = EBS_size_gb × 0.85
# Or for capacity planning: plan EBS_size to be ~118% of expected data
```

## Shard count estimator

Too many shards (over-sharding) creates overhead; too few shards
(under-sharding) creates hot shards.

### The 30-50 GB per shard rule

```text
recommended_shard_count = ceil(total_data_size_gb / 30)

# Use 30 GB for write-heavy (logs, metrics)
# Use 50 GB for read-heavy (search, analytics)
```

### Per-shard overhead

- Heap: ~50 KB per shard (mapping, settings).
- File handles: 100-1000 file descriptors per shard.
- CPU: each shard has a merge thread.

**Cluster-wide shard budget:** 20-25 shards per GB of heap. A 3-node
cluster with 32 GB heap each (96 GB total heap) should NOT exceed
~2,000-2,400 shards cluster-wide.

### Shard count by workload

| Workload | Rule | Reason |
|---|---|---|
| Logs / metrics (write-heavy, time-series) | 30 GB per shard | Fast recovery on node loss |
| Product catalog (read-heavy) | 50 GB per shard | Better cache hit rate on larger shards |
| Vector search (k-NN) | 1 shard per data node | Over-sharding dilutes the graph-based index |
| Small dataset (< 10 GB) | 1 shard | Avoid over-sharding overhead |

### Changing shard count post-creation

- `_split` API: split an index into more shards. New index has N×more
  shards (must be a multiple of the original). Disruptive — requires
  read-only mode during split.
- `_shrink` API: shrink an index into fewer shards. New index has
  N/M shards (must be a divisor). Disruptive.
- Reindex to a new index with the correct shard count.

**Plan shard count at index creation.** Resharding is disruptive.

## Replica count

Replica count is per-index, changeable at runtime (no disruption).
Multi-AZ places replica shards in different AZs than primaries.

| Replica count | Storage multiplier | Tolerates | Use when |
|---|---|---|---|
| 0 | 1× | NO node loss (data loss on primary failure) | Dev / test only |
| 1 | 2× | 1 node loss per shard | Production standard |
| 2 | 3× | 2 simultaneous node losses | High availability (rare; cost) |

**Default for production:** `replica=1`.

**For Multi-AZ:** `replica >= 1` is mandatory for AZ-failure resilience.

## UltraWarm and cold storage lifecycle

Managed cluster only — Serverless does NOT support these.

### UltraWarm

- Read-only warm tier for recent history (e.g., last 30 days).
- Uses NVMe instance storage (lower cost per GB than hot tier).
- ~50% cheaper than hot storage.
- Indices are READ-ONLY after migration.
- Migration: hot → warm via ISM policy; warm → hot requires explicit
  reindex.

### Cold storage

- Read-only archive tier for long-term retention (months-years).
- Uses S3 (lowest cost per GB).
- Recall takes minutes-hours (must explicitly recall to query).
- Requires UltraWarm enabled.
- ~80% cheaper than hot storage.

### Index lifecycle (ISM policy)

```json
{
  "policy": {
    "default_state": "hot",
    "states": [
      {
        "name": "hot",
        "actions": [],
        "transitions": [
          {"state_name": "warm", "conditions": {"min_index_age": "7d"}}
        ]
      },
      {
        "name": "warm",
        "actions": [],
        "transitions": [
          {"state_name": "cold", "conditions": {"min_index_age": "30d"}}
        ]
      },
      {
        "name": "cold",
        "actions": [],
        "transitions": [
          {"state_name": "delete", "conditions": {"min_index_age": "365d"}}
        ]
      },
      {"name": "delete", "actions": [{"delete": {}}]}
    ]
  }
}
```

### Storage tier sizing

| Tier | Use | Cost | Latency |
|---|---|---|---|
| Hot | Active queryable data (last N days) | $$$ | ms |
| UltraWarm | Recent history (last 30-90 days) | $$ (50% cheaper) | ms (read-only) |
| Cold | Long-term archive (months-years) | $ (80% cheaper) | minutes-hours (recall required) |

**Common mistake:** migrating indices to UltraWarm then needing to
write to them. UltraWarm is READ-ONLY. Writes must complete before ISM
migrates the index.

## Vector search collection sizing

OpenSearch Serverless VECTORSEARCH collections are optimized for k-NN
similarity search. Different sizing rules apply.

### Collection type

- `SEARCH`: general text search collection (managed-cluster equivalent).
- `VECTORSEARCH`: vector similarity search collection (k-NN optimized).
- `TIMESERIES`: time-series collection (optimized for log/metrics).

### Vector index sizing

| Parameter | Recommendation |
|---|---|
| Engine | nmslib (default) or faiss |
| Algorithm | HNSW (default; best recall/latency tradeoff) |
| Space method | `l2` (Euclidean), `cosinesimil` (cosine), `innerproduct` |
| Vector dimensions | 768 (BERT), 1536 (OpenAI), 1024 (Cohere) — depends on model |
| Shards | 1 shard per data node (over-sharding dilutes the graph) |
| Replicas | 1-2 (for HA) |

### Heap-to-vector-data ratio

Vector indices use significant heap for the HNSW graph:

```text
heap_per_vector_bytes = dimensions × 4 + graph_overhead (~50%)
# Example: 1536 dimensions (OpenAI ada-002)
# heap_per_vector = 1536 × 4 × 1.5 = 9,216 bytes ≈ 9 KB

total_heap_for_vectors = vector_count × heap_per_vector_bytes
```

For 10M vectors at 1536 dimensions: 10M × 9 KB = 90 GB heap just for
the vector graph. Plan instance memory accordingly.

## AWS documentation references

- Sizing OpenSearch domains — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/sizing-domains.html
- Dedicated master nodes — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-dedicatedmasternodes.html
- Multi-AZ domains — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-multiaz.html
- UltraWarm storage — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ultrawarm.html
- Cold storage — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/cold-storage.html
- OpenSearch Serverless — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/serverless.html
- Vector search (k-NN) — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/knn.html
- EBS storage — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/limits.html#ebs-limits
