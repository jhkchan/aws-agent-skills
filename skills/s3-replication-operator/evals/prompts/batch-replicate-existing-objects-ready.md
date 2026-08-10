# Eval prompt: batch-replicate-existing-objects-ready

Plan the following S3 Batch Operations replication job for existing
objects and emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: batch-replicate
Source: prod-logs-source-us-east-1 (us-east-1, account 111111111111)
Destination: prod-logs-dr-eu-west-1 (eu-west-1, account 111111111111)
Filter: prefix "logs/"
Estimated object count: ~12 million objects, 4.2 TB total

```json
{
  "S3InventoryConfig": {
    "Id": "prod-logs-inventory-daily",
    "Destination": "s3://prod-logs-inventory-prod/inv/",
    "Schedule": "Daily",
    "LastManifest": "2026-08-09T03:00:00Z",
    "IncludedFields": ["Bucket", "Key", "Size", "LastModifiedDate", "ReplicationStatus"]
  },
  "ExistingReplicationRule": {
    "ID": "dr-crr-rtc",
    "Status": "Enabled",
    "Filter": {"Prefix": "logs/"}
  },
  "BatchOperationsRole": {
    "Arn": "arn:aws:iam::111111111111:role/s3-batch-repl-role",
    "Permissions": [
      "s3:GetObject on arn:aws:s3:::prod-logs-source-us-east-1/*",
      "s3:ReplicateObject on arn:aws:s3:::prod-logs-dr-eu-west-1/*",
      "kms:Decrypt on source CMK arn:aws:kms:us-east-1:111111111111:key/source-cmk",
      "kms:Encrypt on destination CMK arn:aws:kms:eu-west-1:111111111111:key/dest-cmk",
      "s3:GetObject on the manifest bucket arn:aws:s3:::prod-logs-inventory-prod/*"
    ]
  },
  "ExistingBatchJobsForPrefix": "none"
}
```
