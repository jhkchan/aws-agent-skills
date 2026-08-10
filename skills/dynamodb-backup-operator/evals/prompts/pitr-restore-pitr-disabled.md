# Eval prompt: pitr-restore-pitr-disabled

Plan the following DynamoDB PITR restore operation and emit the standard
VERDICT block.

Operation: pitr-restore
Source: prod-orders-table
Target table name: prod-orders-table-pitr-2026-08-09
Restore time: 2026-08-09T10:00:00Z
Reason: bad migration applied at 10:05 UTC, need to rewind to 10:00 UTC

```json
{
  "SourceTable": {
    "TableName": "prod-orders-table",
    "TableStatus": "ACTIVE",
    "BillingModeSummary": {"BillingMode": "PROVISIONED"},
    "ProvisionedThroughput": {"ReadCapacityUnits": 5000, "WriteCapacityUnits": 2000},
    "TableSizeBytes": 80000000000,
    "SSEDescription": {"SSEType": "KMS"},
    "GlobalSecondaryIndexes": ["gsi-order-status", "gsi-customer-id"],
    "DeletionProtectionEnabled": true
  },
  "ContinuousBackups": {
    "ContinuousBackupsStatus": "ENABLED",
    "PointInTimeRecoveryDescription": {
      "PointInTimeRecoveryStatus": "DISABLED"
    }
  },
  "ExistingUserBackups": [
    {
      "BackupArn": "arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table/backup/01708888888888-weekly",
      "BackupName": "prod-orders-table-weekly-2026-08-04",
      "BackupStatus": "AVAILABLE",
      "BackupCreationDateTime": "2026-08-04T03:00:00Z"
    }
  ],
  "TargetNameCheck": "prod-orders-table-pitr-2026-08-09 does not exist"
}
```
