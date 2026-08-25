# RDS Backup Restore Operator — worked examples (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

### Worked example — pre-check failure (moved from SKILL.md)

```text
OPERATION: pitr-restore
VERDICT: BLOCKED
TARGET: prod-orders-db -> prod-orders-db-pitr-2026-08-07
PRE_CHECKS:
  - [PASS] prod-orders-db DBInstanceStatus is available
  - [FAIL] BackupRetentionPeriod is 0 — PITR disabled (no transaction logs
    retained). Only manual snapshot restore is possible.
  - [FAIL] LatestRestorableTime is null (no automated backups exist)
  - [PASS] Target identifier does not exist (would be valid if PITR were
    enabled)
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
ENDPOINT: (none)
NOTES:
  - To enable PITR going forward: aws rds modify-db-instance \
      --db-instance-identifier prod-orders-db \
      --backup-retention-period 7 --apply-immediately
    This triggers an immediate automated backup; PITR becomes available
    after the backup completes (~30 minutes for 500 GB).
  - For THIS incident, recover from the most recent manual snapshot:
    aws rds describe-db-snapshots --db-instance-identifier prod-orders-db \
      --snapshot-type manual --query 'reverse(sort_by(DBSnapshots, \
      &SnapshotCreateTime))[0]'
```

### Worked example — Aurora backtrack (moved from SKILL.md)

```text
OPERATION: backtrack
VERDICT: READY
TARGET: aurora-prod-cluster
PRE_CHECKS:
  - [PASS] aurora-prod-cluster DBClusterStatus is available
  - [PASS] Engine is aurora-mysql (Backtrack supported)
  - [PASS] BacktrackWindow is 86400 (24 hours)
  - [PASS] BacktrackToTimestamp 2026-08-07T09:00:00Z is within
    [now - 24h, now]
  - [PASS] Cluster is NOT a writer in a Global Database
  - [PASS] No existing backtrack in progress
STEPS:
  1. CONFIRM: About to backtrack-db-cluster aurora-prod-cluster to
     2026-08-07T09:00:00Z in account 111111111111 region us-east-1.
     This is an IN-PLACE rewind (no new cluster, endpoint unchanged).
     Estimated duration: 2-10 minutes (scales with DML volume). Proceed?
     (yes/no)
  2. aws rds backtrack-db-cluster \
       --db-cluster-identifier aurora-prod-cluster \
       --backtrack-to-timestamp 2026-08-07T09:00:00Z
  3. aws rds wait db-cluster-available --db-cluster-identifier aurora-prod-cluster
POST_VERIFY:
  - (pending execution)
ENDPOINT: unchanged (backtrack is in-place)
NOTES:
  - Backtrack does NOT create a new cluster or endpoint.
  - Backtrack charges per DML change reversed (~$0.012/change in us-east-1).
  - Backtrack cannot undo all DDL operations; verify the bad change was DML
    before executing.
  - Backtrack creates a record that can be re-forwarded (forward backtrack)
    if you rewind too far.
```

