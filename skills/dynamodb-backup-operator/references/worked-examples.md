# Worked Examples (load on demand) — DynamoDB Backup Restore Operator

Secondary worked examples (pre-check failure, snapshot-style restore) moved verbatim from SKILL.md. The primary worked example stays in SKILL.md.


---

## Worked example — pre-check failure (PITR disabled) (moved from SKILL.md)


```text
OPERATION: pitr-restore
VERDICT: BLOCKED
TARGET: prod-orders-table -> prod-orders-table-pitr-2026-08-09
PRE_CHECKS:
  - [PASS] prod-orders-table TableStatus is ACTIVE
  - [FAIL] PointInTimeRecoveryStatus is DISABLED — PITR restore not
    possible. The table has no 35-day continuous recovery window.
  - [SKIP] RestoreDateTime window check skipped (PITR disabled)
  - [PASS] Target table name does not exist (would be valid if PITR
    were enabled)
STEPS: (none — pre-checks failed)
POST_VERIFY: (none)
TABLE_ARN: (none)
NOTES:
  - To enable PITR going forward:
      aws dynamodb update-continuous-backups \
        --table-name prod-orders-table \
        --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
    PITR becomes available within seconds; EarliestRestorableDateTime is
    the moment of enablement.
  - For THIS incident, recover from the most recent on-demand backup:
      aws dynamodb list-backups --table-name prod-orders-table \
        --backup-type USER --time-range-lower-bound 2026-07-01T00:00:00Z
    Then restore-table-from-backup with the latest USER backup ARN.
```

## Worked example — snapshot-style restore (from on-demand backup) (moved from SKILL.md)


```text
OPERATION: snapshot-restore
VERDICT: READY
TARGET: arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table/backup/01712345678900-abcdef
        -> prod-orders-table-restored-2026-08-09
PRE_CHECKS:
  - [PASS] Backup ARN exists (describe-backup OK)
  - [PASS] BackupStatus is AVAILABLE
  - [PASS] Target table name prod-orders-table-restored-2026-08-09 does not exist
  - [PASS] Caller has dynamodb:RestoreTableFromBackup
STEPS:
  1. CONFIRM: About to restore-table-from-backup, creating
     prod-orders-table-restored-2026-08-09 from backup 01712345678900-abcdef
     in account 111111111111 region us-east-1. NEW table; original
     unchanged. Estimated duration: 15-30 minutes for ~60 GB. Proceed?
     (yes/no)
  2. aws dynamodb restore-table-from-backup \
       --target-table-name prod-orders-table-restored-2026-08-09 \
       --backup-arn arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table/backup/01712345678900-abcdef
  3. Poll: aws dynamodb describe-table \
       --table-name prod-orders-table-restored-2026-08-09 \
       --query 'Table.TableStatus'
     Wait for ACTIVE.
POST_VERIFY:
  - (pending execution)
TABLE_ARN: (pending)
NOTES:
  - Snapshot restore recovers to the backup-creation instant, not any
    arbitrary second. For second-level recovery, enable PITR and use
    restore-table-to-point-in-time next time.
  - Same side-config gap as PITR restore: autoscaling, alarms, IAM,
    Streams, TTL, tags must be re-applied.
```