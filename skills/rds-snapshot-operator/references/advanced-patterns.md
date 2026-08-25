# Advanced Patterns — RDS Snapshot Operator


## Step 0: Expert knowledge — non-obvious RDS snapshot behaviors

These behaviors are easy to misjudge without operational RDS experience.
Each changes a plan if ignored:

- **Automated backup retention defines the PITR window.** Setting
  `BackupRetentionPeriod: 7` means RDS retains 7 days of transaction logs
  (5-minute snapshots + continuous logs). PITR can restore to any point
  within that window. Setting retention to 0 disables automated backups
  entirely and deletes all existing automated backups — PITR is lost. When
  increasing retention from 1 to 35, RDS does NOT backfill logs for the
  new period; the extended window starts from the change time forward.

- **Manual snapshots persist beyond instance deletion.** This is the most
  important RDS backup behavior. Deleting an RDS instance with
  `--skip-final-snapshot` also deletes automated backups. Manual snapshots
  (`create-db-snapshot`) are independent objects that survive instance
  deletion. For DR and compliance, always create a manual snapshot before
  deleting an instance, even if `DeletionProtection: true` is set.

- **Aurora clone from snapshot is instant (copy-on-write).** Aurora's
  distributed storage layer supports clone-on-write: a new cluster from a
  snapshot takes seconds regardless of data size. The clone shares storage
  with the source snapshot at the page level; writes allocate new pages.
  This is fundamentally different from RDS (non-Aurora) restore, which
  copies the entire backup to new EBS volumes.

- **PITR granularity is 5 minutes for RDS, sub-second for Aurora.** RDS
  records transaction logs every 5 minutes; `LatestRestorableTime` shows
  the most recent restorable point. Aurora's continuous backup stream
  supports second-level granularity. When a user requests "restore to
  2:47:32 PM," Aurora can honor the exact second; RDS rounds to the
  nearest 5-minute boundary.

- **Cross-region snapshot copy re-encrypts with a target-region KMS key.**
  You cannot copy an encrypted snapshot to another region using the same
  KMS key — KMS keys are region-scoped. The copy operation must specify a
  KMS key in the target region. The source key must allow the target
  account to `kms:Decrypt` (for cross-account source snapshots).

- **Cross-account snapshot sharing requires `share-db-snapshot`.** Use
  `modify-db-snapshot-attribute --attribute-name restore --values-to-add
  <target-account-id>` to share a snapshot. The target account can then
  `copy-db-snapshot` or `restore-db-instance-from-db-snapshot`. For
  encrypted snapshots, the KMS key must also be shared via a key policy
  grant.

- **Restore always creates a NEW instance/cluster.** RDS restore does NOT
  overwrite the original instance. PITR restore creates a new instance
  with a new endpoint. The operator must update connection strings,
  security groups, and parameter groups. This is why the verdict is
  REVIEW_REQUIRED for restore operations — the post-restore cutover needs
  human attention.

- **Option groups do not carry over on restore.** The restored instance
  uses the DEFAULT option group unless `--option-group-name` is specified.
  If the source used TDE, SSL, or other options, the restored data is
  unreadable or inaccessible without the correct option group. Always
  specify the option group explicitly on restore.

- **Snapshot is incremental at the storage layer but billed at full
  allocated storage.** RDS snapshots are incremental (only changed blocks
  are stored), but manual snapshot billing is based on the FULL allocated
  storage of the source instance at snapshot time, NOT the incremental
  delta. A 1 TB instance costs $95/month for each manual snapshot
  regardless of how much data changed.

- **Aurora backtrack is NOT a snapshot restore.** Aurora backtrack rewinds
  the cluster in-place to a target time within the backtrack window (up to
  72 hours). It does NOT create a new cluster and does NOT require a
  snapshot. Use backtrack for rapid rollback of logical errors (e.g.,
  accidental DELETE). Use snapshot restore for DR or cross-region recovery.

- **Blue/Green deploy uses snapshots as safety net.** Before a Blue/Green
  deploy switch, create a manual snapshot of the source instance. If the
  green environment has issues post-switch, the snapshot enables a
  rollback path. The snapshot is the pre-deploy recovery point.

- **Snapshot export to S3 uses an async ExportTask.** `start-export-task`
  exports a snapshot to S3 in Parquet format. The task runs asynchronously
  (30-60 minutes for 100 GB). The IAM role needs `s3:PutObject` on the
  target bucket and `kms:Decrypt` on the source snapshot's KMS key. The
  export preserves table structure as Parquet columns.

- **Delete-old-snapshot lifecycle automation uses EventBridge + Lambda.**
  Create a Lambda function that lists manual snapshots older than N days
  and deletes them via `delete-db-snapshot`. Trigger via EventBridge
  schedule (e.g., `rate(1 day)`). Tag compliance-hold snapshots with
  `DoNotDelete: true` and have the Lambda skip them.

- **`--final-db-snapshot-identifier` on instance deletion is mandatory
  unless `--skip-final-snapshot`.** Deleting an instance without a final
  snapshot is irreversible — all data is lost. Always use
  `--final-db-snapshot-identifier` for production instances. The final
  snapshot is a manual snapshot that persists indefinitely.

- **Snapshot copy can be automated via AWS Backup or DLM.** For
  cross-region DR, Data Lifecycle Manager (DLM) or AWS Backup can automate
  snapshot creation and cross-region copy on a schedule. DLM policies
  target EBS-backed RDS instances; AWS Backup supports both RDS and
  Aurora.

- **`DeletionProtection` blocks instance deletion, NOT snapshot
  deletion.** You can delete a manual snapshot of a
  `DeletionProtection: true` instance. The protection prevents the
  INSTANCE from being deleted (and thus losing automated backups). Always
  set DeletionProtection on production instances to prevent accidental
  data loss.

## Recent AWS features (2024-2026)

- **Aurora clone from snapshot optimization (2024-2025):** Aurora's
  copy-on-write clone mechanism now supports cross-account clones within
  the same region. The source account shares the snapshot; the target
  account clones. Storage is shared at the page level.

- **Blue/Green Deployments GA (2024):** RDS Blue/Green Deployments create
  a staging environment that mirrors production. The switch is near-zero-
  downtime. Always create a pre-deploy snapshot as the rollback recovery
  point. The Blue/Green switch itself does not create snapshots.

- **RDS Snapshot Export to S3 with column-level filtering (2024-2025):**
  The `start-export-task` API now supports exporting specific tables or
  columns via the `ExportOnly` parameter (list of
  `database.schema.table` patterns). Useful for compliance exports that
  only need specific tables.

- **Automated backup retention up to 35 days (2024):** RDS
  `BackupRetentionPeriod` supports up to 35 days (previously 35 was the
  max for Aurora; RDS was 35). Aurora supports up to 35 days of PITR with
  continuous backup.

- **Aurora backtrack window up to 72 hours (2024-2025):** Aurora MySQL
  and PostgreSQL support backtrack windows up to 72 hours. Backtrack
  rewinds the cluster in-place without creating a new cluster. Use for
  rapid logical rollback (e.g., accidental DELETE/DROP).

- **AWS Backup integration with RDS (2024-2025):** AWS Backup now
  supports RDS cross-region copy and cross-account backup vaults. Use
  AWS Backup for centralized backup governance across RDS, Aurora, and
  other AWS services.

- **Snapshot export in columnar Parquet with compression (2025):** The
  export task now supports Snappy and ZSTD compression for Parquet
  output. ZSTD reduces output size by 30-50% compared to uncompressed
  Parquet.

- **RDS Storage Auto Scaling (2024-2025):** When Storage Auto Scaling is
  enabled, snapshots capture the current allocated storage (which may
  have auto-scaled beyond the original provisioning). Restores allocate
  the snapshot's storage size, not the original.

- **DLM cross-region copy with KMS re-encryption (2024):** Data Lifecycle
  Manager policies now support cross-region snapshot copy with automatic
  KMS re-encryption. Use DLM for automated DR snapshot pipelines without
  custom Lambda.

- **CloudWatch RUM for database performance monitoring (2025):** CloudWatch
  RUM integrates with RDS Performance Insights to correlate application
  requests with database query performance. Useful for post-restore
  validation to confirm the restored instance performs as expected.
