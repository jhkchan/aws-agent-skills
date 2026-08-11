# Eval prompt: lock-dr-vault-ready

Plan the following DR vault lock operation and emit the standard
VERDICT block.

Operation: lock-dr-vault
Region: us-west-2
Vault name: dr-vault
Mode: COMPLIANCE
MinRetentionDays: 30
MaxRetentionDays: 3650
ChangeableForDays: 3
Justification: DR vault immutable for CIS 3.6

```json
{
  "VaultLockCheck": {
    "describe-backup-vault.dr-vault.us-west-2": {
      "exists": true,
      "VaultLock": null,
      "NumberOfRecoveryPoints": 12,
      "oldest_recovery_point_age_days": 10
    },
    "caller_iam": {
      "role": "AWSBackupOperatorRole",
      "permissions": ["backup:PutBackupVaultLockConfiguration"]
    },
    "validation": {
      "MinRetentionDays_30_lte_MaxRetentionDays_3650": true,
      "ChangeableForDays_3_lte_3_max_grace": true
    }
  }
}
```
