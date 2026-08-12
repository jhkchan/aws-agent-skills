# Disk Watermark and JVM Heap Reference Guide

Supplementary reference for the OpenSearch Cluster Troubleshooter
skill. Loaded on-demand when a diagnostic needs disk-watermark
thresholds, JVM heap sizing rules, or the working-set triad
(close / reduce replicas / add nodes).

## Disk watermark defaults (managed OpenSearch)

Managed OpenSearch Service runs with three disk watermarks tuned for
stability. Defaults are applied at the cluster level and can be
read via `_cluster/settings?include_defaults=true&flat_settings`.

| Watermark setting | Default | Threshold effect |
|---|---|---|
| `cluster.routing.allocation.disk.watermark.low` | 85% | New shards do not allocate to the node. Existing shards stay. |
| `cluster.routing.allocation.disk.watermark.high` | 90% | Cluster actively relocates shards OFF the node. Drives IOPS and CPU up. |
| `cluster.routing.allocation.disk.watermark.flood_stage` | 95% | `index.blocks.read_only_allow_delete` set on every index with a replica (or every index if no replicas). Writes blocked cluster-wide. |
| `cluster.routing.allocation.disk.watermark.flood_stage.frozen` | 95% (managed) | Frozen flood stage; block auto-clears once disk drops below flood. |
| `cluster.routing.allocation.disk.watermark.low.max_headroom` | 200 GB | Headroom-based floor (used when the percentage threshold is too generous on very large volumes). |

The flood-stage block is the well-known write blocker. It is
**auto-applied** at the index level via
`index.blocks.read_only_allow_delete` (note: `_allow_delete` —
deletes are still permitted to allow recovery). Once disk drops
below flood, the block is **auto-cleared** on managed domains.

### Stage comparison

| Stage | What happens | Recovery |
|---|---|---|
| 85% (`low`) | New shards skip this node. Cluster continues serving traffic. | Free disk below 85%; cluster rebalances new shards to the node. |
| 90% (`high`) | Cluster evacuates shards off this node. High disk IOPS, CPU, and network. Queries may slow. | Free disk below 85% (cluster continues relocating until below low). |
| 95% (`flood_stage`) | Read-only block on indices with replicas. Writes return `ClusterBlockException`. Reads still succeed. | Free disk below 95%. Block auto-clears within ~1-5 min. Force-clear via `PUT _all/_settings {"index.blocks.read_only_allow_delete": null}` ONLY after disk is below flood. |

### Why disk filled — the upstream causes

- **Unbounded index growth, no ISM policy:** date-suffix indices
  (`logs-2024-01`, `events-2025-q3`) accumulate without rollover or
  deletion. Detect via `_cat/indices?v&s=store.size:desc` and the
  presence of an ISM policy (`_plugins/_ism/explain/<index>`).
- **Replica count increase:** `number_of_replicas: 2` instead of 1
  doubles disk usage on the replicated indices. Detect via
  `GET /<index>/_settings` and look at `number_of_replicas`.
- **Force-merge in progress:** a recent
  `_forcemerge?max_num_segments=1` call temporarily doubles segment
  file size during the merge. Wait; do not force-merge under disk
  pressure.
- **Snapshot restore in progress:** `_snapshot/_status` shows a
  restore in progress; restored indices consume disk.
- **Shard relocation in progress:** `_cat/recovery?v` shows active
  recoveries that consume disk on the destination node.

## JVM heap sizing reference (managed OpenSearch)

Heap on managed OpenSearch is fixed at **~50% of instance RAM** up
to the **32 GB ceiling** (the JVM compressed-oops threshold). Above
32 GB heap, the JVM loses pointer compression and effective heap
shrinks. AWS caps heap at 32 GB regardless of instance RAM.

| Instance class | vCPU | RAM (GB) | Heap (GB, ~50%) | Notes |
|---|---|---|---|---|
| `r6g.large.search` | 2 | 16 | 8 | Smallest practical for production |
| `r6g.xlarge.search` | 4 | 32 | 16 | Common mid-tier |
| `r6g.2xlarge.search` | 8 | 64 | 32 (ceiling) | First instance at the heap ceiling |
| `r6g.4xlarge.search` | 16 | 128 | 32 (ceiling) | RAM adds off-heap headroom only |
| `r6g.8xlarge.search` | 32 | 256 | 32 (ceiling) | RAM adds off-heap headroom only |
| `r6g.12xlarge.search` | 48 | 384 | 32 (ceiling) | Max instance; off-heap dominant |

The implication: scaling beyond `r6g.2xlarge` adds CPU and off-heap
RAM (Lucene segment cache, fielddata cache, in-flight buffers) but
NOT more heap. Heap-bound workloads plateau at 32 GB.

## JVMHeapPressure threshold guide

| Pressure | Behaviour | Action |
|---|---|---|
| < 60% | Healthy | None |
| 60-75% | Normal peak load | Watch |
| 75-85% sustained 5 min | Old-gen GC cycles frequent; query latency degrades | Early warning — reduce working set (close old indices, reduce replicas, migrate to UltraWarm) |
| 85-95% | Frequent stop-the-world GC; queries slow dramatically | Reduce working set immediately; consider scale-out |
| > 95% | One query allocation away from OOM; imminent `circuit_breaking_exception` | Emergency working-set reduction; AWS Support ticket if node has already dropped |

The managed service CloudWatch alarm default is **80%**. Senior
operators alarm at **75% sustained for 5 minutes** — by 80% the
cluster is already in trouble.

## The working-set reduction triad

When heap pressure is the diagnosis, three actions resolve most
incidents without raising the heap (which is fixed on managed
domains):

1. **Close indices not actively queried.**
   `POST /<index>/_close` removes the index from the searchable
   working set; shards stay on disk but heap overhead drops to near
   zero. Reversible via `POST /<index>/_open`.
2. **Reduce replica count temporarily.**
   `PUT /<index>/_settings {"number_of_replicas": 1}` halves the
   per-shard heap cost on the replicated indices. Trade-off: less
   redundancy. Reversible.
3. **Migrate cold indices to UltraWarm storage.**
   UltraWarm uses a different storage model (S3-backed) with a
   smaller per-shard heap footprint. Migrated indices remain
   queryable at lower cost. Use the ISM policy action
   `ultrawarm_migration`.

Scaling the instance class up (to raise heap up to 32 GB) is a
fourth option, but it defers the cause — the cluster grew past its
capacity. Reducing the working set addresses the cause.

## Fielddata cache

Fielddata is the on-heap cache used by text fields when
aggregations, sorting, or scripting require doc-values on a field
that does not have them (i.e., `text` fields). It is heap-resident
and a common cause of heap pressure.

| Setting | Default | Effect |
|---|---|---|
| `indices.fielddata.cache.size` | unbounded | Maximum heap % for fielddata. Set to 40% as a safety net on read-heavy clusters. |
| `indices.fielddata.cache.expire` | never | Time after which fielddata is evicted if not accessed. Rarely useful — the cache self-evicts under pressure. |

Field-level remediation:

```json
// Disable fielddata on the offending text field
PUT /<index>/_mapping
{
  "properties": {
    "request_body": {
      "type": "text",
      "fielddata": false
    }
  }
}

// If aggregation is needed, add a keyword multi-field and aggregate on it
PUT /<index>/_mapping
{
  "properties": {
    "request_body": {
      "type": "text",
      "fields": {
        "raw": { "type": "keyword" }
      }
    }
  }
}
```

Aggregate on `request_body.raw` (uses doc-values, off-heap) instead
of `request_body` (uses fielddata, on-heap).

## OldGenGCTime — the silent metric

`OldGenGCTime` (CloudWatch `AWS/ES` namespace) measures cumulative
time spent in old-generation GC. It is monotonically increasing
during normal operation — the key signal is the **rate of climb**.

| Pattern | Meaning |
|---|---|
| `OldGenGCTime` climbs 5-10 min/hour | Healthy — minor old-gen GCs are normal |
| `OldGenGCTime` climbs 30-60 min/hour | Old-gen GC pressure; queries slowing |
| `OldGenGCTime` climbs 100+ min/hour | Stop-the-world storms; imminent OOM |

Cross-reference `OldGenGCTime` against `JVMHeapPressure`. The two
move together; if `JVMHeapPressure` is rising and `OldGenGCTime`
rate-of-climb is increasing, the cluster is in the death spiral
that ends in OOM.

## AWS documentation references

- Disk-based allocation: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/size-your-clusters.html
- JVM heap pressure and OOM: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/handling-errors.html
- CloudWatch metrics: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-cloudwatch-metrics.html
- Circuit breakers: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/circuit-breaker.html
