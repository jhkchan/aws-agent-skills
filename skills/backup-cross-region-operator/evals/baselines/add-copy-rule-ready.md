# Baseline (no-skill) response: add-copy-rule-ready

This file captures what a generic assistant produces WITHOUT the
backup-cross-region-operator skill loaded.

---

To add a cross-region copy rule to your backup plan:

```bash
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "prod-daily-with-dr",
    "Rules": [{
      "RuleName": "DailyBackup",
      "TargetBackupVaultName": "prod-daily-vault",
      "ScheduleExpression": "cron(0 5 ? * * *)",
      "CopyActions": [{
        "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault",
        "Lifecycle": {"DeleteAfterDays": 90}
      }]
    }]
  }' --region us-east-1
```

The plan will copy recovery points to us-west-2.
