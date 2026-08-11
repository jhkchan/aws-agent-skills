# Baseline (no-skill) response: reindex-from-remote-ready

This file captures what a generic assistant produces WITHOUT the
opensearch-migration-operator skill loaded.

---

You can reindex your data from the old ES 7.10 cluster to the new
OpenSearch 2.11 cluster using the reindex API. Run this on the target
cluster:

```
POST _reindex
{
  "source": {
    "remote": {
      "host": "https://search-old-es-cluster.us-east-1.es.amazonaws.com:443"
    },
    "index": "products"
  },
  "dest": {
    "index": "products"
  }
}
```

Repeat this for each index (orders, customers). You'll need to make sure
reindex.remote.whitelist is configured on the target cluster to allow
connections from the source endpoint.

Monitor the reindex progress using the task API:
`GET _tasks/<task_id>`
