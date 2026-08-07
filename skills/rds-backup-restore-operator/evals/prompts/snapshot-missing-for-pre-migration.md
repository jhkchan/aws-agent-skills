# Eval prompt: snapshot-missing-for-pre-migration

The operator wants to restore from a manual snapshot
"prod-pre-migration-snap" before applying a risky schema change. Plan the
restore operation and emit the standard VERDICT block.

Operation: snapshot-restore
Source snapshot: prod-pre-migration-snap
Target identifier: prod-checkout-restored

```json
{
  "SourceInstance": {
    "DBInstanceIdentifier": "prod-checkout",
    "DBInstanceStatus": "available",
    "Engine": "postgres",
    "EngineVersion": "15.4",
    "AllocatedStorage": 200,
    "BackupRetentionPeriod": 0,
    "StorageEncrypted": true
  },
  "SnapshotChecks": {
    "describe-db-snapshots.prod-pre-migration-snap": "DBSnapshotNotFoundFault",
    "describe-db-snapshots.automated.prod-checkout": []
  }
}
```
