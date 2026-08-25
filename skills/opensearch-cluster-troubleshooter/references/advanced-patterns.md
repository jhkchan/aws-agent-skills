# Advanced patterns — opensearch-cluster-troubleshooter

Expert behaviours, edge cases, and per-layer detail, moved verbatim from SKILL.md (load on demand).

## Extended Mindset — four senior-engineer behaviours

Four behaviours separate a senior OpenSearch engineer from a
generalist: (1) disk watermarks are a three-stage clutch (`low: 85%`
stops allocation, `high: 90%` evacuates shards off the node,
`flood_stage: 95%` enforces a read-only block) — the well-known
write-block hits at flood, not at high; (2) JVM heap pressure is the
inverse of GC headroom — `JVMHeapPressure > 75%` sustained for 5+
minutes is the early warning, by 80% (the managed default alarm) the
cluster is already in frequent old-gen GC, and the fix is almost
never "raise the heap" (managed domains cap heap at 32 GB) but
"reduce the working set" (close indices, reduce replicas, add data
nodes, migrate to UltraWarm); (3) shard count is a load-bearing
capacity dimension — each shard carries 50-200 MB overhead, AWS
guidance targets ≤ 20 shards per GB of heap, and the working
approximation `(primary × replica) ≈ data node count × 20` keeps the
per-node shard ceiling near the safe overhead ceiling; (4) cluster
red and cluster yellow mean different things — yellow means
redundancy loss (reads and writes succeed), red means data
unavailability (a primary shard is unallocated).

## Step 0: Non-obvious behaviours that change diagnosis

- **AWS managed OpenSearch runs with three disk watermarks tuned for
  stability.** Defaults: `low: 85%`, `high: 90%`, `flood_stage: 95%`.
  Flood sets `index.blocks.read_only_allow_delete` on every index;
  writes return `ClusterBlockException` to every client. The high
  watermark (90%) quietly starts SHARD EVACUATION off the node —
  a cluster that "suddenly slows down" at 90% is paying the
  relocation cost before flood hits.
- **The flood-stage block auto-clears once disk falls below flood.**
  Operators must free disk below flood AND the block auto-clears
  once usage recovers. Force-clear via
  `PUT _all/_settings {"index.blocks.read_only_allow_delete": null}`
  only after disk is below flood.
- **`JVMHeapPressure > 75%` is the early warning, not the alarm.**
  The managed default CloudWatch alarm is 80%; by 80% the cluster
  is already in frequent old-gen GC. Senior engineers alarm at 75%
  sustained for 5 minutes. The actual OOM follows once a query
  allocates faster than GC reclaims.
- **Heap on managed OpenSearch is fixed at ~50% of instance RAM up
  to the 32 GB ceiling** (compressed-oops threshold). Operators
  cannot raise the heap beyond the instance-class ceiling — the fix
  is to scale the instance class OR reduce the working set.
- **Thread-pool queues are bounded per-node and DO NOT grow
  dynamically on managed OpenSearch.** `search` queue defaults to
  1000; `write` defaults to 10000 (varies by version). Operators who
  raise the queue via `_cluster/settings` on a managed domain find
  the setting is overridden — the fix is to scale out or throttle.
- **Shard allocation deciders report `NO` reasons that are not the
  root cause.** `_cluster/allocation/explain` returns deciders that
  voted against allocation. The FIRST decider is the binding
  constraint; the rest are cascading `NO` votes.
- **Snapshots block index deletion by design.**
  `SnapshotInProgressException` on `DELETE /index` is expected —
  the snapshot repository holds a lock on the index until completion.
  Force-deleting mid-snapshot risks repository corruption.
- **UltraWarm migration failures are usually hot-node disk or
  shard-count related.** If hot-node disk is near `high`, the
  consolidation fails with `node does not have enough disk` — the
  root cause is hot-node disk pressure, not the warm node.
- **Version upgrades can rollback silently.** If validation fails
  (incompatible mappings, deprecated API usage, cluster health red),
  the domain enters `RollbackInProgress` and reverts to the prior
  engine version. Check `ChangeProgressDetails` in `describe-domain`.
- **Split-brain is rare on managed OpenSearch (3 dedicated masters
  by default) but possible if quorum is lost.** With 3 masters,
  quorum is 2; loss of 2 masters pauses the cluster. Diagnose via
  `_cat/master` (only one master should appear) and `_cat/nodes?v`.

## Slow queries — heavy query shapes

Heavy query shapes: `terms` aggregation on a high-cardinality field
(`size: 0` with `terms: {field: <high-card>, size: 10000}`),
`wildcard` or `regexp` query on a keyword field (O(n) scan),
`script_score` with a heavy Painless script per document, deep
pagination via `from / size` beyond 10000.

## Mapping explosion — remediation detail

Mapping explosion happens when each document introduces new fields
(dynamic mapping on a high-variability source). Fix: set
`index.mapping.total_fields.limit` higher (defers the problem); set
`dynamic: false` to reject unmapped fields or `dynamic: strict` to
reject the document; flatten the offending subtree into a single
`text` field with key-value extraction at query time.

## Snapshot blocking deletion — automated snapshot behavior

Managed OpenSearch takes automated daily snapshots to a repository
named `cs-automated`. Index deletion during the snapshot window
(which can last hours) is blocked. Fix: wait for the snapshot to
complete, then delete. Force-deleting mid-snapshot risks repository
corruption. If immediate deletion is required (e.g., sensitive data),
cancel the snapshot via
`DELETE /_snapshot/<repository>/<snapshot>` and document it.

## Upgrade rollback — common triggers

Common rollback triggers: deprecated API usage by clients
(`_type`-qualified paths on OpenSearch 2.x), indices created on very
old Elasticsearch versions, custom plugins incompatible with the new
engine, cluster health red at validation time.
