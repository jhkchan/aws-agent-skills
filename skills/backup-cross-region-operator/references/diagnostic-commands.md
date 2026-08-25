# Diagnostic Commands — Backup Cross-Region Operator

## Live-account pre-flight
**Live-account pre-flight (skip if offline plan):**
1. `backup describe-backup-vault --backup-vault-name
   <destination-vault> --region <destination-region>` — confirm
   vault exists; capture `EncryptionKeyArn`, `VaultLock`.
2. `kms describe-key --key-id <destination-key-arn> --region
   <destination-region>` — capture `KeyState`, `KeyManager`.
3. `backup describe-backup-vault --backup-vault-name <source-vault>
   --region <source-region>` — source vault lock state.
4. `backup describe-recovery-point --backup-vault-name <source-vault>
   --recovery-point-arn <arn> --region <source-region>` — capture
   recovery point `Status`.
5. `backup list-copy-jobs --region <source-region>` — active jobs.
6. `organizations describe-organization` +
   `describe-effective-policy --policy-type BACKUP_POLICY` —
   org-mode state and cross-account policy.
7. `iam get-role-policy` for the source backup role — verify
   `backup:StartCopyJob`, `backup:CopyIntoBackupVault`,
   `kms:Decrypt` on source key.
