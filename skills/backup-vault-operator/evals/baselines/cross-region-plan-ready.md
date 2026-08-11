# Baseline (no-skill) response: cross-region-plan-ready

This file captures what a generic assistant produces WITHOUT the
backup-vault-operator skill loaded.

---

You can create a backup plan like:

```bash
aws backup create-backup-plan --backup-plan '{
  "BackupPlanName": "prod-daily-with-dr",
  "Rules": [{
    "RuleName": "DailyBackup",
    "TargetBackupVaultName": "prod-compliance-vault",
    "ScheduleExpression": "cron(0 5 ? * * *)",
    "Lifecycle": {"MoveToColdStorageAfterDays": 30, "DeleteAfterDays": 365}
  }]
}'
```

You'll need a separate plan or rule for cross-region copy.
