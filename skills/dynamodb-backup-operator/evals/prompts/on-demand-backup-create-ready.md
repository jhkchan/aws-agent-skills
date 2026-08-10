# Eval prompt: on-demand-backup-create-ready

Plan the following DynamoDB on-demand backup creation and emit the
standard VERDICT block.

Operation: create-backup
Source table: prod-orders-table
Backup name: prod-orders-table-pre-migration-2026-08-09

```json
{
  "SourceTable": {
    "TableName": "prod-orders-table",
    "TableStatus": "ACTIVE",
    "BillingModeSummary": {"BillingMode": "PROVISIONED"},
    "ProvisionedThroughput": {"ReadCapacityUnits": 5000, "WriteCapacityUnits": 2000},
    "TableSizeBytes": 80000000000,
    "SSEDescription": {"SSEType": "KMS"},
    "DeletionProtectionEnabled": true
  },
  "ExistingUserBackups": [
    {
      "BackupName": "prod-orders-table-weekly-2026-08-04",
      "BackupStatus": "AVAILABLE"
    }
  ],
  "BackupNameConflictCheck": "No backup with name 'prod-orders-table-pre-migration-2026-08-09' exists"
}
```
