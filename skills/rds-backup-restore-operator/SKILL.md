---
name: rds-backup-restore-operator
description: >-
  Operates RDS and Aurora backup and restore workflows safely — automated
  backup window configuration, manual snapshots for pre-maintenance safety,
  cross-region and cross-account snapshot copy, point-in-time restore (PITR),
  Aurora Backtrack for in-place rewind, S3 export/import, and full post-
  restore verification. Runs deterministic pre-checks (subnet group, security
  group, option group, KMS key, instance status), executes the operation
  behind a CONFIRM gate, and emits a verdict (READY | BLOCKED | COMPLETED)
  per operation with the exact CLI sequence, expected side-effects (new
  instance endpoint, connection-string updates), and verification commands.
  Use when configuring RDS backup retention, creating pre-migration snapshots,
  restoring to a point in time, backtracking an Aurora cluster, exporting a
  snapshot to S3, or recovering from a bad change.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline plan classification. Live-account
  operations use aws rds describe-db-instances, aws rds describe-db-snapshots,
  aws rds describe-db-cluster-backtracks, aws rds create-db-snapshot, aws rds
  restore-db-instance-to-point-in-time, aws rds restore-db-instance-from-db-
  snapshot, aws rds backtrack-db-cluster, aws rds start-export-task, and aws
  rds start-import-from-s3 (AWS CLI v2, SSO or key-based credentials).
keywords:
  - RDS
  - Amazon Aurora
  - Aurora MySQL
  - Aurora PostgreSQL
  - automated backup
  - manual snapshot
  - point-in-time recovery
  - PITR
  - backtrack
  - fast database clone
  - cross-region snapshot copy
  - cross-account snapshot share
  - S3 export
  - S3 import
  - backup retention
  - backup window
  - maintenance window
  - Multi-AZ
  - restore-db-instance-to-point-in-time
  - restore-db-instance-from-db-snapshot
  - backtrack-db-cluster
  - create-db-snapshot
  - start-export-task
tags: [rds, aurora, databases, backup, restore, pitr, backtrack, snapshot, recovery, disaster-recovery]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 4
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: operate
  skill_class: capability
  verdict_shape: "READY | BLOCKED | COMPLETED"
  when_to_use: >-
    Configuring RDS backup retention or backup window, creating a manual
    snapshot before maintenance or a risky change, copying snapshots cross-
    region or cross-account, restoring an RDS instance to a point in time,
    restoring from a snapshot, backtracking an Aurora MySQL cluster, exporting
    a snapshot to S3, importing from S3 into Aurora MySQL, or recovering
    from a bad schema change.
  activation_triggers:
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
  invocation_schema: >-
    Input: either (a) an RDS instance/cluster configuration with the intended
    operation (create-snapshot, pitr-restore, snapshot-restore, backtrack,
    export, import), OR (b) an instance-id / cluster-id + operation for
    live-account execution. Output: deterministic OPERATION/VERDICT/PRE_CHECKS/
    STEPS/POST_VERIFY block per operation, where VERDICT is one of READY,
    BLOCKED, COMPLETED.
---

# RDS Backup Restore Operator

## What this skill does

Executes RDS/Aurora backup and restore operations correctly and safely.
Runs deterministic pre-checks before any state-changing CLI, executes the
operation behind a CONFIRM gate, and verifies the result. Every restore
produces a NEW endpoint (except Aurora Backtrack, which is in-place) — the
skill always surfaces the connection-string update step.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (missing subnet/SG/option group, retention=0 for PITR, instance not available, KMS key inaccessible) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Operation finished and post-verification passed | Emit endpoint, verification results, cleanup steps |

**Priority order for pre-checks (apply in this sequence, all must pass for
READY):**

1. **Instance/cluster status** — must be `available` (or `backing-up` for
   read operations). `modifying`, `upgrading`, `creating`, `deleting` → BLOCKED.
2. **Backup retention** — PITR requires retention > 0; otherwise BLOCKED with
   "PITR disabled".
3. **Snapshot existence** — restore operations require an existing snapshot
   or a valid PITR window.
4. **Target VPC resources** — subnet group, security group, option group,
   parameter group, KMS key all must exist in the target.
5. **Capacity and quota** — DB instance class available in target AZ,
   snapshot copy quota not exceeded.

**Cost/time baselines (2026):**

- Snapshot create time: ~1 min per 100 GB (storage-bound).
- Snapshot restore time: ~30-90 min for 1 TB (proportional to data size).
- Aurora Backtrack: seconds to minutes, regardless of cluster size.
- Cross-region snapshot copy: data-transfer fee ($0.02/GB cross-region) +
  destination-region storage.
- S3 export: ~$0.025/GB-hour for the export task; writes Parquet to S3.

## Mindset

**One-line takeaway:** restore always creates a new instance with a new
endpoint — except Aurora Backtrack, which is an in-place rewind. Driven by
three RDS realities:

- **Restore is non-destructive by default.** `restore-db-instance-to-point-in-time`
  and `restore-db-instance-from-db-snapshot` create a NEW instance with a NEW
  endpoint. The original is unchanged. Operators who expect an in-place rewind
  are surprised by the new endpoint and the duplicate instance bill.
- **PITR requires retention > 0.** Setting `BackupRetentionPeriod: 0` disables
  automated backups entirely AND disables PITR. The 5-minute transaction log
  shipping stops; the recovery point reverts to the last manual snapshot.
- **Aurora Backtrack is the only in-place rewind.** Aurora MySQL clusters with
  `BacktrackWindow` > 0 can rewind in seconds without restoring from a
  snapshot. Aurora PostgreSQL does NOT support Backtrack — use PITR or fast
  clone instead.

## Pre-flight: instance metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-db-instances` paginates at 100/page — drain
`--marker` (or `--starting-token` for the AWS CLI v2 pagination syntax) to
completion. `describe-db-snapshots` paginates at 100/page similarly.

**Live-account pre-flight (skip if offline plan audit):**
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

**Malformed input:** if the input JSON is invalid or missing required fields,
emit `VERDICT: ERROR` with `REASON: Instance/operation configuration is not
valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws rds describe-db-instances --db-instance-identifier
<id> --output json and re-plan.`

| Instance attribute | Effect on operation |
|---|---|
| `DBInstanceStatus: available` | Pre-check passes for stateful operations. |
| `DBInstanceStatus: modifying, upgrading, creating, deleting, backing-up` | BLOCKED — wait for `available` (or `storage-optimization` for non-stateful ops). |
| `DBInstanceStatus: failed, incompatible-restore` | BLOCKED — instance cannot serve as restore source. |
| `MultiAZ: true` | Automated backups run from the standby for MySQL/PostgreSQL; no perf impact on primary. |
| `StorageEncrypted: true` | Restore requires KMS key access in the target. Cross-account restore needs the source account's KMS key policy grant. |
| `BackupRetentionPeriod: 0` | PITR BLOCKED — automated backups disabled. Only manual snapshot restore is available. |
| `BackupRetentionPeriod: 1-35` | PITR window is `now - retention` to `~5 min ago`. |
| `Engine: aurora-mysql` | Backtrack available if `BacktrackWindow > 0`. Fast clone available. |
| `Engine: aurora-postgresql` | Backtrack NOT supported. Use PITR or fast clone. |
| `Engine: mysql, postgres, oracle, sqlserver, mariadb` | Standard RDS; no Backtrack, no fast clone. |
| `DBSubnetGroup` missing or `Subnets: []` | Restore BLOCKED — no target subnets. |
| `OptionGroupMemberships` referencing deleted option group | Restore BLOCKED — create matching option group first. |
| `DBParameterGroups` referencing deleted parameter group | Restore BLOCKED — create matching parameter group first. |
| `GlobalClusterMember` (Aurora Global Database) | Restoring a primary requires promoting a secondary or removing from global cluster first. |
| `ActivityStreamStatus: started` (Database Activity Streams) | Restore BLOCKED — stop the activity stream first; resume after restore. |
| `ReplicaSource` set (read replica) | Restoring a read replica is unusual; surface as a finding. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious RDS/Aurora behaviors

These behaviors are easy to misjudge without operational RDS experience.
Each changes a plan if ignored:

- **Restore creates a NEW instance with a NEW endpoint.** Always. The original
  instance is unchanged. Operators must update application connection strings
  to the new endpoint. This is the single most common RDS restore surprise.

- **PITR restore uses the `LatestRestorableTime` from automated backups.**
  The recoverable window is `[SnapshotCreateTime, LatestRestorableTime]`,
  where `LatestRestorableTime` lags real-time by ~5 minutes (the transaction-
  log shipping cadence). You cannot restore to "right now" — the latest
  recoverable point is 5 minutes ago.

- **`BackupRetentionPeriod: 0` disables PITR entirely.** Setting retention to
  0 stops automated backups AND transaction-log shipping. The only recovery
  option becomes manual snapshots. This is irreversible for the existing
  window — once disabled, the unbacked-up period cannot be recovered.

- **Aurora Backtrack is in-place and fast but bounded.** The `BacktrackWindow`
  (1-72 hours, configurable up to 7 days for Aurora MySQL) bounds how far back
  you can rewind. Backtrack does NOT create a new cluster — it reverses DML
  in-place. Operations NOT supported by Backtrack: DDL rollback is limited;
  Backtrack cannot undo some CREATE/DROP operations. Test before relying on
  Backtrack for DDL rollback.

- **Aurora Fast Database Clone is instant but storage-billed.** An Aurora
  clone shares storage with the source (copy-on-write), so the clone is
  instant regardless of data size. However, as the clone writes divergent
  pages, storage grows — a long-lived clone can double the storage bill.

- **Cross-region snapshot copy requires destination-region KMS for encrypted
  snapshots.** The source-region KMS key cannot decrypt in the destination
  region. The copy operation re-encrypts with a destination-region KMS key
  that you specify via `--kms-key-id`.

- **Cross-account snapshot share requires both snapshot share AND KMS key
  policy grant.** Sharing an encrypted snapshot via
  `modify-db-snapshot-attribute` is necessary but NOT sufficient — the
  source account's KMS key policy must allow the recipient account to
  `kms:Decrypt` and `kms:CreateGrant`. Without the KMS side, the recipient
  can describe the snapshot but cannot restore from it.

- **Manual snapshots persist after the instance is deleted.** Deleting an
  RDS instance with `SkipFinalSnapshot: false` (or true) does NOT delete
  manual snapshots. Manual snapshots persist indefinitely until explicitly
  deleted — they are the long-term recovery source. Automated backups
  (retention-managed) ARE deleted with the instance.

- **Restoring from a snapshot does NOT inherit tags by default.** Use
  `--copy-tags-to-snapshot` on the source instance, or pass tags explicitly
  on `restore-db-instance-from-db-snapshot --tags`. Tag drift on restored
  instances is a common cost-allocation gap.

- **Option groups and parameter groups must match the engine major version.**
  A snapshot from MySQL 8.0 cannot be restored with the MySQL 5.7 option
  group. Aurora cluster parameter groups differ from instance parameter
  groups — surface both.

- **Aurora Backtrack performance scales with the change volume, not cluster
  size.** Backtracking 1 hour of high-write traffic may take longer than
  backtracking 24 hours of low-write traffic. Aurora Backtrack charges per
  backtrack record ($0.012 per backtrack change in us-east-1).

- **`modify-db-instance --backup-retention-period` triggers a backup.**
  Increasing retention from 0 to 7 immediately starts an automated backup
  run; the instance enters `modifying` then `backing-up` state. The PITR
  window only becomes available after the first successful automated backup
  completes (can take 30+ minutes for large instances).

- **Multi-AZ failover does NOT affect backup continuity.** Backups run from
  the standby in a Multi-AZ deployment; a primary failover does not interrupt
  the backup window. Single-AZ instances pause I/O during the backup window.

- **`RestoreTime` must be within the retention window.** Specifying a
  `--restore-time` outside `[SnapshotCreateTime, LatestRestorableTime]`
  returns `InvalidParameterValue`. Always check `LatestRestorableTime` via
  `describe-db-instances` before specifying a restore time.

- **Aurora continuous backup is always-on (no `BackupRetentionPeriod: 0`).**
  Aurora clusters require retention >= 1; PITR is always available. The
  Aurora `BackupRetentionPeriod` controls the continuous-backup window
  (1-35 days) AND the automated-snapshot retention.

- **S3 export requires the snapshot to be in `available` state and the
  export role to trust `rds.amazonaws.com`.** The `--role-arn` and
  `--s3-bucket-name` must be in the same account; the role needs
  `s3:PutObject`, `s3:ListBucket`, `kms:Decrypt` on the export bucket.

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is BLOCKED
with the failed checks enumerated in PRE_CHECKS. Do NOT execute the
operation.

**For ALL operations:**
1. `DBInstanceStatus` (or `DBClusterStatus` for Aurora) is `available` (or
   `backing-up`/`storage-optimization` for read-only operations).
2. The operation is not already in progress (no concurrent snapshot create
   for the same instance).
3. IAM role for the operator holds the required RDS permissions.
4. Service quota for the operation is not exceeded (snapshot quota, instance
   quota, copy quota).

**For snapshot create (`create-db-snapshot`):**
5. Instance is in `available` state (not `modifying` or `creating`).
6. No existing manual snapshot with the same `--db-snapshot-identifier`.

**For PITR restore (`restore-db-instance-to-point-in-time`):**
5. `BackupRetentionPeriod > 0` on the source instance.
6. `LatestRestorableTime` >= `--restore-time` >= `EarliestRestorableTime`.
7. Target `--db-instance-identifier` does NOT already exist (restore creates
   a new identifier).
8. Target DB subnet group exists and has subnets in >= 2 AZs (recommended).
9. Target security group exists in the same VPC as the subnet group.
10. Target option group matches the engine + engine-version.
11. Target parameter group matches the engine + engine-version.
12. KMS key (if encrypted) is accessible: `kms:Decrypt`, `kms:CreateGrant`.

**For snapshot restore (`restore-db-instance-from-db-snapshot`):**
5. Snapshot exists (`describe-db-snapshots --db-snapshot-identifier <id>`).
6. Snapshot status is `available`.
7. Target `--db-instance-identifier` does NOT already exist.
8. Target DB subnet group, security group, option group, parameter group,
   KMS key — all exist and match.

**For Aurora backtrack (`backtrack-db-cluster`):**
5. Engine is `aurora-mysql` (PostgreSQL does NOT support backtrack).
6. `BacktrackWindow` > 0 on the cluster.
7. `--backtrack-to-timestamp` is within `[now - BacktrackWindow, now]`.
8. Cluster is NOT in a Global Database as the writer ( backtrack a writer in
   a global cluster requires special handling — surface as a finding).
9. No existing backtrack in progress for the cluster.

**For S3 export (`start-export-task`):**
5. Snapshot exists and is `available`.
6. `--role-arn` trusts `rds.amazonaws.com`.
7. `--s3-bucket-name` exists and the role has `s3:PutObject` + `s3:ListBucket`.
8. KMS key (if specified) is accessible to the role.

**For S3 import (`start-import-from-s3`):**
5. Target Aurora MySQL cluster exists and is `available`.
6. Source S3 bucket is in the same region as the cluster.
7. The cluster's role has `s3:GetObject` + `s3:ListBucket` on the source.
8. The data format matches `--type` (CSV, etc.).

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI sequence
and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the source instance
  configuration.
- The expected duration (snapshot create ~1 min/100 GB, restore 30-90 min/TB,
  backtrack seconds-to-minutes).
- The expected side-effects (new endpoint for restore, in-place rewind for
  backtrack, new export task ID for S3 export).
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI, emit:
  `CONFIRM: About to <operation> on <instance/cluster/snapshot> in account
  <account> region <region>. This will <consequence>. Proceed? (yes/no)`.
  Do NOT execute until the operator confirms.
- Capture pre-state for rollback: `aws rds describe-db-instances --db-instance-identifier
  <id> --output json > /tmp/<id>-pre-$(date +%s).json`.
- Execute the CLI. Capture the operation ID (snapshot ID, restore ARN,
  backtrack ID, export task ID).
- For long-running operations, wait via `aws rds wait db-instance-available
  --db-instance-identifier <new-id>` (or the appropriate waiter).

### Step 4: Post-verification — COMPLETED

After the operation finishes, run post-verification. ALL checks must pass
for `COMPLETED`.

1. `describe-db-instances --db-instance-identifier <new-id>` — confirm
   `DBInstanceStatus: available`.
2. Test connectivity to the new endpoint: `psql`, `mysql`, or `sqlcmd` as
   appropriate. The endpoint is in the `Endpoint.Address` field.
3. Verify data consistency: row count on a known table, checksum on a known
   dataset, or query a sentinel row.
4. Verify the restore point matches the intended time (for PITR).
5. Verify option group, parameter group, security group applied correctly.
6. Surface the connection-string update step (new endpoint).
7. Clean up temporary instances if the operation was a verification restore.
8. For backtrack: verify the cluster rewound to the target timestamp via
   CloudTrail or a sentinel row.

If ANY verification fails, emit `VERDICT: ERROR` with the failure details —
do not claim COMPLETED.

## Output format (per operation)

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
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
ENDPOINT: <new endpoint if restore, "unchanged" if backtrack>
NOTES: <connection-string update, cleanup, caveats>
```

### Worked example — PITR restore

```text
OPERATION: pitr-restore
VERDICT: READY
TARGET: prod-orders-db -> prod-orders-db-pitr-2026-08-07
PRE_CHECKS:
  - [PASS] prod-orders-db DBInstanceStatus is available
  - [PASS] BackupRetentionPeriod is 7 (> 0, PITR enabled)
  - [PASS] RestoreTime 2026-08-07T10:00:00Z is within window
    [2026-07-31T00:00:00Z, 2026-08-07T10:55:00Z]
  - [PASS] Target identifier prod-orders-db-pitr-2026-08-07 does not exist
  - [PASS] DB subnet group prod-subnet-group has subnets in 3 AZs
  - [PASS] Security group sg-prod-rds exists in vpc-vpc-12345
  - [PASS] Option group default:mysql-8-0 matches engine mysql 8.0.x
  - [PASS] Parameter group prod-mysql80 matches engine mysql 8.0.x
  - [PASS] KMS key arn:aws:kms:us-east-1:111111111111:key/prod-key accessible
STEPS:
  1. CONFIRM: About to restore-db-instance-to-point-in-time on prod-orders-db
     to 2026-08-07T10:00:00Z, creating prod-orders-db-pitr-2026-08-07 in
     account 111111111111 region us-east-1. This will create a new instance
     with a new endpoint (original unchanged). Estimated duration: 60-90
     minutes. Proceed? (yes/no)
  2. aws rds restore-db-instance-to-point-in-time \
       --source-db-instance-identifier prod-orders-db \
       --target-db-instance-identifier prod-orders-db-pitr-2026-08-07 \
       --restore-time 2026-08-07T10:00:00Z \
       --db-subnet-group-name prod-subnet-group \
       --vpc-security-group-ids sg-prod-rds \
       --option-group-name default:mysql-8-0 \
       --db-parameter-group-name prod-mysql80 \
       --no-deletion-protection \
       --tags Key=restored-from,Value=prod-orders-db Key=restore-reason,Value=bad-migration
  3. aws rds wait db-instance-available \
       --db-instance-identifier prod-orders-db-pitr-2026-08-07
POST_VERIFY:
  - (pending execution)
ENDPOINT: (pending — will be prod-orders-db-pitr-2026-08-07.<random>.us-east-1.rds.amazonaws.com)
NOTES:
  - The new instance has a NEW endpoint. Update application connection strings.
  - The original prod-orders-db is unchanged and continues to bill.
  - Set --deletion-protection on the new instance once verified.
  - Plan cleanup: delete the restored instance after migration cutover.
```

### Worked example — pre-check failure

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

### Worked example — Aurora backtrack

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

## Anti-Patterns — NEVER

- NEVER execute `restore-db-instance-to-point-in-time` or
  `restore-db-instance-from-db-snapshot` without explicitly surfacing that
  a NEW instance and NEW endpoint will be created. Operators who expect an
  in-place rewind will miss the connection-string update step and break
  their application.

- NEVER attempt PITR on an instance with `BackupRetentionPeriod: 0`. There
  are no transaction logs and no recoverable window. Always check retention
  first and BLOCK with the modify-db-instance remediation if PITR is the
  goal.

- NEVER assume Aurora PostgreSQL supports Backtrack. Only Aurora MySQL
  supports Backtrack. For Aurora PostgreSQL, use PITR or fast clone.

- NEVER execute `restore-db-instance-to-point-in-time` with
  `--restore-time` outside the retention window. Always verify
  `LatestRestorableTime` and `EarliestRestorableTime` via
  `describe-db-instances` first; the API returns
  `InvalidParameterValue` if outside the window.

- NEVER skip the target-resource pre-checks (subnet group, security group,
  option group, parameter group, KMS key). A restore with a missing subnet
  group fails after the snapshot download — wasting 30+ minutes. Always
  verify all target resources exist before executing.

- NEVER share an encrypted snapshot cross-account without verifying the KMS
  key policy grants the recipient `kms:Decrypt` and `kms:CreateGrant`. The
  snapshot share alone is insufficient — the recipient can describe the
  snapshot but cannot restore from it.

- NEVER copy a snapshot cross-region without surfacing the cost. Cross-region
  copy bills $0.02/GB data transfer plus destination-region storage. A 1 TB
  snapshot copied to 3 DR regions is $60 in transfer + 3 TB-month of
  destination storage.

- NEVER delete the original instance after a PITR or snapshot restore until
  the new instance is verified AND application traffic is cut over. Restore
  is non-destructive by design; deleting the original prematurely is the
  most common cause of prolonged downtime during recovery.

- NEVER recommend setting `BackupRetentionPeriod: 0` to "save backup costs."
  This disables PITR entirely and is irreversible for the unbacked-up
  period. The cost saving is negligible; the recovery exposure is total.

- NEVER restore into the same DB subnet group with insufficient AZs. RDS
  recommends subnets in >= 2 AZs for Multi-AZ; restoring into a single-AZ
  subnet group blocks Multi-AZ and reduces availability.

- NEVER skip the post-restore verification. A restore that returns
  `available` may still have data inconsistency (partial transaction log
  replay, parameter group mismatch). Always verify with a row count,
  checksum, or sentinel query.

- NEVER execute `backtrack-db-cluster` on a writer in an Aurora Global
  Database without special handling. Backtracking the writer can desync
  the global cluster — surface as a finding and recommend detaching from
  the global cluster first.

- NEVER assume Aurora Fast Clone is free. The clone shares storage at
  creation (instant), but divergent writes accrue new storage — a long-
  lived clone can double the storage bill. Always plan clone cleanup.

- NEVER auto-execute a state-changing RDS CLI without the CONFIRM gate.
  Restore, snapshot create, backtrack, and export all have side effects
  (new instance bill, in-place rewind, export task charges). Always emit
  CONFIRM and wait.

- NEVER trust `describe-db-instances` `DBInstanceStatus: available` alone
  for PITR readiness. An instance can be `available` with retention=0
  (no automated backups). Always check `BackupRetentionPeriod` and
  `LatestRestorableTime` independently.

## Pre-flight safety checks (run before any remediation CLI)

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

## Recent AWS features (2024-2026)

- **Aurora Backtrack extended window (2024-2025):** Aurora MySQL now supports
  BacktrackWindow up to 72 hours (previously 24 hours). Configure via
  `modify-db-cluster --backtrack-window`. The backtrack cost per change
  remains ~$0.012/change (us-east-1). Aurora PostgreSQL still does NOT
  support Backtrack as of 2026.

- **RDS Multi-AZ Cluster Standby Backups (2024):** Multi-AZ cluster
  deployments (2 standbys) now run automated backups from a standby,
  eliminating the brief I/O pause during backup windows. Operators should
  verify their Multi-AZ deployment type (single-AZ, Multi-AZ instance, or
  Multi-AZ cluster) to understand backup behavior.

- **Aurora Fast Database Clone GA:** Instant clone of Aurora clusters via
  copy-on-write storage. Operators should verify clone cleanup lifecycle —
  long-lived clones double the storage bill as pages diverge.

- **S3 Export with column-level filtering (2024-2025):** `start-export-task`
  now supports `--export-only` for selective table/column export, reducing
  export time and S3 cost. Pair with Parquet output for analytics-ready
  exports.

- **RDS Blue/Green Deployments GA (2024):** Blue/Green deployments create a
  staging environment (Green) that mirrors production (Blue) for zero-
  downtime switches. Operators should use Blue/Green for schema changes
  instead of in-place restores — Backtrack and PITR remain the recovery
  path for failed Blue/Green switches.

- **Aurora Serverless v2 scaling improvements (2024-2025):** Serverless v2
  now supports backup configuration identical to provisioned Aurora. PITR
  and Backtrack are fully supported on Serverless v2 clusters.

- **Cross-account snapshot automation via AWS Backup (2025):** AWS Backup
  now supports cross-account snapshot management for RDS, simplifying the
  KMS key policy coordination that previously made cross-account restore
  error-prone.

## Domain

AWS CloudOps / RDS & Aurora Backup, Restore & Disaster Recovery.

## AWS documentation

- **Amazon RDS User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html
- **Amazon Aurora User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html
- **Backing up and restoring** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_CommonTasks.BackupRestore.html
- **Aurora Backtrack** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Managing.Backtrack.html
- **Point-in-time recovery** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html
- **Amazon RDS Security** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/UsingWithRDS.html
- **AWS CLI Command Reference: rds** — https://docs.aws.amazon.com/cli/latest/reference/rds/
- **RDS Blue/Green Deployments** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments.html
- **Aurora Fast Database Clone** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.FastClone.html
