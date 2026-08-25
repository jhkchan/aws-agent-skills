# RDS Backup Restore Operator — diagnostic commands (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Live-account pre-flight commands (moved from SKILL.md)

1. `aws rds describe-db-instances --db-instance-identifier <id>` — confirm
   `DBInstanceStatus: available`. Capture `DBInstanceClass`, `Engine`,
   `EngineVersion`, `AllocatedStorage`, `MultiAZ`, `StorageEncrypted`,
   `KmsKeyId`, `DBSubnetGroup`, `VpcSecurityGroups`, `OptionGroupMemberships`,
   `DBParameterGroups`.
2. `aws rds describe-db-snapshots --db-instance-identifier <id>` — list
   available manual + automated snapshots.
3. `aws rds describe-db-engine-versions --engine <engine>` — verify the
   engine version is available in the target region.
4. `aws rds describe-orderable-db-instance-options --engine <engine>
   --engine-version <version>` — verify the instance class is available in
   the target AZ.
5. `aws ec2 describe-vpcs --vpc-ids <vpc-id>` — verify the target VPC exists.
6. `aws ec2 describe-subnets --filters Name=vpc-id,Values=<vpc-id>` — verify
   the subnet group's subnets exist.
7. `aws kms describe-key --key-id <kms-key-id>` — verify KMS key access;
   `kms:Decrypt` and `kms:CreateGrant` are required for encrypted restores.
8. `aws rds describe-db-clusters --db-cluster-identifier <id>` — for Aurora,
   capture cluster-level config (backtrack window, copy-tags, global-cluster
   membership).

## Pre-flight safety checks (run before any remediation CLI) (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-db-snapshot`, `restore-db-instance-*`, `backtrack-db-cluster`,
  `start-export-task`, `start-import-from-s3`, `delete-db-instance`), emit:
  `CONFIRM: About to <operation> on <target> in account <account> region
  <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT execute
  until the operator confirms.

- **Capture pre-state for rollback.** Before restore or backtrack:
  `aws rds describe-db-instances --db-instance-identifier <id> --output json
  > /tmp/<id>-pre-$(date +%s).json`. RDS instance state is not versioned.

- **Verify target resources BEFORE executing restore.** Subnet group,
  security group, option group, parameter group, KMS key — all must exist
  in the target VPC/region. A restore with a missing resource fails after
  snapshot download, wasting 30+ minutes.

- **Verify retention BEFORE PITR.** `BackupRetentionPeriod > 0` AND
  `LatestRestorableTime >= --restore-time >= EarliestRestorableTime`. The
  window is `[SnapshotCreateTime, LatestRestorableTime]` with ~5 min lag.

- **Verify BacktrackWindow BEFORE Aurora backtrack.** Engine must be
  `aurora-mysql`; `BacktrackWindow > 0`; target timestamp within the
  window. Aurora PostgreSQL does NOT support backtrack.

- **Verify KMS key access for encrypted restores.** Cross-account restore
  requires both snapshot share AND KMS key policy grant. Cross-region
  restore requires a destination-region KMS key.

- **Plan connection-string cutover BEFORE restore completes.** Restore
  produces a new endpoint. Application connection strings, DNS aliases,
  and secrets (Secrets Manager, Parameter Store) must be updated
  atomically with the cutover.

- **Plan cleanup BEFORE creating temporary instances.** A verification
  restore creates a billable instance. Tag it (`temp: true, delete-after:
  2026-08-14`) and schedule deletion after cutover.

- **Snapshot identifier uniqueness.** Before `create-db-snapshot`, verify
  `--db-snapshot-identifier` does NOT already exist. RDS rejects duplicate
  identifiers with `DBSnapshotAlreadyExists`.

- **Deletion protection.** Restored instances inherit `--deletion-protection`
  setting. If you create a restore WITHOUT deletion protection, plan to set
  it after verification:
  `aws rds modify-db-instance --db-instance-identifier <new> \
  --deletion-protection --apply-immediately`.

