# Backup Vault Operator — expert-heuristic deep dives, Step-0 expert knowledge, recent AWS features

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

### Step 0: Expert knowledge — non-obvious AWS Backup behaviors (moved verbatim from SKILL.md)

- **Compliance mode is irreversible after `ChangeableForDays` expires.**
  The grace window is set when the lock is applied (max 3 days). During
  grace, the lock can be removed by the principal that created it;
  after grace, no one (including root) can remove the lock or shorten
  retention.
- **Governance mode is soft-bypassable.** Any principal with
  `backup:DeleteBackupVaultLockConfiguration` and
  `iam:CreatePolicy`/`AttachRolePolicy` can remove the lock. For
  regulatory compliance (CIS Benchmark 3.6, NIST 800-53 CP-9), use
  compliance mode.
- **Retention window applies to ALL recovery points in the vault.**
  The vault lock's `MinRetentionDays` and `MaxRetentionDays` constrain
  every recovery point in the vault. The backup plan's lifecycle moves
  recovery points to cold storage or deletes them; the vault lock sets
  the floor (MinRetentionDays) and ceiling (MaxRetentionDays).
- **Tag-based selections apply to future resources.** A selection with
  `Conditions: {"StringEquals": {"aws:ResourceTag/backup": "daily"}}`
  picks up any new resource tagged `backup=daily`. Resource-tag-based
  selection is the recommended pattern; resource-ARN lists are static.
- **Cross-region copy needs a destination vault + KMS.** The copy
  rule in the backup plan references a destination region; AWS Backup
  creates the recovery point in the destination region's default vault
  unless a `BackupVaultName` is specified.
- **Continuous backup (PITR) requires the underlying service to support
  it.** EC2 PITR requires `aws:ec2:enable-point-in-time-recovery` on
  the instance. RDS PITR requires `BackupPlan.AdvancedBackupSettings`
  with `BackupOptions: {"WindowsVSS": "enabled"}` for Windows instances.
- **Backup selection with no `Conditions` and no `ListOfTags` selects
  nothing.** The selection MUST include at least one of `ListOfTags`,
  `Resources`, or `Conditions`. Empty selection silently matches no
  resources.
- **Restore creates a new resource by default.** The original resource
  is NOT overwritten. For RDS, the restore creates a new DB instance
  with a new endpoint; for EC2, a new instance with a new IP (unless
  the restore specifies the original private IP and that IP is
  available).
- **`StartRestoreJob` requires `Metadata` for resource-type-specific
  parameters.** EC2 restore needs `InstanceId`, `SubnetId`,
  `SecurityGroupIds`, `InstanceType`. RDS restore needs
  `NewDBInstanceIdentifier`. Wrong metadata = validation error or
  silent wrong configuration.
- **Backup Vault Lock applies to the vault, NOT to the plan.** Two
  plans writing to the same locked vault share the retention window.
  Cannot have one plan with 30-day retention and another with 7-day
  retention to the same locked vault — MinRetentionDays wins.
- **`Backup Search` (2025) searches across recovery points without
  restoring.** Use `backup search:SearchResource` (or the console
  Backup Search) to find files/items within EBS snapshots, S3 backups,
  and EFS backups without launching a restore job.
- **FSx backups are volume-level.** AWS Backup supports FSx for
  Windows File Server, Lustre, OpenZFS, and NetApp ONTAP. Each
  filesystem type has different restore semantics (volume-level vs
  file-level).
- **Cold storage transition (GLACIER / DEEP_ARCHIVE) is one-way for
  recovery speed.** Restore from GLACIER is 3-5 hours; from DEEP
  ARCHIVE is 12+ hours. Plan the lifecycle transition carefully —
  regulatory archives go to DEEP ARCHIVE, operational recovery stays
  in WARM.

---

## Recent AWS features (2024-2026) (moved verbatim from SKILL.md)

- **AWS Backup for Amazon FSx** (2025): backup and restore for FSx
  for Lustre, OpenZFS, and NetApp ONTAP with volume-level granularity.
- **AWS Backup Search** (2025): search across recovery points for
  files (EFS, S3) and items (DynamoDB, RDS) without launching a
  restore job; supports item-level restore from search results.
- **Continuous backups for EC2** (2024): point-in-time recovery for
  EC2 instances within a 35-day window; the backup plan rule must set
  `ContinuousBackup: true`.
- **AWS Backup support for Amazon S3** (2024): continuous backup with
  PITR for S3 objects; versioning and Object Lock requirements.
- **Backup Vault Lock grace window refinement**: max 3 days
  `ChangeableForDays`; clarified that governance mode does NOT meet
  regulatory compliance.
- **Cross-account backup** (2023, refined 2025): backup and restore
  across AWS accounts via AWS Organizations; requires
  `backup:CrossAccountBackupRole` delegation.
- **AWS Backup for Amazon Timestream, Amazon Neptune, and Amazon
  MQ** (2024): expanded service coverage.

