# Eval prompt: search-thread-pool-rejection

Diagnose the OpenSearch cluster incident for the following domain.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, ROOT_CAUSE, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-search-cluster` clients receive HTTP 429
(`EsRejectedOperationException`). Read-heavy dashboards began failing
at 14:30 UTC. The cluster is green; no `ClusterBlockException`; heap
and disk are healthy.

```text
DomainName: prod-search-cluster
EngineVersion: OpenSearch_2.13
DataNodes: 5 (r6g.xlarge.search)
MasterNodes: 3
ClusterStatus: green

_cat/thread_pool/search?v output (per node):
  node-1  active=4  queue=1000  queue_size=1000  rejected=18271
  node-2  active=4  queue=1000  queue_size=1000  rejected=17934
  node-3  active=4  queue=1000  queue_size=1000  rejected=18112
  node-4  active=4  queue=1000  queue_size=1000  rejected=17893
  node-5  active=4  queue=1000  queue_size=1000  rejected=18044

CloudWatch metrics (last 30 min):
  - ThreadedSearchQueue: Maximum = 1000 (queue full on all nodes)
  - SearchRate: 4800 searches/sec (sustained 25 min)
  - JVMHeapPressure Average: 52% (heap healthy)
  - FreeStorageSpace Minimum: 41% (disk healthy)
  - CPUUtilization Average: 88%

Recent slow log entries (top 3):
  took[8.4s], took[7.9s], took[8.1s] — all from:
  "query": { "size": 0, "aggs": {
    "by_user": { "terms": { "field": "user_id", "size": 10000 } } } }
  Cardinality of user_id field: 8.4M distinct values
```

A high-cardinality terms aggregation is the trigger. Managed
OpenSearch does not let you raise the search queue via
`_cluster/settings`. Identify the layer and the upstream cause of
saturation.
