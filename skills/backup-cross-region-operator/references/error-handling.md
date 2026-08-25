# Error Handling — Backup Cross-Region Operator

## Diagnostic flows

### Cross-region copy job stuck or failed

1. `describe-copy-job --copy-job-id <id>` — capture `State`,
   `StatusMessage`, `BackupSizeInBytes`, `SourceRecoveryPointArn`.
2. Common failures:
   - `FAILED: IAM role not authorized` — source role lacks
     `backup:StartCopyJob` or `backup:CopyIntoBackupVault`.
   - `FAILED: Destination vault not found` — vault deleted or
     wrong region.
   - `FAILED: KMS key access denied` — source KMS lacks
     `kms:Decrypt`, or destination KMS lacks `kms:GenerateDataKey`.
   - `RUNNING > 6h` — large snapshot; check EC2 copy bandwidth.
3. CloudTrail: `StartCopyJob`, `CopyJobCompleted` events.
4. Remediation: fix IAM/KMS, re-run with `--idempotency-token`.

### Cross-region restore failed

1. `describe-restore-job --restore-job-id <id>` — capture `Status`,
   `StatusMessage`, `CreatedResourceArn`.
2. Common failures:
   - `FAILED: Invalid metadata` — `--metadata` missing
     destination-region-specific fields (SubnetId, SecurityGroupIds
     in destination region).
   - `FAILED: Insufficient capacity` — destination subnet lacks
     capacity.
   - `FAILED: KMS key inaccessible` — destination-region KMS policy
     blocks `backup:Decrypt`.
3. Re-attempt with corrected metadata in the destination region.

### Cross-account copy returns `InvalidParameterValueException`

1. `organizations describe-effective-policy --policy-type
   BACKUP_POLICY` — verify cross-account enabled.
2. `describe-backup-vault --backup-vault-name <destination>` —
   verify vault exists and access policy grants
   `backup:CopyIntoBackupVault` to source.
3. If accounts NOT in same org, cross-account is unsupported. Use
   same-org accounts or re-archive to a same-account destination
   region.
