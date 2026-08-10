# Eval prompt: pitr-restore-in-window

Plan the following DynamoDB PITR restore operation and emit the standard
VERDICT block.

Operation: pitr-restore
Source: prod-orders-table
Target table name: prod-orders-table-pitr-2026-08-09
Restore time: 2026-08-09T10:00:00Z
Reason: bad migration applied at 10:05 UTC

```json
{
  "SourceTable": {
    "TableName": "prod-orders-table",
    "TableStatus": "ACTIVE",
    "BillingModeSummary": {"BillingMode": "PROVISIONED"},
    "ProvisionedThroughput": {"ReadCapacityUnits": 5000, "WriteCapacityUnits": 2000},
    "SSEDescription": {
      "SSEType": "KMS",
      "KMSMasterKeyArn": "arn:aws:kms:us-east-1:111111111111:key/prod-key"
    },
    "GlobalSecondaryIndexes": ["gsi-order-status"],
    "DeletionProtectionEnabled": true
  },
  "ContinuousBackups": {
    "ContinuousBackupsStatus": "ENABLED",
    "PointInTimeRecoveryDescription": {
      "PointInTimeRecoveryStatus": "ENABLED",
      "EarliestRestorableDateTime": "2026-07-05T00:00:00Z",
      "LatestRestorableDateTime": "2026-08-09T10:59:30Z"
    }
  },
  "TargetNameCheck": "prod-orders-table-pitr-2026-08-09 does not exist",
  "KmsAccess": "arn:aws:kms:us-east-1:111111111111:key/prod-key is accessible (kms:Decrypt, kms:GenerateDataKey granted)"
}
```
