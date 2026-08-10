---
description: Operate DynamoDB backup and restore workflows — on-demand backups via create-backup, point-in-time recovery (PITR), AWS Backup cross-region/cross-account plans, snapshot-style restore, PITR restore with selective attribute projection, S3 export/import — with deterministic pre-checks, CONFIRM gate, and post-verification including the side-config re-apply checklist.
nl_triggers:
  - "create DynamoDB backup"
  - "enable DynamoDB PITR"
  - "restore DynamoDB table"
  - "restore DynamoDB to point in time"
  - "PITR restore DynamoDB"
  - "restore DynamoDB from backup"
  - "copy DynamoDB table cross-region"
  - "export DynamoDB to S3"
  - "import DynamoDB from S3"
  - "DynamoDB pre-migration backup"
  - "recover DynamoDB data"
  - "DynamoDB AWS Backup plan"
  - "verify DynamoDB restore"
  - "DynamoDB selective restore"
  - "DynamoDB disaster recovery"
routes_to: dynamodb-backup-operator
---

# /aws:operate-dynamodb-backup

Activate the `dynamodb-backup-operator` skill and plan/execute a
DynamoDB backup/restore operation with deterministic pre-checks,
CONFIRM gate, and post-verification.

## What it does

Reads a table configuration plus the intended operation and applies
the priority-ordered pre-check sequence:

1. Pre-flight table metadata gate — short-circuit `CREATING`/`DELETING`
   /`INACCESSIBLE_ENCRYPTION_CREDENTIALS` states, Global Table replica
   awareness.
2. Pre-check gate — BLOCKED if any check fails (PITR disabled for PITR
   restore, backup missing or CREATING for snapshot restore, target
   name collision, IAM permission missing, CMK inaccessible).
3. READY — emit the exact CLI sequence with all flags populated, the
   expected side-effects (new table name, new backup ARN, new export
   job ARN), and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   poll until operation completes (RESTORING → ACTIVE, CREATING →
   AVAILABLE, IN_PROGRESS → COMPLETED).
5. Post-verification — describe-table status, item count, sentinel
   query, GSI/LSI ACTIVE check, side-config re-apply checklist
   (autoscaling, alarms, IAM, Streams, TTL, tags,
   DeletionProtectionEnabled), connection-string cutover plan.
   COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <create-backup | enable-pitr | pitr-restore | snapshot-restore | export | import | aws-backup-restore>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <table-name, backup-arn, restore-target>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait/poll command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
TABLE_ARN: <new table ARN if restore, "unchanged" if backup-create>
NOTES: <connection-string update, side-config re-apply, cleanup, caveats>
```

## When to invoke

Paste a table configuration plus the intended operation, or just
describe the scenario and ask any of:

- "create a pre-migration backup"
- "restore to a point in time"
- "restore from this backup ARN"
- "export this table to S3 for analytics"
- "did my PITR window cover this incident?"
- "set up AWS Backup for this table"

A bare table name + any operation verb ("restore this table", "back up
this table") also routes here via the orchestrator.

## Inputs

- Source table configuration (`describe-table` JSON): status, billing
  mode, throughput, SSE/CMK, GSI/LSI, deletion protection.
- Continuous backups state (`describe-continuous-backups`):
  `PointInTimeRecoveryStatus`, `EarliestRestorableDateTime`,
  `LatestRestorableDateTime`.
- The intended operation: `create-backup`, `enable-pitr`,
  `pitr-restore`, `snapshot-restore`, `export`, `import`,
  `aws-backup-restore`.
- For PITR restore: the `--restore-date-time` (verified against the
  PITR window).
- For snapshot restore: the backup ARN (verified to be AVAILABLE).
- For restore: target table name (verified free), billing-mode override
  decision, CMK access in the target account.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for
  failure.
- For READY: the exact CLI sequence, expected duration, expected side-
  effects, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the new
  table ARN, side-config re-apply checklist, connection-string cutover
  plan, and cleanup plan.
- For BLOCKED: the specific failure reason and the remediation step
  (e.g., `update-continuous-backups`, wait for backup AVAILABLE).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for DynamoDB backup and restore).
- `/aws:audit-dynamodb-table` for the broader table hardening audit
  (encryption, capacity mode, GSI quota, deletion protection) — run
  before and after restore to verify posture.
- `/aws:audit-backup-plan` for the AWS Backup plan side — AWS Backup
  complements DynamoDB PITR with cross-region vault copies and
  Vault Lock retention.
