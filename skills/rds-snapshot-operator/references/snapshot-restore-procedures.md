# RDS Snapshot & Restore Procedures Reference

Load this reference when planning or executing snapshot creation,
restore, copy, or lifecycle operations. The procedures below cover the
canonical CLI sequences for each operation type, with pre-checks and
verification steps.

## Decision tree — which snapshot operation

| Scenario | Use | Why |
|---|---|---|
| Pre-upgrade, pre-maintenance safety snapshot | **create-snapshot** | Manual snapshot persists beyond instance deletion; recovery point |
| DR copy to another region | **copy-snapshot** | Cross-region copy with KMS re-encryption for DR |
| Recover from accidental data change | **restore-pitr** | PITR to 5-minute granularity (RDS) or second-level (Aurora) |
| Recover from instance deletion | **restore-from-snapshot** | Manual snapshot is the only recovery path after deletion |
| Quick dev/test copy of production data | **Aurora clone** | Instant copy-on-write clone (Aurora only) |
| Rapid logical rollback (Aurora) | **Aurora backtrack** | In-place rewind, no new cluster, within backtrack window |
| Compliance data extraction | **export-to-s3** | Export snapshot to S3 in Parquet format |
| Cross-account sharing | **share-snapshot** | Share via modify-db-snapshot-attribute |
| Old snapshot cleanup | **delete-snapshot** | Lifecycle cleanup, skip compliance-hold snapshots |
| Change backup window duration | **update-retention** | Modify BackupRetentionPeriod (1-35 days) |

## Procedure: create-snapshot

**Prerequisites:** Instance is `available`, no existing snapshot with
the target identifier.

```bash
# 1. Create the snapshot
aws rds create-db-snapshot \
  --db-instance-identifier <instance-id> \
  --db-snapshot-identifier <snapshot-id> \
  --tags Key=DoNotDelete,Value=true Key=Purpose,Value=pre-upgrade

# 2. Monitor status (creating -> available)
aws rds describe-db-snapshots \
  --db-snapshot-identifier <snapshot-id> \
  --query 'DBSnapshots[0].Status'

# 3. Verify snapshot properties
aws rds describe-db-snapshots \
  --db-snapshot-identifier <snapshot-id> \
  --query 'DBSnapshots[0].{Status:Status,Encrypted:Encrypted,Storage:AllocatedStorage,Engine:Engine}'
```

**Time estimate:** 2-5 min per 100 GB (RDS). Aurora cluster snapshots
are near-instant metadata operations.

## Procedure: copy-snapshot (cross-region)

**Prerequisites:** Source snapshot `available`, target-region KMS key
specified and enabled.

```bash
# 1. Copy with KMS re-encryption
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:<src-region>:<account>:snapshot:<snap-id> \
  --target-db-snapshot-identifier <target-snap-id> \
  --kms-key-id arn:aws:kms:<target-region>:<account>:key/<target-key-id> \
  --region <target-region> \
  --copy-tags

# 2. Monitor status in target region
aws rds describe-db-snapshots \
  --db-snapshot-identifier <target-snap-id> \
  --region <target-region> \
  --query 'DBSnapshots[0].Status'
```

**Time estimate:** 10-30 min per 100 GB cross-region (depends on
inter-region bandwidth).

## Procedure: restore-pitr

**Prerequisites:** BackupRetentionPeriod >= 1, target time within
[EarliestRestorableTime, LatestRestorableTime].

**IMPORTANT:** Restore creates a NEW instance. Specify option group,
security groups, and subnet group explicitly.

```bash
# 1. Verify restorable window
aws rds describe-db-instances \
  --db-instance-identifier <source-id> \
  --query 'DBInstances[0].{Earliest:EarliestRestorableTime,Latest:LatestRestorableTime,Retention:BackupRetentionPeriod}'

# 2. Restore to target time (RDS)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier <source-id> \
  --target-db-instance-identifier <target-id> \
  --restore-time 2026-08-05T14:35:00Z \
  --db-instance-class db.r6g.xlarge \
  --option-group-name <option-group> \
  --vpc-security-group-ids sg-xxxx \
  --db-subnet-group-name <subnet-group>

# 3. For Aurora cluster PITR
aws rds restore-db-cluster-to-point-in-time \
  --source-db-cluster-identifier <source-cluster> \
  --db-cluster-identifier <target-cluster> \
  --restore-to-time 2026-08-05T14:35:00Z \
  --db-subnet-group-name <subnet-group> \
  --vpc-security-group-ids sg-xxxx

# 4. Aurora: create instance in restored cluster
aws rds create-db-instance \
  --db-instance-identifier <target-cluster>-instance-1 \
  --db-instance-class db.r6g.xlarge \
  --engine aurora-mysql \
  --db-cluster-identifier <target-cluster>

# 5. Monitor restore
aws rds describe-db-instances \
  --db-instance-identifier <target-id> \
  --query 'DBInstances[0].DBInstanceStatus'
```

**Time estimate:** 20-45 min for RDS (proportional to allocated
storage). Aurora is faster due to distributed storage.

## Procedure: Aurora clone from snapshot

```bash
# 1. Restore cluster from snapshot (near-instant for Aurora)
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier <clone-cluster> \
  --snapshot-identifier <snapshot-id> \
  --engine aurora-mysql \
  --db-subnet-group-name <subnet-group> \
  --vpc-security-group-ids sg-xxxx

# 2. Create primary instance in the clone
aws rds create-db-instance \
  --db-instance-identifier <clone-cluster>-instance-1 \
  --db-instance-class db.r6g.xlarge \
  --engine aurora-mysql \
  --db-cluster-identifier <clone-cluster>
```

**Key insight:** Aurora clones share storage with the source snapshot
at the page level (copy-on-write). Writes allocate new pages; reads of
unmodified pages are served from shared storage. Clone creation is
seconds regardless of data size.

## Procedure: share-snapshot (cross-account)

```bash
# 1. Share the snapshot with the target account
aws rds modify-db-snapshot-attribute \
  --db-snapshot-identifier <snapshot-id> \
  --attribute-name restore \
  --values-to-add <target-account-id>

# 2. For encrypted snapshots: share the KMS key
# Add the target account to the key policy:
# {
#   "Sid": "Allow target account to use the key",
#   "Effect": "Allow",
#   "Principal": {"AWS": "arn:aws:iam::<target-account>:root"},
#   "Action": ["kms:Decrypt", "kms:CreateGrant"],
#   "Resource": "*"
# }

# 3. Target account: copy or restore the shared snapshot
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:<region>:<source-account>:snapshot:<snap-id> \
  --target-db-snapshot-identifier <local-snap-id> \
  --kms-key-id <target-account-kms-key>
```

## Procedure: export-snapshot to S3

```bash
# 1. Create IAM role for the export
# Trust policy must include service: export.rds.amazonaws.com
# Permissions: s3:PutObject on the target bucket, kms:Decrypt on source key

# 2. Start the export task
aws rds start-export-task \
  --export-task-identifier <task-id> \
  --source-arn arn:aws:rds:<region>:<account>:snapshot:<snap-id> \
  --s3-bucket-name <bucket> \
  --s3-prefix rds-exports/ \
  --iam-role-arn arn:aws:iam::<account>:role/rds-export-role \
  --kms-key-id arn:aws:kms:<region>:<account>:key/<export-key-id> \
  --export-only database.schema.table1 database.schema.table2

# 3. Monitor export status
aws rds describe-export-tasks \
  --export-task-identifier <task-id> \
  --query 'ExportTasks[0].{Status:Status,PercentProgress:PercentProgress,TotalFullSize:TotalExtractedDataInGB}'
```

**Time estimate:** 30-60 min per 100 GB. Output format: Parquet with
Snappy compression. Cost: $0.012/GB exported.

## Procedure: delete-snapshot (lifecycle)

```bash
# 1. List manual snapshots older than N days
aws rds describe-db-snapshots \
  --snapshot-type manual \
  --query "DBSnapshots[?SnapshotCreateTime<'2026-07-05'].[DBSnapshotIdentifier,SnapshotCreateTime,AllocatedStorage]"

# 2. Check for compliance-hold tags before deletion
aws rds list-tags-for-resource \
  --resource-name arn:aws:rds:<region>:<account>:snapshot:<snap-id> \
  --query 'TagList[?Key==`DoNotDelete`]'

# 3. Delete (irreversible)
aws rds delete-db-snapshot \
  --db-snapshot-identifier <snap-id>
```

## Procedure: update-retention

```bash
# 1. Check current retention
aws rds describe-db-instances \
  --db-instance-identifier <id> \
  --query 'DBInstances[0].{Retention:BackupRetentionPeriod,Latest:LatestRestorableTime}'

# 2. Update retention (1-35 days)
aws rds modify-db-instance \
  --db-instance-identifier <id> \
  --backup-retention-period 14 \
  --apply-immediately

# NOTE: Increasing retention does NOT backfill historical logs.
# The extended window starts from the change time forward.
# Decreasing to 0 immediately deletes ALL automated backups.
```

## Aurora backtrack (in-place rewind)

```bash
# 1. Check backtrack window
aws rds describe-db-clusters \
  --db-cluster-identifier <cluster> \
  --query 'DBClusters[0].{BacktrackWindow:BacktrackWindow,LatestBacktrack:LatestBacktrackTime}'

# 2. Backtrack to target time (in-place, no new cluster)
aws rds backtrack-db-cluster \
  --db-cluster-identifier <cluster> \
  --backtrack-to 2026-08-05T14:35:00Z \
  --use-system-events true
```

**Key insight:** Backtrack rewinds the cluster in-place within the
backtrack window (up to 72 hours). No new cluster is created. Use for
rapid logical rollback (accidental DELETE/DROP). Use snapshot restore
for DR or cross-region recovery.
