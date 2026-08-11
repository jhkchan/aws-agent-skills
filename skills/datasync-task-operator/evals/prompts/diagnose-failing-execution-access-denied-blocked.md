# Eval prompt: diagnose-failing-execution-access-denied-blocked

Diagnose the failing DataSync task execution and emit the standard
VERDICT block.

Operation: diagnose-failing-execution
Task: arn:aws:datasync:us-east-1:111111111111:task/task-001
  (name: nfs-to-s3-archive)
Source: nfs://10.0.10.20/vol/data
Destination: s3://prod-migration-archive-2026

```json
{
  "LatestExecution": {
    "TaskExecutionArn": "arn:aws:datasync:us-east-1:111111111111:task/task-001/execution/exec-009",
    "Status": "ERROR",
    "StartTime": "2026-08-09T22:00:00Z",
    "BytesTransferred": 2310000000000,
    "BytesWritten": 2290000000000,
    "EstimatedFilesToTransfer": 5000000,
    "FilesTransferred": 870000,
    "VerificationFilesFailed": 0,
    "ErrorCode": "AccessDenied",
    "ErrorDetail": "AccessDenied (403) for s3:PutObject on arn:aws:s3:::prod-migration-archive-2026/logs/app.log"
  },
  "Task": {
    "Status": "AVAILABLE",
    "Options": {
      "VerifyMode": "POINT_IN_TIME_CONSISTENT",
      "PosixPermissions": "PRESERVE"
    }
  },
  "Agent": {
    "Status": "ONLINE",
    "LastConnectionTime": "2026-08-10T21:55:00Z"
  },
  "IamRole": {
    "Name": "datasync-task-role",
    "AttachedPolicies": [
      "s3:GetObject on arn:aws:s3:::prod-migration-archive-2026/*",
      "s3:ListBucket on arn:aws:s3:::prod-migration-archive-2026",
      "kms:Encrypt, kms:GenerateDataKey on dest-cmk"
    ],
    "Missing": "s3:PutObject on arn:aws:s3:::prod-migration-archive-2026/*"
  },
  "DestinationKmsKeyPolicy": {
    "Grants": "arn:aws:iam::111111111111:role/datasync-task-role kms:Encrypt + kms:GenerateDataKey"
  }
}
```
