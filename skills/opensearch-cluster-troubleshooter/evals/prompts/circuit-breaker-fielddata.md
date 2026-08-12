# Eval prompt: circuit-breaker-fielddata

Diagnose the OpenSearch cluster incident for the following domain.
Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, ROOT_CAUSE, LAYER, EVIDENCE,
REMEDIATION).

Symptom: `prod-search-cluster` returns HTTP 503 with
`circuit_breaking_exception` for queries that aggregate on the
`request_body` field. Other queries succeed. Cluster is green.

```text
DomainName: prod-search-cluster
EngineVersion: OpenSearch_2.13
DataNodes: 5 (r6g.xlarge.search)
MasterNodes: 3
ClusterStatus: green

Application log (failing request):
  {
    "error": {
      "type": "circuit_breaking_exception",
      "reason": "[fielddata] Data too large, data for
        [request_body] would be larger than limit of
        [1288490188/1.2gb]",
      "bytes_wanted": 1410000000,
      "bytes_limit": 1288490188,
      "durability": "TRANSIENT"
    }
  }

_nodes/stats/breaker?pretty (excerpt):
  "breakers": {
    "fielddata": {
      "limit_size_in_bytes": 1288490188,
      "estimated_size_in_bytes": 1310000000,
      "tripped": 14
    },
    "parent": {
      "limit_size_in_bytes": 3060164198,
      "estimated_size_in_bytes": 1410000000,
      "tripped": 0
    }
  }

events-2025-q3/_mapping (excerpt):
  "request_body": {
    "type": "text",
    "fielddata": true
  }

CloudWatch metrics (last 30 min):
  - JVMHeapPressure Average: 62%
  - ClusterIndexWritesBlocked: 0
  - ClusterStatus.green: 1
```

The breaker that tripped is `[fielddata]`, not `[parent]`. The parent
breaker has not tripped (tripped: 0). The `request_body` field is
mapped as `text` with `fielddata: true`. Identify the layer and the
field-level remediation.
