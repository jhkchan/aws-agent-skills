# Eval prompt: es710-inplace-upgrade-ready

Assess the migration readiness of the following Elasticsearch domain and
emit the standard VERDICT block (OPERATION, VERDICT, PRE_CHECKS, STEPS,
POST_VERIFY, ENDPOINT, CLIENT_NOTES).

Domain: prod-search-cluster-es710-inplace-upgrade-ready
Region: us-east-1
Current version: Elasticsearch_7.10
Target version: OpenSearch_2.11
Operation: assess-migration-readiness

```json
{
  "Domain": {
    "DomainName": "prod-search-cluster-es710-inplace-upgrade-ready",
    "EngineVersion": "Elasticsearch_7.10",
    "Processing": false,
    "Region": "us-east-1"
  },
  "Cluster": {
    "Status": "Active",
    "Health": "green",
    "Indices": 45,
    "StorageTB": 12,
    "InstanceType": "r6g.2xlarge.search",
    "NodeCount": 6,
    "DedicatedMasters": true,
    "EncryptionAtRest": true,
    "VPC": true
  },
  "Plugins": ["analysis-icu", "analysis-phonetic", "ingest-attachment"],
  "SnapshotRepository": {
    "Name": "s3-migration-repo",
    "Registered": true,
    "Verified": true
  }
}
```
