# Eval prompt: copy-snapshot-cross-region-dr-completed

Plan the following RDS cross-region snapshot copy and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: copy-snapshot
Source snapshot: prod-orders-db-pre-upgrade-20260805
Source region: us-east-1
Target snapshot: prod-orders-db-dr-20260805
Target region: us-west-2

```json
{
  "SourceSnapshot": {
    "DBSnapshotIdentifier": "prod-orders-db-pre-upgrade-20260805",
    "Status": "available",
    "Encrypted": true,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/orders-cmk",
    "AllocatedStorage": 500,
    "Engine": "mysql"
  },
  "TargetKmsKey": {
    "KeyId": "arn:aws:kms:us-west-2:111111111111:key/dr-cmk",
    "Enabled": true,
    "KeyState": "Enabled"
  }
}
```
