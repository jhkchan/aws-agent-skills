---
name: opensearch-cluster-troubleshooter
description: >-
  Diagnoses Amazon OpenSearch Service cluster incidents across eleven
  failure categories: ClusterBlockException from disk watermark
  breach (85% flood-stage read-only block, 90% / 95% allocation
  freeze), JVM heap pressure above 75% triggering old-gen GC storms
  and OutOfMemoryError, thread-pool rejections on the search and write
  queues, shard allocation failures and unassigned shards, cluster
  yellow / red status, split-brain from lost quorum, slow-log analysis
  for heavy queries and mapping explosion (too many fields), circuit
  breaker errors (parent, fielddata, request), index deletion during
  snapshot, cold-node to hot-node migration failures, and version
  upgrade rollback scenarios. Walks symptoms to a verified root cause
  with evidence-backed probes and emits ROOT_CAUSE_IDENTIFIED or
  INSUFFICIENT_DATA.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and cluster health output. Live-account diagnosis uses
  aws opensearch describe-domain, describe-domain-config, list-domain-names, aws es describe-elasticsearch-domain (legacy), aws cloudwatch get-metric-statistics on the AWS/ES namespace, aws s3 ls for snapshot
  repositories, the _cluster/health, _cat/shards, _cat/allocation, _cat/thread_pool, _nodes/stats, and _cluster/settings OS APIs, and aws logs filter-log-events on the OpenSearch application logs (AWS CLI v2, SSO
  or key-based credentials).
keywords:
- OpenSearch
- Elasticsearch
- ClusterBlockException
- disk watermark
- flood stage
- JVM heap pressure
- old gen GC
- OutOfMemoryError
- thread pool rejection
- search queue
- write queue
- unassigned shards
- cluster red
- cluster yellow
- split-brain
- slow log
- mapping explosion
- circuit breaker
- parent circuit breaker
- fielddata circuit breaker
- index deletion during snapshot
- cold node
- hot node
- UltraWarm
- migration failure
- upgrade rollback
- troubleshooting
tags:
- opensearch
- analytics
- troubleshooting
- cluster-health
- disk-watermark
- jvm-heap
- thread-pool
- shard-allocation
- circuit-breaker
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an Amazon OpenSearch Service cluster incident — ClusterBlockException (read-only block, write block), cluster status red or yellow, JVM heap pressure alarms, search or write thread-pool
    rejections, unassigned shards, shard allocation failures, circuit breaker trips (parent / fielddata / request), slow-query investigations, mapping explosion (too many fields), index deletion blocked by an
    in-progress snapshot, cold-to-hot storage migration failures, an in-place upgrade rollback, or a split-brain event. Use whenever the symptom is cluster-wide (not a single index mapping question) and the
    operator needs the failing subsystem named with positive evidence.
  when_not_to_use: Index mapping design or analyzer tuning (use the OpenSearch _mapping API and the index mapping reference), application-side query authoring (use the search DSL and slow logs), OpenSearch
    Serverless collection incidents (use a Serverless-specific skill — this skill targets managed OpenSearch Service domains only), VPC endpoint posture audits for the OpenSearch domain (use
    ec2-security-group-auditor), or IAM fine-grained-access-control user/role provisioning (use iam-least-privilege-advisor). This skill diagnoses cluster-health incidents; it does not design mappings or audit
    steady-state access posture.
  activation_triggers:
  - OpenSearch ClusterBlockException
  - OpenSearch cluster red
  - OpenSearch cluster yellow
  - OpenSearch disk watermark
  - OpenSearch flood stage disk.watermark.flood
  - OpenSearch JVM heap pressure
  - OpenSearch OutOfMemoryError
  - OpenSearch old gen GC
  - OpenSearch thread pool rejected
  - OpenSearch search queue rejected
  - OpenSearch write queue rejected
  - OpenSearch unassigned shards
  - OpenSearch shard allocation failed
  - OpenSearch circuit breaker
  - OpenSearch parent breaker tripped
  - OpenSearch fielddata circuit breaker
  - OpenSearch mapping explosion
  - OpenSearch too many fields
  - OpenSearch slow query
  - OpenSearch slow log
  - OpenSearch index delete during snapshot
  - OpenSearch snapshot in progress
  - OpenSearch UltraWarm migration failed
  - OpenSearch cold node to hot node
  - OpenSearch upgrade rollback
  - OpenSearch split-brain
  - troubleshoot OpenSearch cluster
  invocation_schema: 'Input: either (a) a symptom description (error message from a client, observed cluster status, an alarm name), optionally paired with the _cluster/health output, _cat/shards output, and recent
    CloudWatch metrics, OR (b) a DomainName plus caller context (region, observed error) for live-account diagnosis. Output: a deterministic TARGET / VERDICT / ROOT_CAUSE / LAYER / EVIDENCE / REMEDIATION block
    where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {DISK_WATERMARK_FLOOD, DISK_WATERMARK_HIGH, JVM_HEAP_PRESSURE, JVM_OOM, THREAD_POOL_SEARCH, THREAD_POOL_WRITE, SHARD_ALLOCATION,
    CLUSTER_YELLOW, CLUSTER_RED, SPLIT_BRAIN, SLOW_QUERY, MAPPING_EXPLOSION, CIRCUIT_BREAKER_PARENT, CIRCUIT_BREAKER_FIELDDATA, CIRCUIT_BREAKER_REQUEST, SNAPSHOT_BLOCKING_DELETE, COLD_HOT_MIGRATION,
    UPGRADE_ROLLBACK, UNKNOWN}.'
  invocation_example: "# Minimal valid input (offline symptom classification):\nSymptom: \"OpenSearch domain prod-logs-cluster returns\nClusterBlockException: blocked by: [FORBIDDEN/12/index read-only / delete\n\
    admin api];\" the cluster status is yellow and writes are failing.\nDomainName: prod-logs-cluster\nEngineVersion: OpenSearch_2.13\nClusterStatus: yellow\nHotDataNodes: 3 (r6g.large.search)\nMasterNodes:\
    \ 3\nEBSVolumeSize: 100 GB per node\nLastCloudWatchAlarm: ClusterIndexWritesBlocked > 0 for 12 minutes"
---

# OpenSearch Cluster Troubleshooter

## Quick start

- **Symptom → layer map (the first plausible match drives the first
  probe):** `ClusterBlockException: index read-only / delete admin api`
  → DISK_WATERMARK_FLOOD (85% flood stage); `cluster status: red` →
  CLUSTER_RED / SHARD_ALLOCATION / SPLIT_BRAIN; `cluster status: yellow`
  → CLUSTER_YELLOW / SHARD_ALLOCATION; `JVMHeapPressure > 75%` alarm →
  JVM_HEAP_PRESSURE; `OutOfMemoryError: Java heap space` → JVM_OOM;
  `thread_pool [search] rejected execution` → THREAD_POOL_SEARCH;
  `thread_pool [write] rejected execution` → THREAD_POOL_WRITE;
  `circuit_breaking_exception` with `parent breaker` →
  CIRCUIT_BREAKER_PARENT; unassigned shards in `_cat/shards` →
  SHARD_ALLOCATION; `SnapshotInProgressException` on delete →
  SNAPSHOT_BLOCKING_DELETE.
- **Always verify with a probe, never guess.** Each layer has a single
  command that proves or disproves it. A ROOT_CAUSE_IDENTIFIED verdict
  requires positive evidence — a failing probe that matches the
  symptom — not a process of elimination that "must be the disk."
- **The three numbers every senior OpenSearch engineer keeps in head:
  85 / 75 / 20.** Disk at 85% triggers the flood-stage read-only
  block (managed default `low: 85%` / `high: 90%` / `flood: 95%`;
  the well-known write-block hits at flood). JVM heap pressure above
  75% triggers old-gen GC storms. Shard count per data node should
  stay near 20 × (data node count) — i.e. `(primary × replica)` should
  equal data node count × 20 as a steady-state ceiling. These three
  thresholds catch the large majority of cluster incidents before
  they cascade.
- **Read-only block is a symptom, not the root cause.** When flood
  trips, OpenSearch sets `index.blocks.read_only_allow_delete` on
  every index. Freeing disk and rerouting shards clears the block,
  but the disk pressure that triggered it has an upstream cause —
  unbounded index growth, missing ISM policy, replica increase, or
  shard relocation. Always trace one layer up from the flood block.
- **INSUFFICIENT_DATA is acceptable.** Cluster incidents frequently
  present with partial telemetry (no `_cat/shards` snapshot, no
  CloudTrail for a config change). If a failing probe cannot be
  obtained, emit INSUFFICIENT_DATA with the specific missing inputs
  and the next probe to run — do not declare a verdict on inference.

## Mindset

An OpenSearch incident is almost always a resource pressure event
that crossed a published threshold. The cluster was healthy
yesterday; today the disk crossed flood, the heap crossed 75%, the
shard count crossed 20 × node, or a snapshot ran longer than
expected. Senior search engineers do not start by reading mapping
files or query DSL — they start with `_cluster/health`,
`_cat/allocation`, and the CloudWatch `ClusterIndexWritesBlocked`,
`JVMHeapPressure`, and `ClusterStatus.red` metrics. Only once
resource pressure is ruled out do they look at mapping design, slow
queries, or upgrade state.

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

## Quick reference — symptom triage table

| Symptom phrase / error | Layer | First probe |
|---|---|---|
| `ClusterBlockException: blocked by: [FORBIDDEN/12/index read-only / delete admin api]` | DISK_WATERMARK_FLOOD | `_cat/allocation?v` (disk.percent per node); CloudWatch `FreeStorageSpace` |
| `ClusterBlockException: TOOMANYREQUESTS` / writes blocked alarm | DISK_WATERMARK_HIGH or JVM_HEAP_PRESSURE | `_cluster/health?pretty`, `ClusterIndexWritesBlocked` |
| `cluster_status: red` | CLUSTER_RED / SHARD_ALLOCATION / SPLIT_BRAIN | `_cat/shards?v` for UNASSIGNED; `_cat/nodes?v` for node loss |
| `cluster_status: yellow` | CLUSTER_YELLOW / SHARD_ALLOCATION | `_cluster/health?pretty` (`relocating_shards`, `unassigned_shards`) |
| `JVMHeapPressure > 75%`, GC spikes | JVM_HEAP_PRESSURE | CloudWatch `JVMHeapPressure`, `OldGenGCTime` |
| `OutOfMemoryError: Java heap space`, node dropped | JVM_OOM | CloudWatch `JVMMemoryPressure`, application logs |
| `thread_pool [search] rejected execution` | THREAD_POOL_SEARCH | `_cat/thread_pool/search?v` |
| `thread_pool [write] rejected execution`, 429 | THREAD_POOL_WRITE | `_cat/thread_pool/write?v` |
| `circuit_breaking_exception [parent]` | CIRCUIT_BREAKER_PARENT | `_nodes/stats/breaker`, query shape |
| `circuit_breaking_exception [fielddata]` | CIRCUIT_BREAKER_FIELDDATA | `_nodes/stats/indices/fielddata` |
| Unassigned shards in `_cat/shards` | SHARD_ALLOCATION | `_cluster/allocation/explain` |
| Slow query, slow log > 5s | SLOW_QUERY | `_cat/indices` slow log, query DSL |
| `Limit of total fields [1000] exceeded` | MAPPING_EXPLOSION | `_mapping?pretty`, field count |
| `SnapshotInProgressException` on delete | SNAPSHOT_BLOCKING_DELETE | `_snapshot/_status` |
| UltraWarm migration: `node does not have enough disk` | COLD_HOT_MIGRATION | hot node disk |
| `RollbackInProgress` after upgrade | UPGRADE_ROLLBACK | `describe-domain-config` |
| Two masters visible, cluster split | SPLIT_BRAIN | `_cat/master`, `_cat/nodes?v` |

## Pre-flight: cluster state and gather-info gate

Before running symptom-specific probes, gather the canonical cluster
state and short-circuit on cluster-wide events that mimic per-index
failures.

```bash
# Domain configuration (EngineVersion, ClusterConfig, EBSOptions,
# VPCOptions, SnapshotOptions, ChangeProgressDetails)
aws opensearch describe-domain --domain-name <domain> --output json

# Domain config history (last change to cluster config)
aws opensearch describe-domain-config --domain-name <domain> --output json

# AWS Health (regional events, OpenSearch scheduled maintenance)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --service OPENSEARCH_SERVICE --region us-east-1 --output json

# OpenSearch _cluster/health (the single most informative endpoint)
curl -sS "https://<domain-endpoint>/_cluster/health?pretty" \
  -H "Content-Type: application/json"
```

### Cluster-state short-circuit

| Signal | Effect on diagnosis |
|---|---|
| `status: green` but client reports errors | Issue is per-index, per-query, or per-client; not cluster-wide. Pivot to the error string. |
| `status: yellow`, `relocating_shards: > 0` | Active rebalance. Writes succeed. Investigate only if `unassigned_shards` non-zero or yellow persists > 30 min. |
| `status: yellow`, `unassigned_shards: > 0` | Replica shards cannot allocate. Jump to SHARD_ALLOCATION. |
| `status: red` | Primary shard unallocated. Data unavailability — jump to CLUSTER_RED as high-severity. |
| `timed_out: true` | Cluster overloaded. Treat as JVM_HEAP_PRESSURE or thread-pool exhaustion until proven otherwise. |
| `number_of_nodes: decreased` vs expected | Node loss. Investigate via CloudTrail and AWS Health. |

If the input is malformed (missing DomainName, absent symptom, no
error string), emit:

```text
TARGET: <domain-name or unknown>
VERDICT: INSUFFICIENT_DATA
ROOT_CAUSE: UNKNOWN
REASON: Input is missing required context — at minimum a symptom
  description (the error string, observed cluster status, or an
  alarm name) and the DomainName (with region for live diagnosis).
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact error string
  or observed symptom, (2) the DomainName and region, and (3) for
  live diagnosis, the most recent `_cluster/health?pretty` output
  and the CloudWatch `ClusterIndexWritesBlocked`, `JVMHeapPressure`,
  and `ClusterStatus.red` metrics over the last 30 minutes.
```

## Process — Diagnostic decision tree (apply in symptom order)

The diagnostic tree is symptom-driven. Pick the entry point based on
the observed symptom, then walk the layer-specific probes in order.
Each layer ends with either a positive root-cause confirmation
(failing probe that matches the symptom) or a pass that moves to the
next layer. **Never emit ROOT_CAUSE_IDENTIFIED without a failing
probe that matches the symptom.**

### Step 0: Non-obvious behaviours that change diagnosis

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

### Step 1: Symptom entry — pick the diagnostic branch

| Symptom | Branch |
|---|---|
| `ClusterBlockException: FORBIDDEN/12/index read-only / delete admin api` | Step 2 — Disk watermarks |
| `ClusterBlockException` generic / writes blocked | Step 2 + Step 3 (heap) |
| `cluster status: red` | Step 5 — Cluster red |
| `cluster status: yellow` persistent > 30 min | Step 6 — Cluster yellow |
| `JVMHeapPressure > 75%` alarm / `OutOfMemoryError` | Step 3 — JVM heap |
| `thread_pool [search] rejected`, `[write] rejected` | Step 4 — Thread pools |
| `circuit_breaking_exception` | Step 7 — Circuit breakers |
| Unassigned shards in `_cat/shards` | Step 8 — Shard allocation |
| Slow query, slow log > 5s | Step 9 — Slow query |
| `Limit of total fields [1000] exceeded` | Step 10 — Mapping explosion |
| `SnapshotInProgressException` on delete | Step 11 — Snapshot blocking |
| `RollbackInProgress`, upgrade issue | Step 12a — Upgrade rollback |
| None of the above | Step 12 — INSUFFICIENT_DATA |

### Step 2: Disk watermarks — ClusterBlockException read-only

Symptom: writes return
`ClusterBlockException: blocked by: [FORBIDDEN/12/index read-only / delete
admin api]`. CloudWatch `ClusterIndexWritesBlocked > 0` alarm fires.
Reads still succeed until heap pressure cascades.

```bash
# Per-node disk usage
curl -sS "https://<domain-endpoint>/_cat/allocation?v" \
  -H "Content-Type: application/json"

# CloudWatch FreeStorageSpace (managed-service source of truth)
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name FreeStorageSpace \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Minimum --output json
```

Any node with `disk.percent >= 95` is at flood stage. The read-only
block applies cluster-wide as soon as ANY node hits flood.

| Stage | Threshold | Cluster effect | Recovery |
|---|---|---|---|
| `low` | 85% | New shards do not allocate to this node. | Free disk below 85%; cluster rebalances. |
| `high` | 90% | Cluster actively relocates shards OFF this node. | Free disk below 85% (cluster continues relocating until then). |
| `flood_stage` | 95% | `index.blocks.read_only_allow_delete` set. Writes blocked. | Free disk below 95%; block auto-clears. Force-clear via `PUT _all/_settings {"index.blocks.read_only_allow_delete": null}` only after disk is below flood. |

#### Identify why disk filled

- **Unbounded index growth, no ISM policy:** `_cat/indices?v&s=index`
  shows old date-suffix indices (`logs-2024-01`) accumulating without
  rollover or deletion. Fix: configure an ISM policy to roll over and
  delete old indices.
- **Replica count increase:** `_settings` shows
  `number_of_replicas: 2` instead of 1 — disk usage doubles on the
  replicated indices. Fix: revert via
  `PUT /<index>/_settings {"number_of_replicas": 1}`.
- **Force-merge in progress:** a recent `_forcemerge?max_num_segments=1`
  call temporarily doubles segment file size during the merge. Fix:
  wait; do not force-merge under disk pressure.
- **Snapshot restore:** `_snapshot/_status` shows a restore in
  progress; the restored indices consume disk. Fix: cancel the restore
  or expand the cluster.

**Verdicts:**
- Flood stage confirmed, root cause is unbounded growth:
  ROOT_CAUSE_IDENTIFIED, `LAYER: DISK_WATERMARK_FLOOD`. Fix: delete or
  rollover old indices, free disk below 85%, force-clear the block
  after disk recovers.
- High watermark with active relocation: ROOT_CAUSE_IDENTIFIED,
  `LAYER: DISK_WATERMARK_HIGH`. Fix: add data nodes OR reduce replica
  count OR delete indices.

### Step 3: JVM heap pressure — old-gen GC storms and OOM

Symptom: CloudWatch `JVMHeapPressure > 75%` sustained; `OldGenGCTime`
rising; queries slow dramatically; eventual `OutOfMemoryError: Java
heap space` if untreated.

```bash
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name JVMHeapPressure \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json

# Per-node heap breakdown
curl -sS "https://<domain-endpoint>/_cat/nodes?v&h=name,heap.percent,ram.percent,node.role" \
  -H "Content-Type: application/json"

# Breaker trip evidence
aws logs filter-log-events \
  --log-group-name /aws/opensearch/domains/<domain>/application-logs \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"OutOfMemoryError" OR "circuit_breaking_exception" OR "Old Gen"' \
  --output json
```

**Decision matrix:**

| Heap pressure pattern | Likely cause | Fix direction |
|---|---|---|
| Sustained 75-85%, gradual climb | Working set grew (open indices, fielddata) | Close old indices; reduce replicas; add data nodes |
| Spike to 95%+ on a single query | Single heavy query (terms agg on high-card field) | Rewrite query; cap via `_cluster/settings` |
| Spike correlates with fielddata size | Fielddata loaded for keyword/text field | Disable fielddata; use the `keyword` subtype |
| Spike correlates with snapshot or force-merge | Background task competing for heap | Reschedule off-peak |
| `OutOfMemoryError` followed by node drop | Heap exhausted; JVM killed by SIGKILL | Reduce working set before restart; raise Support ticket |

The canonical triad — close old indices, reduce replicas, add data
nodes — resolves most heap-pressure incidents without raising the
heap (fixed on managed domains up to 32 GB).

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: JVM_HEAP_PRESSURE` (or
`JVM_OOM` if the error already occurred).

### Step 4: Thread-pool rejections

Symptom: client receives 429 or
`EsRejectedExecutionException: rejected execution of
org.opensearch.action.search.SearchTransportService` (search) or
`org.opensearch.action.bulk.BulkShardRequest` (write).

```bash
curl -sS "https://<domain-endpoint>/_cat/thread_pool/search?v&h=node_name,name,active,queue,queue_size,rejected,largest" \
  -H "Content-Type: application/json"

curl -sS "https://<domain-endpoint>/_cat/thread_pool/write?v&h=node_name,name,active,queue,queue_size,rejected,largest" \
  -H "Content-Type: application/json"
```

The `rejected` column counts rejected tasks since node start. A
non-zero, growing `rejected` count is the positive evidence.

| Pool | Default queue | Cause pattern | Fix |
|---|---|---|---|
| `search` | 1000 | Concurrent or slow searches | Scale data nodes; optimise slow queries (Step 9); throttle client |
| `write` | 10000 (varies) | Bulk indexing rate exceeds shard capacity | Reduce bulk batch size; raise `index.refresh_interval`; scale data nodes |
| `get` | 1000 | High rate of multi-get by ID | Usually transient; scale out |

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: THREAD_POOL_SEARCH` or
`THREAD_POOL_WRITE`.

### Step 5: Cluster red — primary shard unassigned

Symptom: `_cluster/health` returns `status: red`. At least one
primary shard is unallocated; data is unavailable for that index.

```bash
curl -sS "https://<domain-endpoint>/_cluster/health?pretty" -H "Content-Type: application/json"
curl -sS "https://<domain-endpoint>/_cat/shards?v&h=index,shard,prirep,state,unassigned.reason" \
  -H "Content-Type: application/json" | grep UNASSIGNED
curl -sS -X POST "https://<domain-endpoint>/_cluster/allocation/explain?pretty" \
  -H "Content-Type: application/json" -d \
  '{"index": "<index-name>", "shard": <shard-id>, "primary": true}'
```

`allocate_explanation` returns a list of deciders. The FIRST decider
is the binding constraint. Verdicts: disk-watermark-blocked primary
allocation → ROOT_CAUSE_IDENTIFIED, `LAYER: SHARD_ALLOCATION` (cause:
DISK_WATERMARK_HIGH); node loss with no replicas →
`LAYER: CLUSTER_RED` (cause: NODE_LOSS, restore from snapshot);
`max_shards_per_node` exhausted → `LAYER: SHARD_ALLOCATION` (cause:
SHARD_CEILING).

### Step 6: Cluster yellow — replica unassigned

Symptom: `_cluster/health` returns `status: yellow`. All primaries
allocated; at least one replica is not. Writes succeed. The
diagnostic path mirrors Step 5 with `primary: false`. Common causes:
replica count exceeds (data node count − 1); a data node is in the
`restart` or `leaving` state; allocation deciders blocked replica
placement.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CLUSTER_YELLOW`.

### Step 7: Circuit breakers

Symptom: queries fail with `circuit_breaking_exception`. The error
names the breaker: `[parent]`, `[fielddata]`, or `[request]`.

```bash
curl -sS "https://<domain-endpoint>/_nodes/stats/breaker?pretty" -H "Content-Type: application/json"
```

| Breaker | Default limit | Triggers when |
|---|---|---|
| `parent` | 95% of heap | Sum of all child breakers + in-flight allocations |
| `fielddata` | 40% of heap | Fielddata cache for text/keyword fields |
| `request` | 60% of heap | Per-request allocation (aggregations, sorting) |
| `in_flight_requests` | 100% of heap | HTTP/transport in-flight buffers |
| `accounting` | 100% of heap | Lucene segments memory |

Fix direction: `fielddata` trip → disable fielddata on the field, use
the `keyword` subtype. `request` trip → rewrite the aggregation
(reduce cardinality, paginate). `parent` trip → read the inner
breaker that pushed parent over and fix it.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: CIRCUIT_BREAKER_PARENT` /
`CIRCUIT_BREAKER_FIELDDATA` / `CIRCUIT_BREAKER_REQUEST`.

### Step 8: Shard allocation decider reference

For both Step 5 (red) and Step 6 (yellow), read the FIRST decider in
`_cluster/allocation/explain`; the rest cascade.

| First decider | Fix |
|---|---|
| `disk_watermark.*` | Free disk (Step 2) |
| `max_shards_per_node` | Raise cap OR add data nodes OR reduce shard count |
| `same_shard` | Add data nodes; replica count too high for node count |
| `filter` / `awareness` | Fix `_cluster/settings` allocation attributes / add nodes in missing awareness attribute |
| `shard_size` | Shard too large to relocate — `_split` the index |
| `recovery_after_time` | Recovery in progress; wait |

### Step 9: Slow queries — slow log analysis

Symptom: queries slow, `ThreadedSearchQueue` rises, slow logs record
> 5s per query.

```bash
aws cloudwatch get-metric-statistics --namespace AWS/ES \
  --metric-name SearchLatency \
  --dimensions Name=DomainName,Value=<domain> Name=ClientId,Value=<account> \
  --start-time $(date -d '-1 hour' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,p99 --output json

aws logs filter-log-events \
  --log-group-name /aws/opensearch/domains/<domain>/index-search-slow-logs \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"took[]" OR "query[]"' --output json
```

Heavy query shapes: `terms` aggregation on a high-cardinality field
(`size: 0` with `terms: {field: <high-card>, size: 10000}`),
`wildcard` or `regexp` query on a keyword field (O(n) scan),
`script_score` with a heavy Painless script per document, deep
pagination via `from / size` beyond 10000.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SLOW_QUERY`.

### Step 10: Mapping explosion

Symptom: write failures with
`Limit of total fields [1000] has been exceeded`.

```bash
curl -sS "https://<domain-endpoint>/<index>/_mapping?pretty" -H "Content-Type: application/json"
```

Mapping explosion happens when each document introduces new fields
(dynamic mapping on a high-variability source). Fix: set
`index.mapping.total_fields.limit` higher (defers the problem); set
`dynamic: false` to reject unmapped fields or `dynamic: strict` to
reject the document; flatten the offending subtree into a single
`text` field with key-value extraction at query time.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: MAPPING_EXPLOSION`.

### Step 11: Snapshot blocking index deletion

Symptom: `DELETE /<index>` returns
`SnapshotInProgressException: snapshot is in progress`.

```bash
curl -sS "https://<domain-endpoint>/_snapshot/_status?pretty" -H "Content-Type: application/json"
```

Managed OpenSearch takes automated daily snapshots to a repository
named `cs-automated`. Index deletion during the snapshot window
(which can last hours) is blocked. Fix: wait for the snapshot to
complete, then delete. Force-deleting mid-snapshot risks repository
corruption. If immediate deletion is required (e.g., sensitive data),
cancel the snapshot via
`DELETE /_snapshot/<repository>/<snapshot>` and document it.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: SNAPSHOT_BLOCKING_DELETE`.

### Step 12a: Upgrade rollback

Symptom: an in-place engine-version upgrade was initiated; the domain
shows `UpgradeProcessing: false` and `RollbackInProgress: true`.

```bash
aws opensearch describe-domain --domain-name <domain> --output json | \
  jq '.DomainStatus.{EngineVersion, UpgradeProcessing, ChangeProgressDetails}'
```

Common rollback triggers: deprecated API usage by clients
(`_type`-qualified paths on OpenSearch 2.x), indices created on very
old Elasticsearch versions, custom plugins incompatible with the new
engine, cluster health red at validation time.

**Verdict:** ROOT_CAUSE_IDENTIFIED, `LAYER: UPGRADE_ROLLBACK`.

### Step 12b: INSUFFICIENT_DATA

If none of the above produced a positive root-cause match, OR a probe
requires operator input (live-account credentials, missing
`_cluster/health` output), emit INSUFFICIENT_DATA with the specific
missing pieces and the next probe to run once the info is available.

## Output format

```text
TARGET: <domain-name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
ROOT_CAUSE: <one-sentence naming the failed subsystem>
LAYER: <DISK_WATERMARK_FLOOD | DISK_WATERMARK_HIGH | JVM_HEAP_PRESSURE |
        JVM_OOM | THREAD_POOL_SEARCH | THREAD_POOL_WRITE |
        SHARD_ALLOCATION | CLUSTER_YELLOW | CLUSTER_RED |
        SPLIT_BRAIN | SLOW_QUERY | MAPPING_EXPLOSION |
        CIRCUIT_BREAKER_PARENT | CIRCUIT_BREAKER_FIELDDATA |
        CIRCUIT_BREAKER_REQUEST | SNAPSHOT_BLOCKING_DELETE |
        COLD_HOT_MIGRATION | UPGRADE_ROLLBACK | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <domain> in <region>. Proceed?
  (yes/no)"
```

### Worked example — flood-stage disk block

```text
TARGET: prod-logs-cluster
VERDICT: ROOT_CAUSE_IDENTIFIED
ROOT_CAUSE: ClusterBlockException is the flood-stage read-only block;
  node `prod-logs-cluster-data-3` is at 97% disk; unbounded index
  growth — `logs-2024-*` indices dating back 14 months have no ISM
  policy to roll over or delete.
LAYER: DISK_WATERMARK_FLOOD
EVIDENCE:
  - Symptom: every write returns `ClusterBlockException: blocked by:
    [FORBIDDEN/12/index read-only / delete admin api]`;
    `ClusterIndexWritesBlocked` = 1 for 12 minutes.
  - Probe: `_cat/allocation?v` shows data-3 at `disk.percent: 97`;
    the other two nodes are at 91% and 88%.
  - Probe: `_cat/indices/logs-*?v&s=index` returns 427 monthly
    indices from 2023-02 to 2024-12; oldest 14 months have no ISM
    policy attached.
  - Passing: `JVMHeapPressure` Average = 41%; `status: yellow`;
    no `EsRejectedExecutionException`.
REMEDIATION:
  1. Delete the oldest 6 months of unqueried indices:
     DELETE /logs-2023-02,logs-2023-03,logs-2023-04,logs-2023-05,logs-2023-06,logs-2023-07
  2. Verify disk drops below flood; the block auto-clears once all
     nodes are below 95%.
  3. If the block does not auto-clear within 5 minutes, force-clear:
     PUT _all/_settings {"index.blocks.read_only_allow_delete": null}
  4. Long-term: attach an ISM policy that rolls monthly indices to
     UltraWarm at 30 days and deletes at 12 months.
CONFIRM: Before deleting indices or clearing the block, emit and await:
  "CONFIRM: About to delete logs-2023-02 through logs-2023-07 on
   prod-logs-cluster. Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom. A "process of elimination" erodes trust.
- NEVER free disk and stop there. The flood-stage block is a symptom;
  the upstream cause (no ISM, replica increase, force-merge under
  pressure) re-triggers within days. Name the upstream cause.
- NEVER recommend raising the JVM heap on a managed OpenSearch domain
  without first checking the instance class. Heap is fixed at 50% of
  instance RAM up to 32 GB.
- NEVER recommend raising thread-pool queue sizes as a remediation.
  Managed OpenSearch overrides `_cluster/settings` thread-pool edits.
  Scale out or throttle the client.
- NEVER read past the first decider in `_cluster/allocation/explain`.
  The remaining deciders are cascading `NO` votes.
- NEVER force-delete an index mid-snapshot. Force-deleting risks
  repository corruption that requires AWS Support to repair.
- NEVER conclude "split-brain" without checking the master quorum.
  Managed OpenSearch uses 3 dedicated master nodes by default; a
  true split-brain requires an AZ partition. The more common cause
  of "two masters visible" is a stale `_cat/nodes` cache.
- NEVER treat cluster yellow as a P0. Yellow means redundancy loss;
  reads and writes succeed. Treat as P2 unless node loss may cascade.
- NEVER force-clear the flood-stage read-only block before freeing
  disk below 95%. Force-clearing while disk is still above flood
  causes the block to immediately re-apply.
- NEVER scale the cluster as the first remediation for heap pressure.
  Reducing the working set (close indices, reduce replicas, migrate
  to UltraWarm) is faster, cheaper, and addresses the actual cause.
- NEVER recommend `_forcemerge` under disk or heap pressure.
  Force-merge temporarily doubles segment file size during the merge.
- NEVER initiate an in-place version upgrade when the cluster is red
  or has `JVMHeapPressure > 75%`. Validation will fail and roll back.
- NEVER delete snapshots manually to free space. Manual S3 deletes
  from the snapshot bucket corrupt the repository.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`DELETE /<index>`, `POST /<index>/_close`, `PUT _cluster/settings`,
  `PUT _all/_settings`, `DELETE /_snapshot/...`,
  `POST /<index>/_forcemerge`), emit and await operator approval.
- **Read-only first.** Every probe in the diagnostic tree is
  read-only. Do not perform state-changing operations as diagnostic
  probes.
- **`DELETE /<index>`** is irreversible. Enumerate the index list
  explicitly; never use wildcards in `DELETE /logs-*`.
- **Force-clearing the flood-stage block** is safe ONLY after disk
  is below 95%. Confirm disk usage first.
- **Cluster scaling** triggers a blue/green deployment (30+ minutes).
- **Version upgrade** triggers validation. Confirm cluster health is
  green and heap < 75% first.
- **Bulk remediation batch limit.** Batch state-changing operations
  into groups of at most 5 indices; emit a single CONFIRM per batch.

## Remediation guidance

### For DISK_WATERMARK_FLOOD
Free disk below 85% by deleting or closing old indices; verify the
block auto-clears within 5 minutes; force-clear via
`PUT _all/_settings {"index.blocks.read_only_allow_delete": null}` if
needed; attach an ISM policy to roll over and delete future indices.

### For DISK_WATERMARK_HIGH
Free disk below 85% (cluster continues relocating until then); add
data nodes if pressure is from intended growth; reduce replica count
if replicas are the cause.

### For JVM_HEAP_PRESSURE / JVM_OOM
Close indices not actively queried; reduce replica count temporarily;
disable fielddata on text fields; migrate cold indices to UltraWarm;
scale the instance class up to raise heap (capped at 32 GB).

### For THREAD_POOL_SEARCH / THREAD_POOL_WRITE
For search: tune slow queries (Step 9); add data nodes. For write:
reduce bulk batch size; raise `index.refresh_interval`; add data nodes.

### For SHARD_ALLOCATION
Read the first decider in `_cluster/allocation/explain`; free disk,
add nodes, or fix allocation filters. Raise
`cluster.max_shards_per_node` if the cap is the binding constraint
(deferred fix).

### For CIRCUIT_BREAKER_*
Identify the inner breaker (parent wraps the others). For fielddata:
disable fielddata on the field. For request: rewrite the aggregation
(reduce cardinality, paginate). For parent: fix the inner breaker.

### For MAPPING_EXPLOSION
Set `dynamic: false` or `strict` on the offending subtree; raise
`index.mapping.total_fields.limit` as a short-term deferral; flatten
the offending subtree into a single text field.

### For SNAPSHOT_BLOCKING_DELETE
Poll `_snapshot/_status` until no snapshots are IN_PROGRESS; delete
the index after the snapshot completes; for immediate deletion,
cancel the snapshot explicitly via
`DELETE /_snapshot/<repo>/<snapshot>` and document it.

### For UPGRADE_ROLLBACK
Read the validation failure from `describe-domain`
`ChangeProgressDetails` and the application logs; fix the trigger
(deprecated APIs, incompatible mappings, cluster health red);
re-initiate after the cluster is green and heap < 75%.

## Domain

AWS CloudOps / Analytics — OpenSearch Service Managed Clusters,
Cluster Health Diagnostics, JVM Pressure Analysis, Shard Allocation
Decoders, Disk Watermark Recovery, Circuit Breaker Triage, Index
Lifecycle Management, Snapshot Lifecycle, In-place Version Upgrades.

## AWS documentation

- **Amazon OpenSearch Service Developer Guide — Cluster health** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/monitoring-cloudwatch.html
- **Disk-based allocation** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/size-your-clusters.html
- **JVM heap pressure and OOM** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/handling-errors.html
- **Index State Management** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ism.html
- **UltraWarm and cold storage** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/ultrawarm.html
- **Snapshots** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-snapshots.html
- **In-place upgrades** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/version-maturity.html
- **Circuit breakers** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/circuit-breaker.html
- **CloudWatch metrics for OpenSearch** — https://docs.aws.amazon.com/opensearch-service/latest/developerguide/managedomains-cloudwatch-metrics.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
