# Eval prompt: snapshot-restore-verified-completed

A snapshot restore has already been executed successfully. Emit the post-
verification VERDICT block (COMPLETED form with POST_VERIFY results, the
new endpoint, and the connection-string update step).

Operation: snapshot-restore (post-verification)
Source snapshot: prod-checkout-pre-migration-2026-08-07
Target instance: prod-checkout-restored

```json
{
  "RestoreExecutionResult": {
    "DBInstanceIdentifier": "prod-checkout-restored",
    "DBInstanceStatus": "available",
    "Endpoint": {
      "Address": "prod-checkout-restored.abc123.us-east-1.rds.amazonaws.com",
      "Port": 3306
    }
  },
  "PostExecutionChecks": {
    "describe-db-instances": {
      "DBInstanceStatus": "available",
      "Engine": "mysql 8.0.35",
      "AllocatedStorage": 200,
      "StorageEncrypted": true,
      "MultiAZ": true
    },
    "connectivity": "mysql -h prod-checkout-restored.abc123.us-east-1.rds.amazonaws.com -u admin -p*** OK",
    "data_consistency": {
      "orders.orders_by_date.COUNT": 4827193,
      "orders.audit_log.MAX_created_at": "2026-08-07T09:42:11Z"
    }
  },
  "OriginalInstance": "prod-checkout is still available and unchanged"
}
```
