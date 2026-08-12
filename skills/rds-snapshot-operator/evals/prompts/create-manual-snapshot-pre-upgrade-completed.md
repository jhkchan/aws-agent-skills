# Eval prompt: create-manual-snapshot-pre-upgrade-completed

Plan the following RDS manual snapshot creation and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: create-snapshot
Instance: prod-orders-db
Snapshot identifier: prod-orders-db-pre-upgrade-20260805
Reason: pre-upgrade safety snapshot before engine version upgrade

```json
{
  "InstanceMetadata": {
    "DBInstanceIdentifier": "prod-orders-db",
    "DBInstanceStatus": "available",
    "Engine": "mysql",
    "EngineVersion": "8.0.35",
    "StorageType": "gp3",
    "AllocatedStorage": 500,
    "Encrypted": true,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/orders-cmk",
    "MultiAZ": true,
    "BackupRetentionPeriod": 7,
    "DeletionProtection": true,
    "OptionGroupMemberships": [{"OptionGroupName": "prod-orders-options"}]
  },
  "KmsKey": {
    "Enabled": true,
    "KeyState": "Enabled"
  },
  "ExistingSnapshots": {
    "HasSnapshotWithIdentifier": false
  }
}
```
