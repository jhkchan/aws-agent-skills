# Eval prompt: cross-region-plan-ready

Plan the following AWS Backup plan creation with cross-region copy
and emit the standard VERDICT block.

Operation: create-plan
Plan name: prod-daily-with-dr
Region: us-east-1
TargetBackupVault: prod-compliance-vault
Schedule: cron(0 5 ? * * *)
StartWindowMinutes: 480
CompletionWindowMinutes: 1440
Lifecycle: MoveToColdStorageAfterDays=30, DeleteAfterDays=365
CopyActions:
  - DestinationBackupVaultArn: arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault
    Lifecycle: DeleteAfterDays=90

```json
{
  "PlanChecks": {
    "source_vault.describe-backup-vault.prod-compliance-vault": {
      "VaultLock": {"LockState": "LOCKED", "Mode": "COMPLIANCE", "MaxRetentionDays": 3650}
    },
    "destination_vault.describe-backup-vault.dr-vault.us-west-2": {
      "exists": true,
      "EncryptionKeyArn": "arn:aws:kms:us-west-2:111111111111:key/xyz"
    },
    "destination_kms.policy_grants": {
      "service_principal": "backup.us-west-2.amazonaws.com",
      "permissions": ["kms:Decrypt", "kms:GenerateDataKey"]
    },
    "lifecycle_sanity": {
      "MoveToColdStorageAfterDays": 30,
      "DeleteAfterDays": 365,
      "move_before_delete": true,
      "delete_within_max_retention": true
    }
  }
}
```
