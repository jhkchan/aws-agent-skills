# Diagnostic and Pre-flight Commands — RDS Snapshot Operator


## Pre-flight: instance/cluster metadata gate — live-account commands

**Live-account pre-flight (skip if offline plan audit):**
1. `aws rds describe-db-instances --db-instance-identifier <id>` — confirm
   instance exists; capture `DBInstanceStatus`, `StorageType`, `AllocatedStorage`,
   `Encrypted`, `KmsKeyId`, `OptionGroupMemberships`, `DBSubnetGroup`,
   `VpcSecurityGroups`, `Engine`, `EngineVersion`, `MultiAZ`,
   `BackupRetentionPeriod`, `LatestRestorableTime`, `DeletionProtection`.
2. `aws rds describe-db-snapshots --db-instance-identifier <id>` — list
   existing manual snapshots for the instance.
3. `aws rds describe-db-engine-versions --engine <engine>` — confirm target
   engine version for restore compatibility (major version upgrades on
   restore are supported but option group changes may be required).
4. `aws kms describe-key --key-id <kms-id>` — confirm key `Enabled` and
   the policy allows the RDS service to `kms:CreateGrant` (for encrypted
   snapshot creation) and the target account has `kms:Decrypt` (for
   cross-account shared snapshots).
5. `aws rds describe-option-groups --option-group-name <og>` — confirm the
   option group is compatible with the target engine version and has the
   required options (TDE, SSL, etc.).
6. `aws iam get-role --role-name <export-role>` — for S3 export tasks,
   confirm the IAM role has the required trust policy
   (`service: export.rds.amazonaws.com`) and permissions
   (`s3:PutObject`, `kms:Decrypt` on the source snapshot key).

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-db-snapshot`, `copy-db-snapshot`, `delete-db-snapshot`,
  `restore-db-instance-to-point-in-time`, `restore-db-cluster-from-snapshot`,
  `start-export-task`, `modify-db-snapshot-attribute`, `modify-db-instance`,
  `delete-db-instance`), emit: `CONFIRM: About to <operation> on <target>
  in account <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.

- **Capture pre-state for rollback.** Before any restore or deletion:
  `aws rds describe-db-instances --db-instance-identifier <id> --output
  json > /tmp/<id>-pre-$(date +%s).json`. For snapshot deletions, capture
  `describe-db-snapshots` output including ARN and tags.

- **Verify KMS key for encrypted operations.** Cross-region copy requires
  a target-region key. Cross-account sharing requires a key policy grant.
  `aws kms describe-key --key-id <id>` to confirm `Enabled`.

- **Verify option group for restore.** Restored instances default to the
  DEFAULT option group. If the source used TDE, SSL, or custom options,
  specify the correct option group on the restore CLI.

- **Verify network topology for restore.** Restored instances default to
  the DEFAULT security group. Specify VPC security groups explicitly to
  ensure the restored instance is reachable from the application.

- **Prefer additive operations over destructive ones.** Creating a
  snapshot, copying, and restoring are additive. Deleting a snapshot is
  irreversible. Always confirm the snapshot is not compliance-hold before
  deletion.
