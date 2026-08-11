# Eval prompt: create-task-nfs-to-s3-verify-ready

Plan the following DataSync task creation and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: create-task
Source: nfs://10.0.10.20/vol/data (NFS share, on-prem)
Destination: s3://prod-migration-archive-2026 (us-east-1, SSE-KMS
  with key arn:aws:kms:us-east-1:111111111111:key/dest-cmk)
Schedule: rate(1 day)
Bandwidth throttle: 1000 Mb/s
VerifyMode: POINT_IN_TIME_CONSISTENT
PosixPermissions: PRESERVE

```json
{
  "Agent": {
    "AgentArn": "arn:aws:datasync:us-east-1:111111111111:agent/agent-001",
    "Status": "ONLINE",
    "LastConnectionTime": "2026-08-10T22:00:00Z"
  },
  "SourceLocation": {
    "LocationType": "NFS",
    "LocationUri": "nfs://10.0.10.20/vol/data",
    "AgentArns": ["arn:aws:datasync:us-east-1:111111111111:agent/agent-001"]
  },
  "DestinationLocation": {
    "LocationType": "S3",
    "LocationUri": "s3://prod-migration-archive-2026",
    "S3StorageClass": "STANDARD",
    "ObjectOwnership": "BucketOwnerEnforced"
  },
  "IamRole": {
    "Name": "datasync-task-role",
    "Trust": "datasync.amazonaws.com",
    "Permissions": [
      "s3:GetObject on arn:aws:s3:::prod-migration-archive-2026/*",
      "s3:PutObject on arn:aws:s3:::prod-migration-archive-2026/*",
      "s3:AbortMultipartUpload on arn:aws:s3:::prod-migration-archive-2026/*",
      "s3:ListBucket on arn:aws:s3:::prod-migration-archive-2026",
      "kms:Encrypt on arn:aws:kms:us-east-1:111111111111:key/dest-cmk",
      "kms:GenerateDataKey on arn:aws:kms:us-east-1:111111111111:key/dest-cmk"
    ]
  },
  "DestinationKmsKeyPolicy": {
    "Grants": "arn:aws:iam::111111111111:role/datasync-task-role kms:Encrypt + kms:GenerateDataKey"
  },
  "Scope": {
    "EstimatedBytes": 12000000000000,
    "EstimatedFiles": 5000000
  }
}
```
