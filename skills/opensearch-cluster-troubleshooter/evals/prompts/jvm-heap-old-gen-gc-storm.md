# Eval prompt: jvm-heap-old-gen-gc-storm

Diagnose the OpenSearch cluster incident for the following domain.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, ROOT_CAUSE, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-search-cluster` query p99 latency rose from 250 ms to
4.2 s over 30 minutes. CloudWatch `JVMHeapPressure` alarm fired. One
`circuit_breaking_exception [parent]` logged 5 minutes ago. No
`ClusterBlockException` yet.

```text
DomainName: prod-search-cluster
EngineVersion: OpenSearch_2.13
DataNodes: 7 (r6g.2xlarge.search, 32 GB heap each)
MasterNodes: 3
ClusterStatus: green

CloudWatch metrics (last 30 min):
  - JVMHeapPressure: Average = 87%, Maximum = 94% (sustained 15 min)
  - OldGenGCTime: monotonically rising (5 → 240 min cumulative)
  - SearchLatency p99: 250 ms → 4.2 s
  - ClusterIndexWritesBlocked: 0 (writes still succeed)
  - ThreadedSearchQueue Maximum: 312 (queue not saturated at 1000)
  - FreeStorageSpace Minimum: 38% (disk NOT the issue)

_cat/indices?v&s=store.size:desc (summary):
  14 open indices, 2.1 TB hot data
  4 oldest indices (events-2024-q1..q4) total 900 GB,
    search.count_last_7d = 0 on all 4
  Remaining 10 indices total 1.2 TB

Application log (last 5 min):
  [parent] Data too large, data for [<all_shards>] would be
    larger than limit of [33620709374/31.3gb]
  Old Gen used 28.4 GB of 31.0 GB
```

The `JVMHeapPressure > 75%` early-warning threshold was crossed
sustained for 15 minutes. No single query is the trigger — the
working-set growth is the cause. Identify the failing subsystem and
the upstream cause of pressure.
