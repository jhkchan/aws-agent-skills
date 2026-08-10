# Eval prompt: snapshot-restore-backup-creating

Plan the following DynamoDB snapshot-style restore operation and emit
the standard VERDICT block.

Operation: snapshot-restore
Source backup ARN: arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table/backup/01709999999999-migrating
Target table name: prod-orders-table-restored-2026-08-09

```json
{
  "Backup": {
    "BackupArn": "arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table/backup/01709999999999-migrating",
    "BackupName": "prod-orders-table-pre-migration-2026-08-09",
    "BackupStatus": "CREATING",
    "BackupCreationDateTime": "2026-08-09T11:00:00Z",
    "BackupSizeBytes": 0
  },
  "TargetNameCheck": "prod-orders-table-restored-2026-08-09 does not exist",
  "IamPermissions": "Caller has dynamodb:RestoreTableFromBackup on the backup ARN"
}
```
