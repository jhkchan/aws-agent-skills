# Eval prompt: aurora-clone-from-snapshot-completed

Plan the following Aurora cluster clone from snapshot and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: clone-from-snapshot
Source snapshot: prod-aurora-cluster-snap-20260805
Target cluster: prod-aurora-clone

```json
{
  "SourceSnapshot": {
    "DBClusterSnapshotIdentifier": "prod-aurora-cluster-snap-20260805",
    "Status": "available",
    "Engine": "aurora-mysql",
    "EngineVersion": "8.0.mysql_aurora.3.05.2",
    "StorageType": "aurora",
    "Encrypted": true,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/aurora-cmk",
    "SnapshotType": "manual"
  },
  "KmsKey": {
    "Enabled": true
  },
  "TargetConfig": {
    "DBSubnetGroupName": "prod-db-subnet-group",
    "VpcSecurityGroupId": "sg-prod-aurora"
  }
}
```
