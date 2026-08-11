# Backup Plan Templates

## Standard Templates

### Daily Backup (30-day retention)
```json
{
  "BackupPlanName": "daily-30day",
  "Rules": [{
    "RuleName": "DailyBackup",
    "ScheduleExpression": "cron(0 5 ? * MON-SAT *)",
    "StartWindowMinutes": 60,
    "CompletionWindowMinutes": 1440,
    "Lifecycle": {"DeleteAfterDays": 30},
    "CopyActions": []
  }]
}
```

### Compliance Backup (WORM, 7-year)
```json
{
  "BackupPlanName": "compliance-7yr",
  "Rules": [{
    "RuleName": "DailyCompliance",
    "ScheduleExpression": "cron(0 5 ? * * *)",
    "Lifecycle": {"DeleteAfterDays": 2555},
    "CopyActions": [{
      "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:123:backup-vault:dr-vault",
      "Lifecycle": {"DeleteAfterDays": 2555}
    }]
  }]
}
```

### Tag-Based Resource Assignment
```bash
aws backup create-backup-selection \
  --backup-plan-name tag-based-daily \
  --backup-selection '{
    "SelectionName": "ProductionResources",
    "IamRoleArn": "arn:aws:iam::123:role/service-role/AWSBackupDefaultServiceRole",
    "ListOfTags": [{"ConditionType": "STRINGEQUALS", "ConditionKey": "Backup", "ConditionValue": "daily"}]
  }'
```

## Restore Testing
```bash
aws backup start-restore-job \
  --recovery-point-arn arn:aws:backup:... \
  --metadata VolumeId=vol-new123,AvailabilityZone=us-east-1a \
  --iam-role-arn arn:aws:iam::123:role/AWSBackupRestoreRole
```

## Cross-Account via Organizations
```json
{
  "BackupPlan": {
    "Rules": [{
      "CopyActions": [{
        "DestinationBackupVaultArn": "arn:aws:backup:us-east-1:MASTER_ACCT:backup-vault:org-vault"
      }]
    }]
  }
}
```
Requires: AWS Organizations backup policy + master account vault access policy.
