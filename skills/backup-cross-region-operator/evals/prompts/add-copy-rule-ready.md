# Eval prompt: add-copy-rule-ready

Plan the following AWS Backup cross-region copy-rule addition and
emit the standard VERDICT block (OPERATION, VERDICT, TARGET,
PRE_CHECKS, STEPS, POST_VERIFY, STATE, NOTES).

Operation: add-copy-rule
Plan name: prod-daily-with-dr
Source region: us-east-1
Source vault: prod-daily-vault
Destination region: us-west-2
Destination vault ARN: arn:aws:backup:us-west-2:111111111111:backup-vault:dr-vault
Destination KMS key: arn:aws:kms:us-west-2:111111111111:key/xyz
Copy rule lifecycle: DeleteAfterDays=90

```json
{
  "DestinationCheck": {
    "describe-backup-vault.dr-vault.us-west-2": {
      "exists": true,
      "EncryptionKeyArn": "arn:aws:kms:us-west-2:111111111111:key/xyz",
      "VaultLock": {"LockState": "LOCKED", "Mode": "COMPLIANCE",
                    "MaxRetentionDays": 3650},
      "NumberOfRecoveryPoints": 12
    },
    "kms.describe-key.xyz.us-west-2": {
      "KeyState": "Enabled",
      "KeyManager": "CUSTOMER",
      "policy_grants": ["kms:GenerateDataKey", "kms:Decrypt"],
      "service_principal": "backup.us-west-2.amazonaws.com"
    },
    "caller_iam": {
      "role": "AWSBackupOperatorRole",
      "permissions": ["backup:CreateBackupPlan"]
    }
  },
  "LifecycleCheck": {
    "DeleteAfterDays": 90,
    "MaxRetentionDays": 3650,
    "fits": true
  }
}
```
