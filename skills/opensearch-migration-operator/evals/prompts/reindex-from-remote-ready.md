# Eval prompt: reindex-from-remote-ready

Plan the reindex-from-remote migration for the following clusters and
emit the standard VERDICT block.

Source domain: old-es-cluster-reindex-from-remote-ready
Target domain: new-os-cluster-reindex-from-remote-ready
Region: us-east-1
Operation: new-cluster-reindex

```json
{
  "SourceDomain": {
    "DomainName": "old-es-cluster-reindex-from-remote-ready",
    "EngineVersion": "Elasticsearch_7.10",
    "Status": "Active",
    "Health": "green",
    "Endpoint": "search-old-es-cluster.us-east-1.es.amazonaws.com",
    "Indices": ["products", "orders", "customers"],
    "StorageTB": 5.2,
    "VPC": false
  },
  "TargetDomain": {
    "DomainName": "new-os-cluster-reindex-from-remote-ready",
    "EngineVersion": "OpenSearch_2.11",
    "Status": "Active",
    "Health": "green",
    "Endpoint": "search-new-os-cluster.us-east-1.es.amazonaws.com",
    "TargetIndicesCreated": true,
    "ReindexRemoteWhitelist": "configured for source endpoint",
    "VPC": false
  },
  "NetworkConnectivity": "verified — target can reach source on port 443",
  "IAMPermissions": "opensearch:ESHttp* and es:ESHttp* confirmed"
}
```
