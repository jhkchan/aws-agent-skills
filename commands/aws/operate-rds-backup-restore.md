---
description: Operate RDS and Aurora backup and restore workflows — automated backup configuration, manual snapshots, PITR, snapshot restore, Aurora Backtrack, S3 export/import — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "configure RDS backup retention"
  - "create RDS manual snapshot"
  - "restore RDS to point in time"
  - "PITR restore RDS"
  - "restore RDS from snapshot"
  - "backtrack Aurora cluster"
  - "Aurora fast clone"
  - "copy RDS snapshot cross-region"
  - "share RDS snapshot cross-account"
  - "export RDS snapshot to S3"
  - "import S3 into Aurora MySQL"
  - "RDS pre-migration snapshot"
  - "recover from bad RDS change"
  - "verify RDS restore"
  - "Aurora backtrack window"
routes_to: rds-backup-restore-operator
---

# /aws:operate-rds-backup-restore

Activate the `rds-backup-restore-operator` skill and plan/execute an RDS or
Aurora backup/restore operation with deterministic pre-checks, CONFIRM gate,
and post-verification.

## What it does

Reads an instance/cluster configuration plus the intended operation and
applies the priority-ordered pre-check sequence:

1. Pre-flight instance metadata gate — short-circuit `modifying`/`creating`
   states, Global Database writers, active Database Activity Streams.
2. Pre-check gate — BLOCKED if any check fails (missing subnet/SG/option
   group/parameter group/KMS key, retention=0 for PITR, snapshot missing,
   backtrack window exceeded, target identifier collision).
3. READY — emit the exact CLI sequence with all flags populated, the
   expected side-effects (new endpoint for restore, in-place rewind for
   backtrack, new export task ID), and the CONFIRM gate prompt.
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI, wait
   for the operation to complete.
5. Post-verification — describe-db-instances status, connectivity test,
   data consistency check, connection-string cutover plan, cleanup plan.
   COMPLETED only if ALL post-verification checks pass.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <create-snapshot | pitr-restore | snapshot-restore | backtrack | export | import>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <instance-id, cluster-id, snapshot-id>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ENDPOINT: <new endpoint if restore, "unchanged" if backtrack>
NOTES: <connection-string update, cleanup, caveats>
```

## When to invoke

Paste an instance/cluster configuration plus the intended operation, or
just describe the scenario and ask any of:

- "create a pre-migration snapshot"
- "restore to a point in time"
- "restore from snapshot"
- "backtrack this Aurora cluster"
- "share this snapshot cross-account"
- "export this snapshot to S3"
- "did my backup retention window cover this incident?"

A bare instance-id + any operation verb ("restore this instance", "backtrack
the cluster") also routes here via the orchestrator.

## Inputs

- Source instance/cluster configuration (`describe-db-instances` /
  `describe-db-clusters` JSON): status, engine, version, retention,
  `LatestRestorableTime`, encryption, Multi-AZ, subnet group, security
  group, option group, parameter group.
- The intended operation: `create-snapshot`, `pitr-restore`, `snapshot-
  restore`, `backtrack`, `export`, `import`, `cross-region-copy`,
  `cross-account-share`.
- For PITR: the `--restore-time` (verified against
  `[EarliestRestorableTime, LatestRestorableTime]`).
- For backtrack: the `--backtrack-to-timestamp` (verified against
  `BacktrackWindow`).
- For restore: target identifier, subnet group, security group, option
  group, parameter group, KMS key (all verified to exist).

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[FAIL]` per check and reason for failure.
- For READY: the exact CLI sequence, expected duration, expected side-
  effects, and the CONFIRM gate prompt.
- For COMPLETED: POST_VERIFY list with `[PASS]` per check, the new
  endpoint, connection-string cutover plan, and cleanup plan.
- For BLOCKED: the specific failure reason and the remediation step (e.g.,
  `modify-db-instance --backup-retention-period 7`, `create-db-subnet-group`).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 4 Operate specialist for RDS/Aurora backup and restore).
- `/aws:audit-backup-plan` for the AWS Backup plan side — AWS Backup
  complements RDS automated backups with cross-service orchestration and
  vault lock.
- `/aws:audit-rds-instance` for the security/compliance posture of the
  RDS instance before/after restore.
