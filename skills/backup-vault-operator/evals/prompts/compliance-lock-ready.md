# Eval prompt: compliance-lock-ready

Plan the following AWS Backup vault lock operation for a regulatory
archive (CIS Benchmark 3.6) and emit the standard VERDICT block.

Operation: lock-vault
Vault name: prod-compliance-vault
Region: us-east-1
Mode: COMPLIANCE
MinRetentionDays: 30
MaxRetentionDays: 3650
ChangeableForDays: 3
Justification: CIS Benchmark 3.6 (regulatory archive)

```json
{
  "VaultState": {
    "describe-backup-vault.prod-compliance-vault": {
      "VaultLock": {"LockState": null},
      "NumberOfRecoveryPoints": 14,
      "oldest_recovery_point_age_days": 12
    },
    "caller_iam": {
      "role": "AWSBackupOperatorRole",
      "permissions": ["backup:PutBackupVaultLockConfiguration"]
    },
    "retention_window_sanity": {
      "MinRetentionDays": 30,
      "MaxRetentionDays": 3650,
      "min_le_max": true,
      "changeable_for_days_le_3": true
    }
  }
}
```
