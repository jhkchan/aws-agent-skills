# Diagnostic Commands (load on demand) — DynamoDB Backup Restore Operator

Live-account pre-flight checks and pre-remediation safety checks, moved verbatim from SKILL.md.


---

## Live-account pre-flight (skip if offline plan audit) (moved from SKILL.md)

1. `aws dynamodb describe-table --table-name <name>` — confirm
   `TableStatus: ACTIVE`. Capture `BillingModeSummary`,
   `ProvisionedThroughput`, `TableSizeBytes`, `ItemCount`,
   `SSEDescription`, `GlobalSecondaryIndexes`, `LocalSecondaryIndexes`,
   `DeletionProtectionEnabled`, `StreamSpecification`.
2. `aws dynamodb describe-continuous-backups --table-name <name>` —
   capture `ContinuousBackupsStatus` and
   `PointInTimeRecoveryStatus`. `EarliestRestorableDateTime` and
   `LatestRestorableDateTime` define the PITR window (up to 35 days).
3. `aws dynamodb list-backups --table-name <name>` — list available
   backups (filter `--backup-type USER` for on-demand only).
4. `aws dynamodb describe-backup --backup-arn <arn>` — verify a specific
   backup is `AVAILABLE` before restore.
5. `aws application-autoscaling describe-scaling-policies
   --service-namespace dynamodb --resource-ids table/<name>` — capture
   autoscaling policies that must be re-registered on the restored
   table.
6. `aws backup list-protected-resources --resource-type DynamoDB` —
   check whether AWS Backup is also protecting this table.
7. `aws dynamodb describe-time-to-live --table-name <name>` — capture
   TTL config to re-apply on the restored table.
8. `aws kms describe-key --key-id <cmk-arn>` — verify CMK access for
   encrypted-table restore (`kms:Decrypt`, `kms:GenerateDataKey`,
   `kms:CreateGrant`).

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)


- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-backup`, `update-continuous-backups`,
  `restore-table-from-backup`, `restore-table-to-point-in-time`,
  `export-table-to-point-in-time`, `import-table`, `delete-backup`,
  `delete-table`, `aws backup start-restore-job`), emit:
  `CONFIRM: About to <operation> on <target> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.

- **Capture pre-state for rollback.** Before restore:
  `aws dynamodb describe-table --table-name <name> --output json >
  /tmp/<name>-pre-$(date +%s).json`. DynamoDB table state is not
  versioned.

- **Verify PITR BEFORE PITR restore.**
  `PointInTimeRecoveryStatus: ENABLED` AND
  `LatestRestorableDateTime >= --restore-date-time >=
  EarliestRestorableDateTime`.

- **Verify backup BEFORE snapshot restore.** `describe-backup
  --backup-arn <arn>` returns `BackupStatus: AVAILABLE`. CREATING →
  poll until AVAILABLE.

- **Verify CMK access for encrypted restores.** Cross-account restore
  requires source KMS key policy grant. Cross-region via AWS Backup
  requires destination-region KMS key.

- **Plan connection-string cutover BEFORE restore completes.** Restore
  produces a new table name. Application config, IAM policies,
  Secrets Manager references, CloudWatch alarms must all be updated
  atomically with cutover.

- **Plan cleanup BEFORE creating temporary tables.** A verification
  restore creates a billable table. Tag it (`temp: true, delete-after:
  2026-08-16`) and schedule deletion after cutover.

- **Deletion protection.** Restored tables do NOT inherit
  `DeletionProtectionEnabled`. Enable it after verification:
  `aws dynamodb update-table --table-name <new> --deletion-protection-
  enabled`.