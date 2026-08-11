# Eval prompt: create-vault-ready

Plan the following AWS Backup vault creation and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, STATE, NOTES).

Operation: create-vault
Vault name: prod-daily-vault
Region: us-east-1
EncryptionKeyArn: arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-1234-567890abcdef
Tags: Environment=prod, Owner=platform-team

```json
{
  "VaultCheck": {
    "describe-backup-vault.prod-daily-vault": {
      "error": "ResourceNotFoundException",
      "status": "vault does not exist"
    },
    "kms.describe-key.abcd1234": {
      "KeyState": "Enabled",
      "KeyManager": "CUSTOMER",
      "policy_grants": ["kms:GenerateDataKey", "kms:Decrypt"],
      "service_principal": "backup.us-east-1.amazonaws.com"
    },
    "caller_iam": {
      "role": "AWSBackupOperatorRole",
      "permissions": ["backup:CreateBackupVault"]
    }
  },
  "ExistingVault": null
}
```
