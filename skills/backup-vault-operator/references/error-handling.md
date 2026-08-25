# Backup Vault Operator — diagnostic flows and failure remediation

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

## Diagnostic flows (moved verbatim from SKILL.md)

### Backup job failed or stuck

1. `describe-backup-job --backup-job-id <id>` — capture `State`,
   `StatusMessage`, `PercentDone`, `CreatedBy`, `BackupType`.
2. Common failures:
   - `FAILED: IAM role not authorized` — the
     `AWSBackupDefaultServiceRole` lacks
     `ec2:CreateTags`, `ec2:DescribeVolumes`,
     `kms:GenerateDataKey`, or service-specific permissions.
   - `FAILED: Resource not found` — the resource was deleted between
     the schedule trigger and execution.
   - `ABORTED: Completion window exceeded` — large resource; increase
     `CompletionWindowMinutes` or use parallel backup.
   - `EXPIRED: Recovery point expired` — retention window passed
     before the backup completed.
3. CloudTrail: `StartBackupJob`, `BackupJobCompleted` events to
   correlate with the IAM role snapshot.
4. Remediation: fix the IAM role / increase windows / snapshot
   offline; re-run `start-backup-job` with `--idempotency-token`.

### Restore job failed

1. `describe-restore-job --restore-job-id <id>` — capture `Status`,
   `StatusMessage`, `CreatedResourceArn`.
2. Common failures:
   - `FAILED: Invalid metadata` — `--metadata` missing required
     fields (SubnetId for EC2, NewDBInstanceIdentifier for RDS).
   - `FAILED: Insufficient capacity` — destination subnet/AZ lacks
     capacity for the restore.
   - `FAILED: KMS key inaccessible` — destination region KMS key
     policy blocks `backup:Decrypt`.
3. Re-attempt with corrected metadata via `start-restore-job` with a
   new `--idempotency-token`.

### Vault lock cannot be removed

1. `describe-backup-vault --backup-vault-name <vault>` — capture
   `VaultLock.LockState`, `Mode`, `ChangeableForDays`.
2. If `Mode: COMPLIANCE` and `ChangeableForDays: 0`, the lock is
   permanent. Surface to operator; cannot be removed.
3. If `Mode: GOVERNANCE`, the lock can be removed by a principal with
   `backup:DeleteBackupVaultLockConfiguration`.

