# Eval prompt: blue-green-migration-completed

Verify the following completed blue/green migration and emit the standard
VERDICT block with COMPLETED.

Domain: prod-search-cluster-blue-green-migration-completed
Region: us-east-1
Operation: verify-post-migration

```json
{
  "Domain": "prod-search-cluster-blue-green-migration-completed",
  "Region": "us-east-1",
  "Migration": {
    "Source": "Elasticsearch_7.10",
    "Target": "OpenSearch_2.11",
    "Method": "blue-green in-place upgrade",
    "Start": "2026-08-10T08:15:00Z",
    "Complete": "2026-08-10T09:45:00Z",
    "DurationMinutes": 90
  },
  "PostMigrationVerification": {
    "ClusterHealth": "green",
    "DocumentCounts": "45 indices, 2.1B docs — source=target match",
    "IndexMappings": "preserved correctly",
    "SearchQueryMatch": "100% match with pre-migration baseline",
    "Compatible40Mode": "works with elasticsearch-py 7.17 clients",
    "SnapshotRepository": "s3-migration-repo registered and verified",
    "Plugins": "analysis-icu, analysis-phonetic, ingest-attachment confirmed",
    "RedShards": 0,
    "UnassignedReplicas": 0
  }
}
```
