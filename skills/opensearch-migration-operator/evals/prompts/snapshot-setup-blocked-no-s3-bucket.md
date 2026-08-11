# Eval prompt: snapshot-setup-blocked-no-s3-bucket

Set up the snapshot repository for the following domain and emit the
standard VERDICT block.

Domain: staging-search-cluster-snapshot-setup-blocked-no-s3-bucket
Region: us-east-1
Operation: snapshot-setup

```json
{
  "Domain": {
    "DomainName": "staging-search-cluster-snapshot-setup-blocked-no-s3-bucket",
    "EngineVersion": "Elasticsearch_7.10",
    "Processing": false,
    "Region": "us-east-1"
  },
  "Cluster": {
    "Status": "Active",
    "Health": "green"
  },
  "S3BucketCheck": {
    "BucketName": "migration-snapshots-nonexistent",
    "Exists": false
  },
  "IAMRoleCheck": {
    "RoleName": "OpenSearchSnapshotRole",
    "Exists": true,
    "MissingPermissions": ["s3:PutObject"]
  },
  "SnapshotRepositories": []
}
```
