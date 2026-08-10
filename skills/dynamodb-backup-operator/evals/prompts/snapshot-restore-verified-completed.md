# Eval prompt: snapshot-restore-verified-completed

Post-verification of a completed DynamoDB snapshot-style restore. Emit
the standard VERDICT block (post-verification form).

Operation: snapshot-restore (post-verification after execution)
Source backup: arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table/backup/01708888888888-weekly
Target table: prod-orders-table-restored-2026-08-09

```json
{
  "RestoreExecution": {
    "CommandExecuted": "aws dynamodb restore-table-from-backup --target-table-name prod-orders-table-restored-2026-08-09 --backup-arn arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table/backup/01708888888888-weekly",
    "Result": {
      "TableArn": "arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table-restored-2026-08-09",
      "TableStatus": "ACTIVE"
    }
  },
  "PostExecutionChecks": {
    "DescribeTable": {
      "TableName": "prod-orders-table-restored-2026-08-09",
      "TableStatus": "ACTIVE",
      "ItemCount": 4827193
    },
    "SourceBackupItemCount": 4827193,
    "GsiStatus": {
      "gsi-order-status": "ACTIVE",
      "gsi-customer-id": "ACTIVE"
    },
    "SentinelCheck": {
      "Operation": "GetItem(prod-orders-table-restored-2026-08-09, id=sentinel-001)",
      "Result": "Item returned with expected attributes"
    },
    "OriginalSourceTable": {
      "TableName": "prod-orders-table",
      "TableStatus": "ACTIVE"
    }
  }
}
```
