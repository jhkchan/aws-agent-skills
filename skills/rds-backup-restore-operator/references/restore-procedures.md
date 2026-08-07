# RDS/Aurora Restore Procedures Reference

Load this reference when planning or executing any restore operation. The
procedures below are the canonical sequences for each restore archetype,
with pre-checks, command sequence, post-verification, and rollback notes.

## Decision tree — which restore archetype

| Scenario | Use | Why |
|---|---|---|
| Bad migration / bad DML, original instance intact | **PITR restore** | Rewind to 5 min before the change; new instance, original preserved |
| Instance deleted, snapshot exists | **Snapshot restore** | Reconstitute from a point-in-time snapshot |
| Aurora MySQL bad DML, want in-place rewind | **Aurora Backtrack** | Seconds, no new endpoint, in-place |
| Aurora MySQL/PostgreSQL, want a dev copy fast | **Fast Database Clone** | Instant, copy-on-write storage |
| Cross-region disaster recovery | **Snapshot cross-region copy + restore** | Restore from a DR-region snapshot |
| Cross-account data sharing | **Snapshot share + KMS grant + restore** | Recipient restores in their account |
| Compliance / audit data extraction | **S3 export (Parquet)** | Snapshot to S3 for analytics |
| Bulk load into Aurora MySQL | **S3 import** | Load S3 data into Aurora MySQL |

## PITR restore procedure

**When to use:** recover from bad DML/DDL on a live instance where the
original is still running.

**Pre-checks:**
1. `BackupRetentionPeriod > 0` on the source.
2. `LatestRestorableTime` >= `--restore-time` >= `EarliestRestorableTime`.
3. `DBInstanceStatus: available` on the source.
4. Target `--db-instance-identifier` does NOT exist.
5. Target DB subnet group, security group, option group, parameter group,
   KMS key all exist and match engine+version.

**Command sequence:**
```bash
# 1. Capture pre-state
aws rds describe-db-instances --db-instance-identifier <source> \
  --output json > /tmp/<source>-pre-$(date +%s).json

# 2. Identify the latest restorable time (informational)
aws rds describe-db-instances --db-instance-identifier <source> \
  --query 'DBInstances[0].LatestRestorableTime' --output text

# 3. Execute (NEW instance, NEW endpoint; original unchanged)
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier <source> \
  --target-db-instance-identifier <target> \
  --restore-time 2026-08-07T10:00:00Z \
  --db-subnet-group-name <subnet-group> \
  --vpc-security-group-ids <sg-id> \
  --option-group-name <option-group> \
  --db-parameter-group-name <param-group> \
  --no-deletion-protection \
  --tags Key=restored-from,Value=<source> Key=reason,Value=bad-migration

# 4. Wait for available
aws rds wait db-instance-available --db-instance-identifier <target>

# 5. Get the new endpoint
aws rds describe-db-instances --db-instance-identifier <target> \
  --query 'DBInstances[0].Endpoint.Address' --output text
```

**Post-verification:**
- `describe-db-instances` shows `DBInstanceStatus: available`.
- `mysql -h <new-endpoint> -u <user> -p` connects successfully.
- Row count on a known table matches the expected point-in-time state.
- A sentinel row written at the restore target time is present (or absent
  if restoring to before it was written).

**Rollback:** Delete the restored instance:
```bash
aws rds delete-db-instance --db-instance-identifier <target> \
  --skip-final-snapshot
```
The original source is untouched — there is no in-place rollback needed.

**Common failure modes:**
- `InvalidParameterValue: RestoreTime is outside the window` — verify
  `LatestRestorableTime` and re-issue.
- `DBSubnetGroupNotFoundFault` — the subnet group name is wrong or in a
  different region.
- `KMSKeyNotAccessibleFault` — the KMS key policy does not grant the
  caller `kms:Decrypt` and `kms:CreateGrant`.

## Snapshot restore procedure

**When to use:** recover from a deleted instance (manual snapshot is the
only source) or restore to a known snapshot point.

**Pre-checks:**
1. Snapshot exists and is `available`.
2. Engine + engine-version of the snapshot is available in the target region.
3. Instance class compatible with the snapshot is available in the target AZ.
4. Target `--db-instance-identifier` does NOT exist.
5. DB subnet group, security group, option group, parameter group, KMS key
   all exist.

**Command sequence:**
```bash
# 1. Capture pre-state (for audit)
aws rds describe-db-snapshots --db-snapshot-identifier <snapshot> \
  --output json > /tmp/<snapshot>-pre-$(date +%s).json

# 2. Execute (NEW instance, NEW endpoint)
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier <target> \
  --db-snapshot-identifier <snapshot> \
  --db-instance-class db.r6g.large \
  --db-subnet-group-name <subnet-group> \
  --vpc-security-group-ids <sg-id> \
  --option-group-name <option-group> \
  --db-parameter-group-name <param-group> \
  --no-deletion-protection \
  --copy-tags-to-snapshot \
  --tags Key=restored-from-snapshot,Value=<snapshot>

# 3. Wait for available
aws rds wait db-instance-available --db-instance-identifier <target>

# 4. Get the new endpoint
aws rds describe-db-instances --db-instance-identifier <target> \
  --query 'DBInstances[0].Endpoint.Address' --output text
```

**Post-verification:** Same as PITR plus verify the snapshot's tagged
metadata matches the intended restore point.

**Rollback:** Same as PITR — delete the restored instance.

## Aurora Backtrack procedure

**When to use:** Aurora MySQL cluster, rewind bad DML in seconds without
creating a new cluster. In-place.

**Pre-checks:**
1. Engine is `aurora-mysql` (Aurora PostgreSQL does NOT support Backtrack).
2. `BacktrackWindow > 0` on the cluster.
3. `--backtrack-to-timestamp` is within `[now - BacktrackWindow, now]`.
4. `DBClusterStatus: available`.
5. Cluster is NOT the writer in a Global Database.
6. No existing backtrack in progress.

**Command sequence:**
```bash
# 1. Capture pre-state (cluster config + sentinel row for verification)
aws rds describe-db-clusters --db-cluster-identifier <cluster> \
  --output json > /tmp/<cluster>-pre-$(date +%s).json

# 2. Execute (IN-PLACE; endpoint unchanged)
aws rds backtrack-db-cluster \
  --db-cluster-identifier <cluster> \
  --backtrack-to-timestamp 2026-08-07T09:00:00Z

# 3. Wait for cluster available
aws rds wait db-cluster-available --db-cluster-identifier <cluster>
```

**Post-verification:**
- `describe-db-clusters` shows `DBClusterStatus: available`.
- Sentinel row state matches the target timestamp (present if written
  before the timestamp, absent if written after).
- CloudTrail shows the `BacktrackDBCluster` event with the target timestamp.

**Rollback:** Aurora supports forward backtrack — re-forward to the
pre-backtrack state. Or, if the backtrack was wrong, use PITR to a point
before the backtrack.

**Common failure modes:**
- `InvalidParameterCombination: BacktrackToTimestamp is outside window` —
  the target is older than `BacktrackWindow`. Use PITR instead.
- `Engine is aurora-postgresql` — Backtrack not supported; use PITR or
  fast clone.
- `InvalidDBClusterStateFault` — a backtrack is already in progress or
  the cluster is in a Global Database writer role.

## Aurora Fast Database Clone procedure

**When to use:** create an instant dev/test copy of an Aurora cluster.

**Pre-checks:**
1. Source cluster is `available`.
2. Target cluster identifier does NOT exist.
3. KMS key (if encrypted) is accessible.

**Command sequence:**
```bash
aws rds restore-db-cluster-to-point-in-time \
  --db-cluster-identifier <target-cluster> \
  --source-db-cluster-identifier <source-cluster> \
  --restore-type copy-on-write \
  --use-latest-restorable-time \
  --db-subnet-group-name <subnet-group> \
  --vpc-security-group-ids <sg-id>

# Create the primary instance in the cloned cluster
aws rds create-db-instance \
  --db-instance-identifier <target-instance> \
  --db-cluster-identifier <target-cluster> \
  --engine aurora-mysql \
  --db-instance-class db.r6g.large
```

**Post-verification:**
- `describe-db-clusters` shows the new cluster `available`.
- Cluster endpoint resolves and connects.
- Storage is shared (copy-on-write); new writes create new pages.

**Cleanup:** Fast clones share storage but diverge over time. Tag the clone
with `cleanup-after: <date>` and delete it promptly:
```bash
aws rds delete-db-cluster --db-cluster-identifier <target-cluster> \
  --skip-final-snapshot
```

## Cross-region snapshot copy + restore

**When to use:** disaster recovery, migration between regions, or
latency reduction.

**Pre-checks:**
1. Source snapshot is `available`.
2. Source and destination regions are different.
3. Destination-region KMS key exists (for encrypted snapshots).
4. Service quota for snapshot copies is not exceeded.

**Command sequence:**
```bash
# 1. Copy snapshot cross-region (encrypted snapshots need --kms-key-id)
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:111111111111:snapshot:<snap> \
  --target-db-snapshot-identifier <snap-dr> \
  --source-region us-east-1 \
  --kms-key-id arn:aws:kms:eu-west-1:111111111111:key/<dr-key> \
  --region eu-west-1

# 2. Wait for the copy
aws rds wait db-snapshot-available --db-snapshot-identifier <snap-dr> --region eu-west-1

# 3. Restore in the destination region
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier <target> \
  --db-snapshot-identifier <snap-dr> \
  --db-subnet-group-name <dr-subnet-group> \
  --vpc-security-group-ids <dr-sg> \
  --region eu-west-1
```

**Cost:** Cross-region copy bills $0.02/GB transfer + destination-region
storage ($0.095/GB-month for gp storage). A 1 TB snapshot copied to 3 DR
regions is $60 transfer + 3 TB-month ongoing.

## Cross-account snapshot share + restore

**When to use:** share data with another AWS account (analytics partner,
acquired subsidiary, regulated isolation).

**Pre-checks:**
1. Source snapshot is `available` and encrypted.
2. Source KMS key policy grants the recipient account
   `kms:Decrypt` + `kms:CreateGrant`.
3. Recipient account has an instance class, subnet group, security group,
   option group, parameter group, and KMS key ready.

**Command sequence:**
```bash
# In the source account: share the snapshot
aws rds modify-db-snapshot-attribute \
  --db-snapshot-identifier <snapshot> \
  --attribute-name restore \
  --values-to-add 222222222222

# In the recipient account: describe the shared snapshot
aws rds describe-db-snapshots \
  --include-shared --db-snapshot-identifier arn:aws:rds:us-east-1:111111111111:snapshot:<snap>

# In the recipient account: copy the shared snapshot (re-encrypt with own KMS)
aws rds copy-db-snapshot \
  --source-db-snapshot-identifier arn:aws:rds:us-east-1:111111111111:snapshot:<snap> \
  --target-db-snapshot-identifier <local-copy> \
  --kms-key-id arn:aws:kms:us-east-1:222222222222:key/<recipient-key>

# In the recipient account: restore from the local copy
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier <target> \
  --db-snapshot-identifier <local-copy> \
  --db-subnet-group-name <recipient-subnet-group> \
  --vpc-security-group-ids <recipient-sg>
```

**Common failure mode:** `KMSKeyNotAccessibleFault` in the recipient
account — the source KMS key policy does not grant the recipient. Fix in
the source account:
```bash
aws kms put-key-policy --key-id <source-key> --policy-name default \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
       "Action": ["kms:Decrypt", "kms:CreateGrant", "kms:DescribeKey"],
       "Resource": "*"}
    ]
  }'
```

## S3 export procedure

**When to use:** extract snapshot data to S3 for analytics, ML training,
or compliance archive.

**Pre-checks:**
1. Snapshot is `available`.
2. `--role-arn` trusts `rds.amazonaws.com` and has `s3:PutObject` +
   `s3:ListBucket` on `--s3-bucket-name`.
3. Export bucket is in the same region as the snapshot.
4. KMS key (if specified) is accessible to the role.

**Command sequence:**
```bash
aws rds start-export-task \
  --export-task-identifier <task-id> \
  --source-arn arn:aws:rds:us-east-1:111111111111:snapshot:<snap> \
  --s3-bucket-name <export-bucket> \
  --s3-prefix exports/<snap>/ \
  --iam-role-arn arn:aws:iam::111111111111:role/rds-export-role \
  --kms-key-id arn:aws:kms:us-east-1:111111111111:key/<export-key> \
  --export-only database.table1 database.table2 \
  --output Parquet

# Monitor progress
aws rds describe-export-tasks --export-task-identifier <task-id>
```

**Cost:** ~$0.025/GB-hour for the export task duration. A 100 GB snapshot
exporting in 2 hours is ~$5.

**Common failure modes:**
- `IamRoleMissingPermissions` — the role lacks S3/KMS permissions.
- `S3BucketNotExistFault` — the bucket is in a different region or account.

## S3 import procedure (Aurora MySQL only)

**When to use:** bulk-load S3 data into Aurora MySQL.

**Pre-checks:**
1. Target Aurora MySQL cluster is `available`.
2. Source S3 bucket is in the same region.
3. Cluster role has `s3:GetObject` + `s3:ListBucket`.
4. `aurora_load_from_s3_role` is set on the cluster parameter group.

**Command sequence:**
```bash
aws rds start-import-from-s3 \
  --import-identifier <import-id> \
  --source-engine mysql \
  --s3-bucket-name <source-bucket> \
  --s3-prefix imports/ \
  --s3-bucket-role-arn arn:aws:iam::111111111111:role/rds-import-role
```

## Restore time benchmarks (2026, us-east-1)

Approximate durations; actual times vary by instance class, storage type,
and snapshot size.

| Operation | Size | Typical duration |
|---|---|---|
| Manual snapshot create | 100 GB | 1-2 min |
| Manual snapshot create | 1 TB | 5-10 min |
| PITR restore | 100 GB | 15-30 min |
| PITR restore | 1 TB | 60-90 min |
| PITR restore | 5 TB | 4-6 hours |
| Snapshot restore | 100 GB | 15-30 min |
| Snapshot restore | 1 TB | 60-90 min |
| Aurora Backtrack (1h low write) | Any | 2-5 min |
| Aurora Backtrack (1h high write) | Any | 10-30 min |
| Aurora Fast Clone (initial) | Any | <1 min (copy-on-write) |
| Cross-region snapshot copy | 1 TB | 30-60 min |
| S3 export | 100 GB | 1-2 hours |

## Backup configuration defaults

| Setting | Default | Recommended range |
|---|---|---|
| `BackupRetentionPeriod` | 1 day (RDS), 1 day (Aurora) | 7-35 days |
| `PreferredBackupWindow` | Region-specific off-hours | Off-peak, e.g., 03:00-05:00 UTC |
| `PreferredMaintenanceWindow` | Region-specific off-hours | Different from backup window |
| `BacktrackWindow` (Aurora MySQL) | 0 (disabled) | 24-72 hours for prod |
| `BackupTarget` | `region` (automated) | `outposts` for on-prem |
| `CopyTagsToSnapshot` | false | true (for cost allocation) |
| `DeletionProtection` | false | true for production |

## Common restore pitfalls

- **Forgot to update connection strings after restore.** The new endpoint
  is in `Endpoint.Address`; application config, Secrets Manager, Parameter
  Store, Route 53 CNAMEs all need updating atomically.
- **Restored into a single-AZ subnet group.** Multi-AZ restore requires
  subnets in >= 2 AZs; a single-AZ subnet group blocks Multi-AZ.
- **Forgot `--deletion-protection` after verification.** A restored instance
  without deletion protection can be accidentally deleted. Set it after
  the post-verification passes.
- **Skipped the pre-state snapshot for rollback.** RDS state is not
  versioned; capture `describe-db-instances` output before any change.
- **Trusted `available` status alone for PITR.** An instance can be
  `available` with `BackupRetentionPeriod: 0` (no PITR). Always verify
  retention and `LatestRestorableTime` independently.
- **Bulk cross-region copy without cost surfacing.** Cross-region copy
  bills $0.02/GB transfer + destination-region storage. Always surface
  the cost estimate before bulk operations.
