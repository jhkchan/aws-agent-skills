# Backup Vault Operator — boilerplate CLI patterns (vault create, plan, selection, manual backup)

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

### Create a backup vault with KMS encryption and tags (moved verbatim from SKILL.md)

```bash
aws backup create-backup-vault \
  --backup-vault-name "prod-daily-vault" \
  --encryption-key-arn arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-1234-567890abcdef \
  --creator-request-id "$(date +%s)" \
  --tags Environment=prod,Owner=platform-team
```

Use `--creator-request-id` for idempotency — re-running with the same
ID returns the existing vault without error.

---

### Create a backup plan with schedule, lifecycle, cross-region copy (moved verbatim from SKILL.md)

```bash
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "prod-daily-with-dr",
    "Rules": [
      {
        "RuleName": "DailyBackup",
        "TargetBackupVaultName": "prod-daily-vault",
        "ScheduleExpression": "cron(0 5 ? * * *)",
        "StartWindowMinutes": 480,
        "CompletionWindowMinutes": 1440,
        "Lifecycle": {"MoveToColdStorageAfterDays": 30, "DeleteAfterDays": 365},
        "CopyActions": [
          {
            "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault",
            "Lifecycle": {"DeleteAfterDays": 90}
          }
        ]
      }
    ]
  }'
```

`ScheduleExpression` is in UTC. `StartWindowMinutes` must be less than
`CompletionWindowMinutes`. The `CopyActions` array defines the
cross-region copy with a separate lifecycle in the destination region.

---

### Create a backup selection by tag (moved verbatim from SKILL.md)

```bash
aws backup create-backup-selection \
  --backup-plan-id "$(aws backup list-backup-plans --query 'BackupPlansList[?BackupPlanName==`prod-daily-with-dr`].BackupPlanId' --output text)" \
  --backup-selection '{
    "SelectionName": "prod-tagged-daily",
    "IamRoleArn": "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole",
    "ListOfTags": [{"ConditionType": "STRINGEQUALS", "ConditionKey": "backup", "ConditionValue": "daily"}],
    "Conditions": {
      "StringEquals": {"aws:ResourceTag/environment": "prod"},
      "StringNotEquals": {"aws:ResourceTag/criticality": "dev"}
    }
  }'
```

Use `ListOfTags` for forward-compatible selections (new resources
tagged `backup=daily` automatically enroll). Use `Resources` for
static ARN lists. `Conditions` supports `StringEquals`,
`StringLike`, `StringNotEquals` on `aws:ResourceTag/*`.

---

### Start a manual backup job (moved verbatim from SKILL.md)

```bash
aws backup start-backup-job \
  --backup-vault-name "prod-daily-vault" \
  --resource-arn arn:aws:ec2:us-east-1:111111111111:instance/i-0123456789abcdef0 \
  --iam-role-arn "arn:aws:iam::111111111111:role/AWSBackupDefaultServiceRole" \
  --idempotency-token "$(date +%s)" \
  --start-window-minutes 60 \
  --complete-window-minutes 1440 \
  --lifecycle '{"MoveToColdStorageAfterDays": 30, "DeleteAfterDays": 365}'
```

