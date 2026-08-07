# Eval prompt: retention-zero-pitr-disabled

The operator dropped the wrong table on prod-analytics-db 30 minutes ago and
wants a PITR restore. Plan the operation and emit the standard VERDICT block.

Operation: pitr-restore
Source: prod-analytics-db
Target identifier: prod-analytics-db-pitr
Restore time: 2026-08-07T08:00:00Z

```json
{
  "SourceInstance": {
    "DBInstanceIdentifier": "prod-analytics-db",
    "DBInstanceStatus": "available",
    "Engine": "postgres",
    "EngineVersion": "15.4",
    "AllocatedStorage": 1000,
    "BackupRetentionPeriod": 0,
    "LatestRestorableTime": null,
    "EarliestRestorableTime": null,
    "StorageEncrypted": true
  },
  "ManualSnapshots": [
    {
      "DBSnapshotIdentifier": "prod-analytics-quarterly-2026-07-01",
      "SnapshotCreateTime": "2026-07-01T03:00:00Z",
      "Status": "available"
    }
  ]
}
```
