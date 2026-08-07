# Eval prompt: pitr-restore-target-subnet-missing

Plan the following RDS PITR restore operation and emit the standard VERDICT
block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, ENDPOINT,
NOTES).

Operation: pitr-restore
Source: prod-orders-db
Target identifier: prod-orders-db-pitr-2026-08-07
Restore time: 2026-08-07T10:00:00Z
Target DB subnet group: dr-subnet-group
Target security group: sg-prod-rds
Target option group: default:mysql-8-0
Target parameter group: prod-mysql80
KMS key: arn:aws:kms:us-east-1:111111111111:key/prod-key

```json
{
  "SourceInstance": {
    "DBInstanceIdentifier": "prod-orders-db",
    "DBInstanceStatus": "available",
    "Engine": "mysql",
    "EngineVersion": "8.0.35",
    "AllocatedStorage": 500,
    "BackupRetentionPeriod": 7,
    "EarliestRestorableTime": "2026-07-31T00:00:00Z",
    "LatestRestorableTime": "2026-08-07T10:55:00Z",
    "StorageEncrypted": true,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/prod-key"
  },
  "TargetResourceChecks": {
    "describe-db-subnet-groups.dr-subnet-group": "DBSubnetGroupNotFoundFault",
    "describe-security-groups.sg-prod-rds": "OK",
    "describe-option-groups.default:mysql-8-0": "OK",
    "describe-db-parameter-groups.prod-mysql80": "OK",
    "kms.describe-key.prod-key": "OK"
  }
}
```
