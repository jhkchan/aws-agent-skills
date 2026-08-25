# RDS Backup Restore Operator — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

### Step 0: Expert knowledge — non-obvious RDS/Aurora behaviors (moved from SKILL.md)

These behaviors are easy to misjudge without operational RDS experience.
Each changes a plan if ignored:

- **Restore creates a NEW instance with a NEW endpoint.** Always. The original
  instance is unchanged. Operators must update application connection strings
  to the new endpoint. This is the single most common RDS restore surprise.

- **PITR restore uses the `LatestRestorableTime` from automated backups.**
  The recoverable window is `[SnapshotCreateTime, LatestRestorableTime]`,
  where `LatestRestorableTime` lags real-time by ~5 minutes (the transaction-
  log shipping cadence). You cannot restore to "right now" — the latest
  recoverable point is 5 minutes ago.

- **`BackupRetentionPeriod: 0` disables PITR entirely.** Setting retention to
  0 stops automated backups AND transaction-log shipping. The only recovery
  option becomes manual snapshots. This is irreversible for the existing
  window — once disabled, the unbacked-up period cannot be recovered.

- **Aurora Backtrack is in-place and fast but bounded.** The `BacktrackWindow`
  (1-72 hours, configurable up to 7 days for Aurora MySQL) bounds how far back
  you can rewind. Backtrack does NOT create a new cluster — it reverses DML
  in-place. Operations NOT supported by Backtrack: DDL rollback is limited;
  Backtrack cannot undo some CREATE/DROP operations. Test before relying on
  Backtrack for DDL rollback.

- **Aurora Fast Database Clone is instant but storage-billed.** An Aurora
  clone shares storage with the source (copy-on-write), so the clone is
  instant regardless of data size. However, as the clone writes divergent
  pages, storage grows — a long-lived clone can double the storage bill.

- **Cross-region snapshot copy requires destination-region KMS for encrypted
  snapshots.** The source-region KMS key cannot decrypt in the destination
  region. The copy operation re-encrypts with a destination-region KMS key
  that you specify via `--kms-key-id`.

- **Cross-account snapshot share requires both snapshot share AND KMS key
  policy grant.** Sharing an encrypted snapshot via
  `modify-db-snapshot-attribute` is necessary but NOT sufficient — the
  source account's KMS key policy must allow the recipient account to
  `kms:Decrypt` and `kms:CreateGrant`. Without the KMS side, the recipient
  can describe the snapshot but cannot restore from it.

- **Manual snapshots persist after the instance is deleted.** Deleting an
  RDS instance with `SkipFinalSnapshot: false` (or true) does NOT delete
  manual snapshots. Manual snapshots persist indefinitely until explicitly
  deleted — they are the long-term recovery source. Automated backups
  (retention-managed) ARE deleted with the instance.

- **Restoring from a snapshot does NOT inherit tags by default.** Use
  `--copy-tags-to-snapshot` on the source instance, or pass tags explicitly
  on `restore-db-instance-from-db-snapshot --tags`. Tag drift on restored
  instances is a common cost-allocation gap.

- **Option groups and parameter groups must match the engine major version.**
  A snapshot from MySQL 8.0 cannot be restored with the MySQL 5.7 option
  group. Aurora cluster parameter groups differ from instance parameter
  groups — surface both.

- **Aurora Backtrack performance scales with the change volume, not cluster
  size.** Backtracking 1 hour of high-write traffic may take longer than
  backtracking 24 hours of low-write traffic. Aurora Backtrack charges per
  backtrack record ($0.012 per backtrack change in us-east-1).

- **`modify-db-instance --backup-retention-period` triggers a backup.**
  Increasing retention from 0 to 7 immediately starts an automated backup
  run; the instance enters `modifying` then `backing-up` state. The PITR
  window only becomes available after the first successful automated backup
  completes (can take 30+ minutes for large instances).

- **Multi-AZ failover does NOT affect backup continuity.** Backups run from
  the standby in a Multi-AZ deployment; a primary failover does not interrupt
  the backup window. Single-AZ instances pause I/O during the backup window.

- **`RestoreTime` must be within the retention window.** Specifying a
  `--restore-time` outside `[SnapshotCreateTime, LatestRestorableTime]`
  returns `InvalidParameterValue`. Always check `LatestRestorableTime` via
  `describe-db-instances` before specifying a restore time.

- **Aurora continuous backup is always-on (no `BackupRetentionPeriod: 0`).**
  Aurora clusters require retention >= 1; PITR is always available. The
  Aurora `BackupRetentionPeriod` controls the continuous-backup window
  (1-35 days) AND the automated-snapshot retention.

- **S3 export requires the snapshot to be in `available` state and the
  export role to trust `rds.amazonaws.com`.** The `--role-arn` and
  `--s3-bucket-name` must be in the same account; the role needs
  `s3:PutObject`, `s3:ListBucket`, `kms:Decrypt` on the export bucket.

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **Aurora Backtrack extended window (2024-2025):** Aurora MySQL now supports
  BacktrackWindow up to 72 hours (previously 24 hours). Configure via
  `modify-db-cluster --backtrack-window`. The backtrack cost per change
  remains ~$0.012/change (us-east-1). Aurora PostgreSQL still does NOT
  support Backtrack as of 2026.

- **RDS Multi-AZ Cluster Standby Backups (2024):** Multi-AZ cluster
  deployments (2 standbys) now run automated backups from a standby,
  eliminating the brief I/O pause during backup windows. Operators should
  verify their Multi-AZ deployment type (single-AZ, Multi-AZ instance, or
  Multi-AZ cluster) to understand backup behavior.

- **Aurora Fast Database Clone GA:** Instant clone of Aurora clusters via
  copy-on-write storage. Operators should verify clone cleanup lifecycle —
  long-lived clones double the storage bill as pages diverge.

- **S3 Export with column-level filtering (2024-2025):** `start-export-task`
  now supports `--export-only` for selective table/column export, reducing
  export time and S3 cost. Pair with Parquet output for analytics-ready
  exports.

- **RDS Blue/Green Deployments GA (2024):** Blue/Green deployments create a
  staging environment (Green) that mirrors production (Blue) for zero-
  downtime switches. Operators should use Blue/Green for schema changes
  instead of in-place restores — Backtrack and PITR remain the recovery
  path for failed Blue/Green switches.

- **Aurora Serverless v2 scaling improvements (2024-2025):** Serverless v2
  now supports backup configuration identical to provisioned Aurora. PITR
  and Backtrack are fully supported on Serverless v2 clusters.

- **Cross-account snapshot automation via AWS Backup (2025):** AWS Backup
  now supports cross-account snapshot management for RDS, simplifying the
  KMS key policy coordination that previously made cross-account restore
  error-prone.

