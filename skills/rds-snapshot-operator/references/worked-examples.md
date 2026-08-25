# Worked Examples — RDS Snapshot Operator


## Worked example — Aurora clone from snapshot

```text
OPERATION: clone-from-snapshot
VERDICT: OPERATION_COMPLETED
TARGET: prod-aurora-cluster (snapshot:
        prod-aurora-cluster-snapshot-20260805)
PRE_CHECKS:
  - [PASS] Source snapshot is a DBClusterSnapshot (Aurora)
  - [PASS] Engine: aurora-mysql, Version: 8.0.mysql_aurora.3.05.2
  - [PASS] Snapshot Status: available
  - [PASS] KMS key Enabled for encrypted clone
STEPS:
  1. CONFIRM: About to create Aurora cluster prod-aurora-clone from
     snapshot prod-aurora-cluster-snapshot-20260805 in account
     111111111111 region us-east-1. Clone is near-instant
     (copy-on-write). Proceed? (yes/no)
  2. aws rds restore-db-cluster-from-snapshot \
       --db-cluster-identifier prod-aurora-clone \
       --snapshot-identifier prod-aurora-cluster-snapshot-20260805 \
       --engine aurora-mysql \
       --db-subnet-group-name prod-db-subnet-group \
       --vpc-security-group-ids sg-prod-aurora
  3. (Aurora clusters require instance creation after cluster restore)
     aws rds create-db-instance \
       --db-instance-identifier prod-aurora-clone-instance-1 \
       --db-instance-class db.r6g.xlarge \
       --engine aurora-mysql \
       --db-cluster-identifier prod-aurora-clone
POST_VERIFY:
  - [PASS] DBCluster prod-aurora-clone Status: available
  - [PASS] DBInstance prod-aurora-clone-instance-1 Status: available
  - [PASS] Clone completed in <30 seconds (copy-on-write)
NOTES:
  - Aurora clones share storage with the source snapshot at the page
    level. Writes to the clone allocate new pages; reads of unmodified
    pages are served from shared storage. No data copy overhead.
  - The clone is a full independent cluster — changes to the clone do
    NOT affect the source cluster.
  - To clean up: delete the clone cluster, then optionally delete the
    source snapshot if no longer needed.
```

## Worked example — PITR restore (REVIEW_REQUIRED)

```text
OPERATION: restore-pitr
VERDICT: REVIEW_REQUIRED
TARGET: prod-orders-db (restore-to: 2026-08-05T14:35:00Z)
PRE_CHECKS:
  - [PASS] BackupRetentionPeriod: 7 (>= 1, automated backups enabled)
  - [PASS] LatestRestorableTime: 2026-08-05T14:40:12Z
  - [PASS] EarliestRestorableTime: 2026-07-29T03:00:00Z
  - [PASS] Target time 2026-08-05T14:35:00Z is within restorable window
  - [REVIEW] Restore creates a NEW instance (prod-orders-db-pitr) with a
    new endpoint. Connection strings must be updated post-restore.
  - [REVIEW] Option group prod-orders-options includes TDE (Transparent
    Data Encryption). Must specify the SAME option group on restore or
    data will be unreadable.
  - [REVIEW] Security group sg-prod-rds must be specified explicitly.
    The restore defaults to the DEFAULT security group.
  - [REVIEW] PITR granularity is 5 minutes for RDS. Actual restore time
    may be rounded to 2026-08-05T14:35:00Z (nearest 5-min boundary).
STEPS:
  1. CONFIRM: About to restore prod-orders-db to 2026-08-05T14:35:00Z
     as new instance prod-orders-db-pitr in account 111111111111 region
     us-east-1. Estimated time: 20-45 minutes. Proceed? (yes/no)
  2. aws rds restore-db-instance-to-point-in-time \
       --source-db-instance-identifier prod-orders-db \
       --target-db-instance-identifier prod-orders-db-pitr \
       --restore-time 2026-08-05T14:35:00Z \
       --db-instance-class db.r6g.xlarge \
       --option-group-name prod-orders-options \
       --vpc-security-group-ids sg-prod-rds \
       --db-subnet-group-name prod-db-subnet-group
  3. aws rds describe-db-instances \
       --db-instance-identifier prod-orders-db-pitr \
       --query 'DBInstances[0].DBInstanceStatus'
POST_VERIFY:
  - (pending execution)
NOTES:
  - After the restore completes, verify application connectivity to the
    NEW endpoint. Then cut over DNS/routing from the original to the
    restored instance.
  - The original instance (prod-orders-db) is UNCHANGED. You must
    delete it manually after the cutover if no longer needed.
  - Create a manual snapshot of the original before deletion:
    aws rds delete-db-instance \
      --db-instance-identifier prod-orders-db \
      --final-db-snapshot-identifier prod-orders-db-final-20260805
```

## Worked example — cross-region copy (DR)

```text
OPERATION: copy-snapshot
VERDICT: OPERATION_COMPLETED
TARGET: prod-orders-db (snapshot: prod-orders-db-pre-upgrade-20260805
        → copy to us-west-2 as prod-orders-db-dr-20260805)
PRE_CHECKS:
  - [PASS] Source snapshot Status: available in us-east-1
  - [PASS] Source snapshot Encrypted: true
  - [PASS] Target KMS key arn:aws:kms:us-west-2:111111111111:key/dr-cmk
    Enabled in us-west-2
  - [PASS] Source KMS key policy allows cross-region copy
STEPS:
  1. CONFIRM: About to copy encrypted snapshot
     prod-orders-db-pre-upgrade-20260805 from us-east-1 to us-west-2
     as prod-orders-db-dr-20260805, re-encrypting with DR KMS key.
     Estimated time: 30-60 minutes (500 GB). Proceed? (yes/no)
  2. aws rds copy-db-snapshot \
       --source-db-snapshot-identifier arn:aws:rds:us-east-1:111111111111:snapshot:prod-orders-db-pre-upgrade-20260805 \
       --target-db-snapshot-identifier prod-orders-db-dr-20260805 \
       --kms-key-id arn:aws:kms:us-west-2:111111111111:key/dr-cmk \
       --region us-west-2
  3. aws rds describe-db-snapshots \
       --db-snapshot-identifier prod-orders-db-dr-20260805 \
       --region us-west-2 \
       --query 'DBSnapshots[0].Status'
POST_VERIFY:
  - [PASS] Snapshot prod-orders-db-dr-20260805 Status: available in
    us-west-2
  - [PASS] Encrypted: true, KMS key:
    arn:aws:kms:us-west-2:111111111111:key/dr-cmk
NOTES:
  - Cross-region snapshot copy re-encrypts with the target-region key.
    The original KMS key cannot be used (KMS keys are region-scoped).
  - To automate DR snapshots, use AWS Backup with a cross-region copy
    rule, or DLM with a cross-region copy policy.
  - Cost: $0.02/GB for cross-region data transfer + $0.095/GB-month
    for snapshot storage in the DR region.
```

## Worked example — snapshot lifecycle cleanup

```text
OPERATION: delete-snapshot
VERDICT: REVIEW_REQUIRED
TARGET: snapshots older than 30 days (lifecycle cleanup)
PRE_CHECKS:
  - [PASS] Lambda function rds-snapshot-lifecycle-cleanup exists
  - [PASS] EventBridge rule rds-snapshot-cleanup-daily schedule: rate(1 day)
  - [REVIEW] 3 snapshots older than 30 days found:
    - dev-test-db-snap-20260701 (35 days old, tagged Environment: dev)
    - staging-db-snap-20260710 (26 days old, tagged Environment: staging)
    - prod-orders-db-snap-20260705 (31 days old, tagged DoNotDelete: true)
  - [REVIEW] prod-orders-db-snap-20260705 has compliance hold tag
    (DoNotDelete: true). Lambda will SKIP this snapshot.
STEPS:
  1. CONFIRM: About to delete 2 snapshots (skipping 1 compliance-hold
     snapshot) via the lifecycle Lambda. This is irreversible. Proceed?
     (yes/no)
  2. aws lambda invoke \
       --function-name rds-snapshot-lifecycle-cleanup \
       --payload '{"dryRun": false, "retentionDays": 30}' \
       /tmp/snapshot-cleanup-result.json
  3. cat /tmp/snapshot-cleanup-result.json
POST_VERIFY:
  - [PASS] dev-test-db-snap-20260701: deleted
  - [PASS] staging-db-snap-20260710: deleted
  - [PASS] prod-orders-db-snap-20260705: skipped (DoNotDelete tag)
NOTES:
  - The Lambda function uses describe-db-snapshots to list manual
    snapshots, filters by SnapshotCreateTime < (now - retentionDays),
    checks for the DoNotDelete tag, and calls delete-db-snapshot.
  - EventBridge triggers the Lambda daily at 02:00 UTC.
  - Add CloudWatch alarm on Lambda Errors to detect cleanup failures.
```
