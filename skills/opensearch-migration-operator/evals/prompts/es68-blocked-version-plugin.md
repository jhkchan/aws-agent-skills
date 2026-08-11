# Eval prompt: es68-blocked-version-plugin

Assess the migration readiness of the following Elasticsearch domain and
emit the standard VERDICT block.

Domain: legacy-search-cluster-es68-blocked-version-plugin
Region: us-east-1
Current version: Elasticsearch_6.8
Target version: OpenSearch_2.11
Operation: assess-migration-readiness

```json
{
  "Domain": {
    "DomainName": "legacy-search-cluster-es68-blocked-version-plugin",
    "EngineVersion": "Elasticsearch_6.8",
    "Processing": false,
    "Region": "us-east-1"
  },
  "Cluster": {
    "Status": "Active",
    "Health": "green",
    "Indices": 20,
    "StorageTB": 3,
    "InstanceType": "r5.large.search",
    "NodeCount": 3,
    "DedicatedMasters": false,
    "VPC": false
  },
  "Plugins": ["analysis-icu", "x-pack-ml", "x-pack-sql"],
  "SnapshotRepository": {
    "Registered": false
  }
}
```
