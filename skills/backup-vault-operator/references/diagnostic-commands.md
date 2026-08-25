# Backup Vault Operator — pre-flight metadata gate and per-operation pre-check listings

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

## Pre-flight: vault/KMS/IAM metadata gate (moved verbatim from SKILL.md)

Run before classification. `describe-backup-vault` returns the full
vault metadata including `VaultLock`, `EncryptionKeyArn`, `NumberOfRecoveryPoints`.
`list-backup-vaults` returns up to 100/page (use `--next-token`).

**Live-account pre-flight (skip if offline plan):**
1. `backup describe-backup-vault --backup-vault-name <name>` — confirm
   vault exists, capture `EncryptionKeyArn`, `VaultLock`, `CreationDate`,
   `NumberOfRecoveryPoints`.
2. `kms describe-key --key-id <key-arn>` — capture `KeyState` and
   `KeyManager` (must be `Enabled` and `AWS` or `CUSTOMER`).
3. `backup list-backup-vaults` — cross-reference vault list.
4. `backup list-recovery-points-by-backup-vault --backup-vault-name <name>`
   — capture recovery points for restore operations; verify the target
   recovery point is `Status: COMPLETED`.
5. `backup list-backup-plans` + `list-backup-selections` — capture
   current plans and selections, check for overlap.
6. `backup describe-backup-job --backup-job-id <id>` — for diagnose
   operations on a specific job.

**Malformed input:** emit `VERDICT: ERROR` with reason and remediation.

| Attribute | Effect on operation |
|---|---|
| `VaultLock.LockState: LOCKED` (compliance) | Retention cannot be shortened; vault cannot be deleted. Plan must respect the existing `MaxRetentionDays`. |
| `VaultLock.LockState: LOCKED` (governance) | Lock can be removed by privileged principal — treat as soft but warn in NOTES. |
| `VaultLock.ChangeableForDays > 0` | Vault is in the grace window — lock can still be modified or removed. Surface explicitly. |
| `KeyState: Disabled` / `PendingDeletion` | KMS key unusable for new backups. BLOCKED. |
| `EncryptionKeyArn` unset | Default AWS-managed key (`aws/backup`) used. Surface as finding for compliance requirements. |
| `NumberOfRecoveryPoints: 0` | Restore not possible. BLOCKED. |
| Overlapping tag-based selections | Allowed but generates duplicate recovery points (and cost). Surface as INFO. |

---

### Step 1: Pre-check gate — per-operation checks (full listing) (moved verbatim from SKILL.md)

**For ALL operations:**
1. Vault name spelled correctly (case-sensitive).
2. Vault exists in the same account+region as the operation
   (`describe-backup-vault` returns it).
3. IAM role holds the required `backup:*` permission.

**For create-vault:**
4. KMS key ARN exists and is `Enabled`.
5. KMS key policy grants
   `kms:GenerateDataKey`, `kms:Decrypt` to
   `backup.<region>.amazonaws.com`.
6. Vault name not already in use.

**For vault lock (compliance mode):**
4. Vault is not already in compliance mode (`VaultLock.LockState !=
   LOCKED` with `Mode: COMPLIANCE`) unless the operation is to
   lengthen `MaxRetentionDays`.
5. `MaxRetentionDays` is greater than or equal to the longest
   retention in any plan writing to the vault.
6. `MinRetentionDays` is greater than or equal to the longest current
   recovery point age in the vault (else existing points cannot be
   deleted on the existing schedule).
7. `ChangeableForDays` <= 3 (max grace window).

**For create-plan:**
4. At least one rule has `StartWindowMinutes` and `CompletionWindowMinutes`
   within service limits.
5. Cross-region copy destination region has a vault with KMS key.
6. Lifecycle `MoveToColdStorageAfterDays` < `DeleteAfterDays` (cannot
   delete before moving to cold).
7. Schedule uses CRON or simple `rate()`. Verify timezone is UTC.

**For create-selection:**
4. Plan exists (`list-backup-plans` returns the plan ID).
5. At least one of `ListOfTags`, `Resources`, `Conditions` is
   populated (empty selection matches nothing).
6. IAM role `RoleArn` exists and has
   `backup:StartBackupJob` / `backup:PutBackupVaultNotifications`
   trust.
7. No overlapping tag-based selections (INFO-level warning, not
   BLOCKED).

**For start-backup (manual):**
4. Resource ARN exists.
5. Backup vault exists and is reachable.
6. IAM role for the selection exists.

**For start-restore:**
4. Recovery point exists in the target vault and `Status: COMPLETED`.
5. Recovery point is not expired (within retention window).
6. `Metadata` includes resource-type-specific fields (InstanceId for
   EC2, NewDBInstanceIdentifier for RDS).
7. For cross-region restore: destination region IAM permissions
   verified.
8. For PITR: continuous backup is enabled on the resource
   (`describe-recovery-point --backup-vault-name <vault>
   --recovery-point-arn <arn>` shows `IsEncrypted: true` and
   `ResourceType` continuous-capable, plus `CalculatedLifecycle`
   reflects continuous backup window).

**For diagnose operations:**
5. `describe-backup-job --backup-job-id <id>` returns the job.
6. `describe-backup-vault --backup-vault-name <name>` reflects current
   state.
7. CloudTrail `StartBackupJob`, `StartCopyJob`, `StartRestoreJob`
   events within last 7 days for the resource.

