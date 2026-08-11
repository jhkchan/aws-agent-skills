# Eval: cross-account-missing-vault-policy

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — destination KMS key policy correct but destination vault lacks backup:CopyIntoBackupVault grant for source account

## Prompt

Create an AWS Backup vault named source-vault in us-east-1
account 111111111111. Create a backup plan with a cross-account
copy action to vault dest-vault in us-west-2 account
222222222222. The destination KMS key policy is correctly
configured to grant the source account. However, the destination
vault dest-vault does NOT have a vault access policy granting
backup:CopyIntoBackupVault to the source account 111111111111.
