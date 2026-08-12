---
description: Operate Amazon RDS and Aurora snapshot workflows — create manual snapshots, copy cross-region for DR, restore via PITR, share cross-account, clone Aurora from snapshot, export to S3, lifecycle cleanup, update backup retention — with deterministic pre-checks, CONFIRM gate, and post-verification.
nl_triggers:
  - "create RDS snapshot"
  - "manual snapshot before upgrade"
  - "change backup retention"
  - "PITR restore"
  - "point-in-time recovery"
  - "copy snapshot to DR region"
  - "cross-region snapshot copy"
  - "share snapshot cross-account"
  - "restore from snapshot"
  - "Aurora clone from snapshot"
  - "Aurora backtrack"
  - "export snapshot to S3"
  - "snapshot lifecycle cleanup"
  - "delete old snapshots"
  - "Blue/Green deploy snapshot"
  - "snapshot size monitoring"
  - "RDS snapshot management"
  - "Aurora snapshot"
  - "RDS backup"
routes_to: rds-snapshot-operator
---

# /aws:operate-rds-snapshots

Activate the `rds-snapshot-operator` skill and plan/execute an RDS or
Aurora snapshot operation with deterministic pre-checks, CONFIRM gate,
and post-verification.

## What it does

Reads an instance/cluster configuration plus the intended operation
and applies the priority-ordered pre-check sequence:

1. Pre-flight instance metadata gate — short-circuit deleting/failed
   instances, verify KMS key state, check option group compatibility.
2. Pre-check gate — verify instance state, storage type, snapshot
   availability, KMS key, IAM export role permissions.
3. Emit OPERATION_COMPLETED for straightforward operations (create,
   copy, clone, export). Emit REVIEW_REQUIRED for operations needing
   human attention (PITR restore, lifecycle deletion with compliance
   holds, cross-account sharing).
4. Execute behind CONFIRM gate — capture pre-state, execute the CLI,
   monitor snapshot status transitions.
5. Post-verification — snapshot reached `available`, restore instance
   is `available`, export task is `complete`, shared snapshot visible
   to target account.

Emits a deterministic VERDICT per operation:

```text
OPERATION: <create-snapshot | copy-snapshot | restore-pitr | share-snapshot | clone-from-snapshot | export-snapshot | delete-snapshot | update-retention>
VERDICT: OPERATION_COMPLETED | REVIEW_REQUIRED
TARGET: <instance-or-cluster-id> (snapshot: <snap-id-or-"none">)
PRE_CHECKS:
  - [PASS] <check description>
  - [REVIEW] <check description> — <item requiring human attention>
STEPS:
  1. <CLI command with flags populated>
  2. <wait / monitoring command>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <schedule, monitoring, caveats>
```

## When to invoke

Paste an instance/cluster configuration plus the intended operation,
or just describe the scenario and ask any of:

- "create a snapshot before the upgrade"
- "copy this snapshot to us-west-2 for DR"
- "restore to 2:35 PM yesterday"
- "share this snapshot with account 222222222222"
- "clone the Aurora cluster from this snapshot"
- "export snapshot data to S3"
- "delete snapshots older than 30 days"
- "change backup retention to 14 days"

A bare instance-id + any snapshot verb ("snapshot this database",
"restore from last night") also routes here via the orchestrator.

## Inputs

- Instance configuration (`describe-db-instances` JSON):
  `DBInstanceStatus`, `StorageType`, `AllocatedStorage`, `Encrypted`,
  `KmsKeyId`, `OptionGroupMemberships`, `VpcSecurityGroups`,
  `BackupRetentionPeriod`, `LatestRestorableTime`, `DeletionProtection`.
- Snapshot configuration (`describe-db-snapshots` JSON): `Status`,
  `Encrypted`, `AllocatedStorage`, `Engine`, `SnapshotCreateTime`.
- KMS key state (`describe-key` JSON): `Enabled`, `KeyState`.
- For Aurora: cluster snapshot (`describe-db-cluster-snapshots` JSON).
- For cross-account: sharing configuration and target account ID.
- For export: IAM role, S3 bucket, KMS key for export.

## Outputs

- One VERDICT block per operation.
- PRE_CHECKS list with `[PASS]` / `[REVIEW]` per check.
- For OPERATION_COMPLETED: POST_VERIFY list with `[PASS]` per check,
  the snapshot ARN, monitoring recommendations.
- For REVIEW_REQUIRED: the specific items requiring human review (new
  endpoint, option group, security group, compliance hold, PITR
  granularity) and the remediation steps once approved.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Operate specialist for RDS snapshot management).
- `/aws:audit-rds-backups` for the audit-side counterpart — auditing
  backup posture across many instances without changing state.
- `/aws:deploy-rds-instance` for the deploy-side counterpart —
  provisioning new RDS instances with backup retention pre-wired.
