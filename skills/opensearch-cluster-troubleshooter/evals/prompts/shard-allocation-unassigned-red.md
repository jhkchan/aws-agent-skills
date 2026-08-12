# Eval prompt: shard-allocation-unassigned-red

Diagnose the OpenSearch cluster incident for the following domain.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, ROOT_CAUSE, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-search-cluster` `_cluster/health` flipped from green
to red at 09:14 UTC after data node `data-3` was replaced via AWS
support. Searches on `events-2025-q3` return
`search_phase_execution_exception: all shards failed`.

```text
DomainName: prod-search-cluster
EngineVersion: OpenSearch_2.13
DataNodes: 2 (was 3, data-3 being replaced)
MasterNodes: 3
ClusterStatus: red

_cluster/health?pretty output (excerpt):
  "status": "red"
  "number_of_data_nodes": 2
  "active_primary_shards": 240
  "active_shards": 360
  "unassigned_shards": 24
  "unassigned_primary_shards": 12

_cat/allocation?v output:
  data-1  shards=180  disk.percent=91
  data-2  shards=180  disk.percent=90
  UNASSIGNED  shards=24

_cluster/allocation/explain (for unassigned primary events-2025-q3/0):
  "current_state": "unassigned"
  "allocation_decisions": [
    { "decider": "max_shards_per_node", "decision": "NO",
      "explanation": "this shard allocation would put the node over
        the cluster max_shards_per_node setting" },
    { "decider": "disk_watermark.high", "decision": "NO",
      "explanation": "the node has 9% free disk; informational only" }
  ]

CloudWatch metrics (last 30 min):
  - JVMHeapPressure Average: 48% (healthy)
  - FreeStorageSpace Minimum: 8.8 GB
  - ClusterStatus.red: 1
```

The FIRST decider in the allocation_explain list is the binding
constraint per the SKILL convention. Read the first decider to
identify the binding cause; the rest cascade.
