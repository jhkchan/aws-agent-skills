# Eval prompt: pitr-restore-to-point-in-time-review

Plan the following RDS point-in-time recovery restore and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: restore-pitr
Source instance: prod-orders-db
Target instance: prod-orders-db-pitr
Restore time: 2026-08-05T14:35:00Z

```json
{
  "InstanceMetadata": {
    "DBInstanceIdentifier": "prod-orders-db",
    "DBInstanceStatus": "available",
    "Engine": "mysql",
    "BackupRetentionPeriod": 7,
    "LatestRestorableTime": "2026-08-05T14:40:12Z",
    "EarliestRestorableTime": "2026-07-29T03:00:00Z",
    "OptionGroupMemberships": [{"OptionGroupName": "prod-orders-options"}],
    "OptionGroupNotes": "prod-orders-options includes TDE (Transparent Data Encryption)",
    "VpcSecurityGroups": [{"VpcSecurityGroupId": "sg-prod-rds"}],
    "DBSubnetGroup": "prod-db-subnet-group",
    "DBInstanceClass": "db.r6g.xlarge"
  }
}
```
