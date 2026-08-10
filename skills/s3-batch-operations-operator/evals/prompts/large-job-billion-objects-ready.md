# Eval prompt: large-job-billion-objects-ready

Plan the first shard of a 1-billion-object bulk KMS re-encrypt job and
emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, NOTES).

Operation: create-job
Operation type: Copy (in-place re-encrypt with new SSE-KMS key)
Source bucket: prod-data (1,000,000,000 objects, SSE-KMS old-key)
Manifest: S3 inventory report, sharded by prefix into 10 jobs of 100M objects each
Report bucket: prod-batch-reports (us-east-1)
Role: arn:aws:iam::111111111111:role/S3BatchOpsRole
RequestsPerSecond: 1000 per shard
CompletionWindow: P30D (30 days)
Priority: 50 per shard

```json
{
  "KmsQuota": {
    "VerifiedRequestLimit": 20000,
    "CombinedDecryptEncryptRate": 2000,
    "PreChecked": true
  },
  "RolePolicies": [
    "s3:GetObject on prod-data/*",
    "s3:PutObject on prod-data/*",
    "s3:GetObject on prod-inventory/manifests/*",
    "s3:PutObject on prod-batch-reports/*",
    "kms:Decrypt on arn:aws:kms:us-east-1:111111111111:key/old-key",
    "kms:Encrypt on arn:aws:kms:us-east-1:111111111111:key/new-key"
  ],
  "NewKmsKeyPolicy": {"GrantsRoleEncrypt": true},
  "Manifest": {
    "Format": "S3InventoryReport",
    "ShardStrategy": "prefix partition into 10 jobs of 100M each",
    "Shard1Prefix": "keys a-h",
    "Shard1ObjectCount": 100000000
  },
  "ReportScope": "FailedTasksOnly",
  "CallerPermissions": {
    "s3control:CreateJob": true,
    "iam:PassRole": "arnn:aws:iam::111111111111:role/S3BatchOpsRole"
  }
}
```
