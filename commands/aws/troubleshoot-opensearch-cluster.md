---
allowed-tools: Read, Bash, Grep
description: "Diagnose OpenSearch cluster incidents — ClusterBlockException (disk watermark flood), JVM heap pressure, thread pool rejections, unassigned shards, cluster red/yellow, circuit breakers, mapping explosion, snapshot-blocked deletes, UltraWarm migration failures, and upgrade rollback"
nl_triggers:
  - "OpenSearch ClusterBlockException"
  - "OpenSearch cluster red"
  - "OpenSearch cluster yellow"
  - "OpenSearch disk watermark"
  - "OpenSearch flood stage"
  - "OpenSearch JVM heap pressure"
  - "OpenSearch OutOfMemoryError"
  - "OpenSearch thread pool rejected"
  - "OpenSearch unassigned shards"
  - "OpenSearch circuit breaker"
  - "OpenSearch mapping explosion"
  - "OpenSearch slow log"
  - "OpenSearch snapshot in progress"
  - "OpenSearch upgrade rollback"
  - "OpenSearch split-brain"
  - "diagnose OpenSearch cluster"
routes_to: opensearch-cluster-troubleshooter
---

# /aws:troubleshoot-opensearch-cluster

Activate the `opensearch-cluster-troubleshooter` skill and diagnose
an Amazon OpenSearch Service cluster incident.

## What it does

Reads the cluster's failure signal (`_cluster/health`,
`_cat/allocation`, `_cat/shards`, `_cat/thread_pool`,
`_cluster/allocation/explain`, `_nodes/stats/breaker`,
`describe-domain`, CloudWatch `AWS/ES` metrics) and walks the
symptom-to-cause decision tree across eleven failure categories:

1. **DISK_WATERMARK_FLOOD** — `ClusterBlockException: FORBIDDEN/12
   index read-only / delete admin api` from a node above 95% disk
   flood stage.
2. **DISK_WATERMARK_HIGH** — `TOOMANYREQUESTS` and active shard
   evacuation from a node above 90% disk high watermark.
3. **JVM_HEAP_PRESSURE** — `JVMHeapPressure > 75%` sustained;
   old-gen GC storms; query latency degradation.
4. **JVM_OOM** — `OutOfMemoryError: Java heap space`; node dropped.
5. **THREAD_POOL_SEARCH** — `thread_pool [search] rejected
   execution`; queue full at 1000.
6. **THREAD_POOL_WRITE** — `thread_pool [write] rejected execution`;
   bulk indexing rate exceeds shard capacity.
7. **CLUSTER_RED / SHARD_ALLOCATION** — primary shard unassigned;
   `_cluster/allocation/explain` returns the binding decider.
8. **CLUSTER_YELLOW** — replica unassigned; redundancy loss.
9. **CIRCUIT_BREAKER_PARENT / FIELDDATA / REQUEST** —
   `circuit_breaking_exception` with the named breaker.
10. **MAPPING_EXPLOSION** — `Limit of total fields [...] exceeded`;
    too many dynamic fields.
11. **SNAPSHOT_BLOCKING_DELETE / COLD_HOT_MIGRATION /
    UPGRADE_ROLLBACK / SPLIT_BRAIN / SLOW_QUERY** — secondary
    categories for less common incidents.

The skill always emits a ROOT_CAUSE_IDENTIFIED verdict with positive
evidence — a failing probe that matches the symptom — never on
inference alone. If a probe cannot be obtained, the skill emits
INSUFFICIENT_DATA with the specific missing inputs and the next
probe to run.

## When to use

- An OpenSearch domain returns `ClusterBlockException` to writers.
- `_cluster/health` reports `status: red` or persistent yellow.
- CloudWatch `JVMHeapPressure > 75%` sustained, or a node dropped
  with `OutOfMemoryError`.
- Clients receive 429 from search or write traffic.
- `_cluster/allocation/explain` returns binding deciders blocking
  shard placement.
- `circuit_breaking_exception` with `[parent]`, `[fielddata]`, or
  `[request]` breaker.
- `Limit of total fields [...] exceeded` on index writes.
- `SnapshotInProgressException` on index delete.
- An in-place upgrade reports `RollbackInProgress`.

## Invocation

```
/aws:troubleshoot-opensearch-cluster <description of the OpenSearch cluster incident>
```

The skill will:

1. Read `_cluster/health?pretty` for the cluster status and the
   primary-vs-replica allocation counts.
2. Read `_cat/allocation?v` for per-node disk usage.
3. Read CloudWatch `ClusterIndexWritesBlocked`, `JVMHeapPressure`,
   `ClusterStatus.red`, `ThreadedSearchQueue`,
   `ThreadedWriteQueue`, `OldGenGCTime` over the last 30 minutes.
4. Branch on the symptom to the layer-specific probe (Steps 2-12
   in SKILL.md).
5. Read the binding allocation decider (`_cluster/allocation/explain`)
   when shards are unassigned — first decider only.
6. Emit the standard VERDICT block with positive evidence and the
   failing probe output.
7. Recommend remediation that addresses the upstream cause (e.g.,
   attach ISM policy), not just the symptom.

## Output shape

```text
TARGET: <domain-name>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
ROOT_CAUSE: <one-sentence naming the failed subsystem>
LAYER: <DISK_WATERMARK_FLOOD | JVM_HEAP_PRESSURE | THREAD_POOL_SEARCH |
        SHARD_ALLOCATION | CLUSTER_RED | CLUSTER_YELLOW |
        CIRCUIT_BREAKER_* | MAPPING_EXPLOSION | SNAPSHOT_BLOCKING_DELETE |
        UPGRADE_ROLLBACK | SPLIT_BRAIN | SLOW_QUERY | UNKNOWN>
EVIDENCE:
  - <symptom — error string or behaviour>
  - <failing probe — command and its output>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <action with CLI command>
  2. <verification command>
CONFIRM: <state-changing operation approval gate>
```

## Pre-flight

The skill requires either (a) a `_cluster/health?pretty` output and
the CloudWatch `AWS/ES` metrics for the domain, OR (b) a live
account with `aws opensearch describe-domain` and `_cat/allocation`
access. If neither is available, the skill emits
`INSUFFICIENT_DATA` with the list of required inputs.

## References

- Skill: `skills/opensearch-cluster-troubleshooter/SKILL.md`
- Reference: `skills/opensearch-cluster-troubleshooter/references/disk-watermark-and-jvm-heap-reference.md`
- Reference: `skills/opensearch-cluster-troubleshooter/references/shard-allocation-and-threadpool-reference.md`
- AWS docs: https://docs.aws.amazon.com/opensearch-service/latest/developerguide/monitoring-cloudwatch.html
