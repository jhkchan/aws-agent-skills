---
name: rds-snapshot-operator
description: Operates Amazon RDS and Aurora snapshot workflows end-to-end — automated backup retention (1-35 days) and the PITR window, manual snapshot creation (pre-upgrade, compliance, audit), snapshot copy to DR regions (cross-region KMS re-encryption), point-in-time recovery at 5-minute granularity, cross-account snapshot sharing via DBSnapshotAttribute, snapshot restore (new instance vs Aurora clone), snapshot lifecycle automation (delete old via Lambda/EventBridge), Aurora backtrack vs snapshot restore, Aurora clone from snapshot (instant copy-on-write), Blue/Green deploy with snapshot pre-flight, snapshot export to S3 (Parquet via ExportTask), snapshot size monitoring, and multi-AZ snapshot behavior. Runs deterministic pre-checks (instance state, storage type, option group compatibility, KMS key, IAM export role) behind a CONFIRM gate and emits OPERATION_COMPLETED or REVIEW_REQUIRED per operation. Use when creating pre-upgrade snapshots, configuring DR snapshot copies, restoring to a point in time, sharing...
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws rds create-db-snapshot, copy-db-snapshot, delete-db-snapshot, describe-db-snapshots, modify-db-instance --backup-retention-period, restore-db-instance-to-point-in-time, restore-db-cluster-to-point-in-time, create-db-cluster-from-snapshot, share-db-snapshot, start-export-task, aws lambda, aws events (AWS CLI v2, SSO or key-based...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPERATION_COMPLETED | REVIEW_REQUIRED
  when_to_use: Creating a manual snapshot before an upgrade or maintenance window, changing automated backup retention (1-35 days), copying snapshots to a DR region, restoring to a point in time (5-minute granularity), sharing a snapshot cross-account, cloning an Aurora cluster from a snapshot, exporting snapshot data to S3 in Parquet format, automating snapshot lifecycle cleanup, or running a Blue/Green deploy with a snapshot pre-flight.
  activation_triggers: create RDS snapshot, manual snapshot before upgrade, change backup retention, PITR restore, point-in-time recovery, copy snapshot to DR region, cross-region snapshot copy, share snapshot cross-account, restore from snapshot, Aurora clone from snapshot, Aurora backtrack, export snapshot to S3, snapshot lifecycle cleanup, delete old snapshots, Blue/Green deploy snapshot, snapshot size monitoring
  invocation_schema: 'Input: either (a) an RDS instance/cluster configuration (describe-db- instance output) plus the intended operation (create-snapshot, copy-snapshot, restore-pitr, share-snapshot, clone-from-snapshot, export-snapshot, delete-snapshot, update-retention), OR (b) an instance/cluster identifier + operation for live-account execution. Output: deterministic OPERATION / VERDICT / PRE_CHECKS / STEPS / POST_VERIFY / NOTES block per snapshot operation, where VERDICT is OPERATION_COMPLETED or REVIEW_REQUIRED.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: RDS snapshot, manual snapshot, automated backup, backup retention, PITR, point-in-time recovery, snapshot copy, cross-region snapshot, DR snapshot, snapshot sharing, cross-account snapshot, snapshot restore, Aurora clone, Aurora backtrack, Blue/Green deploy, snapshot export, S3 export Parquet, snapshot lifecycle, EventBridge snapshot, KMS re-encryption, DBSnapshotAttribute
  tags: aws, rds, aurora, database, snapshot, backup, recovery, dr, compliance, operate
---

# RDS Snapshot Operator

## What this skill does

Executes RDS and Aurora snapshot operations correctly and safely. Runs
deterministic pre-checks before any state-changing CLI (instance state,
storage type, option group and parameter group compatibility, KMS key
availability, IAM export role permissions, snapshot age for lifecycle
deletion), executes the operation behind a CONFIRM gate, and verifies the
result by confirming the snapshot reached `available` status and the
target resource is accessible. Every create-snapshot operation produces a
size estimate and completion-time expectation; every restore operation
surfaces the instance-class mismatch and SG/option-group caveats so the
operator knows what to adjust post-restore.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds + pre-check priority | Before any operation |
| **§ Mindset** | Automated backup = PITR window, manual snapshots persist, Aurora clone is instant | Understanding the safety model |
| **§ Pre-flight** | Instance/cluster metadata gate — state, storage, KMS, option group | Before executing any CLI |
| **§ Process** | Per-operation planning: create, copy, restore, share, clone, export, delete, retention | When choosing which operation to run |
| **§ Output format** | Structured OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY template | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that lose data or break restores | Review before risky operations |
| **§ Pre-flight safety** | Capture pre-state, snapshot verification, KMS policy | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPERATION_COMPLETED` | Snapshot operation finished and post-verification passed (snapshot `available`, restore instance `available`, export task `complete`, copy reached source region) | Emit verification results, monitoring plan |
| `REVIEW_REQUIRED` | Operation plan is ready but requires human review before execution (PITR restore creates new instance, cross-region copy needs KMS re-encryption review, lifecycle deletion of compliance-hold snapshots, Blue/Green deploy pre-flight) | Emit plan with the specific items to review, wait for operator approval |

**Priority order for pre-checks (apply in this sequence):**

1. **Instance/cluster reachability** — target exists, `available` or
   `backing-up` (for create-snapshot), NOT `deleting` or `failed`.
2. **Storage type compatibility** — for `io1`/`io2` volumes, IOPS must be
   provisioned on restore; for `gp3`, throughput settings carry over.
3. **Option group compatibility** — restore creates a new instance with the
   DEFAULT option group unless explicitly specified; custom option groups
   (TDE, SSL, OEM) must be provided or the restore fails or data is
   unreadable.
4. **KMS key** — encrypted instances require the KMS key to be available in
   both source and target regions (cross-region copy re-encrypts with a
   target-region key).
5. **Network reachability** — restore creates a new instance with a DEFAULT
   security group unless VPC security groups are specified.
6. **Snapshot retention** — automated backups (PITR) are deleted with the
   instance; manual snapshots persist until explicitly deleted.

**Cost/time baselines (2026):**

- Manual snapshot creation: varies by storage size. 100 GB: ~2-5 minutes.
  1 TB: ~15-30 minutes. Snapshot is incremental at the storage layer but
  the API call returns immediately; `Status: creating` -> `available`.
- Cross-region copy: 100 GB: ~10-30 minutes (depends on inter-region
  bandwidth). 1 TB: ~1-3 hours.
- PITR restore: creates a new instance; duration proportional to the
  allocated storage. 500 GB: ~20-45 minutes. Aurora: faster due to
  distributed storage.
- Aurora clone from snapshot: near-instant (seconds) because Aurora clones
  use copy-on-write at the storage layer — no data copy.
- S3 export (Parquet): 100 GB: ~30-60 minutes. Charged per GB exported.
- Snapshot storage cost: $0.095/GB-month for manual snapshots (us-east-1).

## Mindset

**One-line takeaway:** Automated backup retention (1-35 days) defines the
PITR window; manual snapshots persist beyond instance deletion and are the
compliance baseline. Aurora clones are instant (copy-on-write). Driven by
three RDS realities:

- **Automated backups are ephemeral; manual snapshots are permanent.**
  Setting `BackupRetentionPeriod: 7` means RDS retains 7 days of
  transaction logs for PITR. Delete the instance and the automated
  backups are gone. Manual snapshots (`create-db-snapshot`) persist
  indefinitely until explicitly deleted — they are the compliance and DR
  baseline. A common mistake is relying solely on automated backups for
  DR; the instance is deleted, and there is no recovery point.

- **Aurora clone from snapshot is instant; RDS restore is not.** Aurora's
  distributed storage layer supports copy-on-write clones — a new cluster
  from a snapshot takes seconds, not hours, regardless of data size. RDS
  (non-Aurora) restore copies the full backup to a new EBS volume,
  proportional to allocated storage. Knowing which engine is in use
  determines the time estimate and whether the operation can be done
  in-window.

- **PITR granularity is 5 minutes for RDS, 1 second for Aurora.** RDS
  records transaction logs every 5 minutes; Aurora uses a continuous
  backup stream. When a user says "restore to 2:47 PM," Aurora can do it
  to the second; RDS rounds to the nearest 5-minute boundary. This is
  critical for recovery objectives and must be surfaced in the plan.

## Pre-flight: instance/cluster metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `describe-db-snapshots` paginates at 100/page — drain
`--starting-token` to completion. `describe-db-instances` paginates at
100/page.

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

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Instance/cluster configuration
is not valid JSON or is missing required fields — cannot plan.` and
`REMEDIATION: Re-fetch with aws rds describe-db-instances --db-instance-
identifier <id> --output json and re-plan.`

| Instance attribute | Effect on operation |
|---|---|
| `DBInstanceStatus: deleting` | Instance is being deleted. All snapshot operations BLOCKED except describe. |
| `DBInstanceStatus: modifying` | Instance is being modified. create-snapshot BLOCKED until modification completes. |
| `DeletionProtection: true` | delete-snapshot still works (protection is on the instance, not snapshots); deleting the INSTANCE is blocked. |
| `BackupRetentionPeriod: 0` | Automated backups disabled. No PITR. Manual snapshots still work. Restore-to-point-in-time BLOCKED. |
| `Encrypted: true` | Cross-region copy requires a target-region KMS key. Cross-account sharing requires the target account's KMS key to be shared or re-encrypted. |
| `MultiAZ: true` | Snapshots are taken from the standby AZ to minimize performance impact on the primary. |
| `Engine: aurora-mysql` or `aurora-postgresql` | Use cluster-level APIs (`create-db-cluster-snapshot`, `restore-db-cluster-to-point-in-time`), not instance-level. Clones are instant. |
| `StorageType: io1` | Restore requires specifying IOPS; snapshot does not capture provisioned IOPS for non-Aurora. |
| `LatestRestorableTime: null` | Automated backups not yet available or `BackupRetentionPeriod: 0`. PITR BLOCKED. |
| `AllocatedStorage` large (> 1 TB) | Snapshot creation and restore take 30+ minutes. Plan for maintenance window. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious RDS snapshot behaviors

These behaviors are easy to misjudge without operational RDS experience.
Each changes a plan if ignored:

- **Automated backup retention defines the PITR window.** Setting
  `BackupRetentionPeriod: 7` means RDS retains 7 days of transaction logs
  (5-minute snapshots + continuous logs). PITR can restore to any point
  within that window. Setting retention to 0 disables automated backups
  entirely and deletes all existing automated backups — PITR is lost. When
  increasing retention from 1 to 35, RDS does NOT backfill logs for the
  new period; the extended window starts from the change time forward.

- **Manual snapshots persist beyond instance deletion.** This is the most
  important RDS backup behavior. Deleting an RDS instance with
  `--skip-final-snapshot` also deletes automated backups. Manual snapshots
  (`create-db-snapshot`) are independent objects that survive instance
  deletion. For DR and compliance, always create a manual snapshot before
  deleting an instance, even if `DeletionProtection: true` is set.

- **Aurora clone from snapshot is instant (copy-on-write).** Aurora's
  distributed storage layer supports clone-on-write: a new cluster from a
  snapshot takes seconds regardless of data size. The clone shares storage
  with the source snapshot at the page level; writes allocate new pages.
  This is fundamentally different from RDS (non-Aurora) restore, which
  copies the entire backup to new EBS volumes.

- **PITR granularity is 5 minutes for RDS, sub-second for Aurora.** RDS
  records transaction logs every 5 minutes; `LatestRestorableTime` shows
  the most recent restorable point. Aurora's continuous backup stream
  supports second-level granularity. When a user requests "restore to
  2:47:32 PM," Aurora can honor the exact second; RDS rounds to the
  nearest 5-minute boundary.

- **Cross-region snapshot copy re-encrypts with a target-region KMS key.**
  You cannot copy an encrypted snapshot to another region using the same
  KMS key — KMS keys are region-scoped. The copy operation must specify a
  KMS key in the target region. The source key must allow the target
  account to `kms:Decrypt` (for cross-account source snapshots).

- **Cross-account snapshot sharing requires `share-db-snapshot`.** Use
  `modify-db-snapshot-attribute --attribute-name restore --values-to-add
  <target-account-id>` to share a snapshot. The target account can then
  `copy-db-snapshot` or `restore-db-instance-from-db-snapshot`. For
  encrypted snapshots, the KMS key must also be shared via a key policy
  grant.

- **Restore always creates a NEW instance/cluster.** RDS restore does NOT
  overwrite the original instance. PITR restore creates a new instance
  with a new endpoint. The operator must update connection strings,
  security groups, and parameter groups. This is why the verdict is
  REVIEW_REQUIRED for restore operations — the post-restore cutover needs
  human attention.

- **Option groups do not carry over on restore.** The restored instance
  uses the DEFAULT option group unless `--option-group-name` is specified.
  If the source used TDE, SSL, or other options, the restored data is
  unreadable or inaccessible without the correct option group. Always
  specify the option group explicitly on restore.

- **Snapshot is incremental at the storage layer but billed at full
  allocated storage.** RDS snapshots are incremental (only changed blocks
  are stored), but manual snapshot billing is based on the FULL allocated
  storage of the source instance at snapshot time, NOT the incremental
  delta. A 1 TB instance costs $95/month for each manual snapshot
  regardless of how much data changed.

- **Aurora backtrack is NOT a snapshot restore.** Aurora backtrack rewinds
  the cluster in-place to a target time within the backtrack window (up to
  72 hours). It does NOT create a new cluster and does NOT require a
  snapshot. Use backtrack for rapid rollback of logical errors (e.g.,
  accidental DELETE). Use snapshot restore for DR or cross-region recovery.

- **Blue/Green deploy uses snapshots as safety net.** Before a Blue/Green
  deploy switch, create a manual snapshot of the source instance. If the
  green environment has issues post-switch, the snapshot enables a
  rollback path. The snapshot is the pre-deploy recovery point.

- **Snapshot export to S3 uses an async ExportTask.** `start-export-task`
  exports a snapshot to S3 in Parquet format. The task runs asynchronously
  (30-60 minutes for 100 GB). The IAM role needs `s3:PutObject` on the
  target bucket and `kms:Decrypt` on the source snapshot's KMS key. The
  export preserves table structure as Parquet columns.

- **Delete-old-snapshot lifecycle automation uses EventBridge + Lambda.**
  Create a Lambda function that lists manual snapshots older than N days
  and deletes them via `delete-db-snapshot`. Trigger via EventBridge
  schedule (e.g., `rate(1 day)`). Tag compliance-hold snapshots with
  `DoNotDelete: true` and have the Lambda skip them.

- **`--final-db-snapshot-identifier` on instance deletion is mandatory
  unless `--skip-final-snapshot`.** Deleting an instance without a final
  snapshot is irreversible — all data is lost. Always use
  `--final-db-snapshot-identifier` for production instances. The final
  snapshot is a manual snapshot that persists indefinitely.

- **Snapshot copy can be automated via AWS Backup or DLM.** For
  cross-region DR, Data Lifecycle Manager (DLM) or AWS Backup can automate
  snapshot creation and cross-region copy on a schedule. DLM policies
  target EBS-backed RDS instances; AWS Backup supports both RDS and
  Aurora.

- **`DeletionProtection` blocks instance deletion, NOT snapshot
  deletion.** You can delete a manual snapshot of a
  `DeletionProtection: true` instance. The protection prevents the
  INSTANCE from being deleted (and thus losing automated backups). Always
  set DeletionProtection on production instances to prevent accidental
  data loss.

### Step 1: Pre-check gate — REVIEW_REQUIRED if any check needs human attention

Run ALL pre-checks for the chosen operation. If any check requires human
review (not a hard BLOCK), the verdict is REVIEW_REQUIRED with the review
items listed.

**For ALL operations:**
1. Instance/cluster exists (`describe-db-instances` does not return
   `DBInstanceNotFoundFault`).
2. Instance is NOT in `deleting` or `failed` state.
3. KMS key (if encrypted) is `Enabled`.

**For create-snapshot (`create-db-snapshot` / `create-db-cluster-snapshot`):**
4. Instance is in `available` or `backing-up` state (creating a manual
   snapshot during `backing-up` queues it).
5. No manual snapshot with the same identifier already exists.
6. For Aurora: use `create-db-cluster-snapshot`, NOT the instance-level
   API.

**For copy-snapshot (`copy-db-snapshot`):**
4. Source snapshot is `available`.
5. For cross-region: target region KMS key specified and `Enabled`.
6. For cross-account source: the sharing account has called
   `modify-db-snapshot-attribute --attribute-name restore --values-to-add
   <account-id>` and the KMS key policy grants `kms:Decrypt`.

**For restore-pitr (`restore-db-instance-to-point-in-time`):**
4. `BackupRetentionPeriod >= 1` (automated backups enabled).
5. `LatestRestorableTime` is not null.
6. Target restore time is within `[EarliestRestorableTime,
   LatestRestorableTime]`.
7. Option group specified (review needed if source uses custom options).
8. Security groups specified (review needed if VPC topology changed).
9. Verdict is REVIEW_REQUIRED (creates a new instance with a new endpoint).

**For clone-from-snapshot (Aurora only):**
4. Source snapshot is a cluster snapshot (`DBClusterSnapshot`), not an
   instance snapshot.
5. Engine is `aurora-mysql` or `aurora-postgresql`.
6. Clone is near-instant (copy-on-write); size is not a time factor.

**For share-snapshot (`modify-db-snapshot-attribute`):**
4. Snapshot is `available`.
5. For encrypted snapshots: KMS key policy grants target account
   `kms:CreateGrant` and `kms:Decrypt`.
6. Target account ID is valid (12 digits).

**For export-snapshot (`start-export-task`):**
4. Snapshot is `available`.
5. S3 bucket exists and the IAM role has `s3:PutObject` on the bucket ARN.
6. IAM role trust policy allows `export.rds.amazonaws.com`.
7. KMS key for export (if specified) is `Enabled`.

**For delete-snapshot (`delete-db-snapshot`):**
4. Snapshot is `available` (cannot delete while `creating` or `copying`).
5. Snapshot is NOT tagged `DoNotDelete: true` (compliance hold).
6. For automated lifecycle: confirm the snapshot is beyond the retention
   window.
7. Verdict is REVIEW_REQUIRED for compliance-hold or audit-sensitive
   snapshots.

**For update-retention (`modify-db-instance --backup-retention-period`):**
4. New retention is in [1, 35].
5. If decreasing retention: confirm no compliance requirement for the
   longer window.
6. If increasing retention: note that RDS does NOT backfill logs for the
   new period.

### Step 2: OPERATION_COMPLETED or REVIEW_REQUIRED — emit operation plan

If all pre-checks pass and the operation is straightforward (create,
copy, clone, export, share), emit `VERDICT: OPERATION_COMPLETED` (for
already-executed verification scenarios) or the plan leading to
completion. For operations requiring human review (restore-pitr,
delete-snapshot with compliance concerns, Blue/Green pre-flight), emit
`VERDICT: REVIEW_REQUIRED` with the specific items to review.

The plan includes:
- The exact AWS CLI command with all flags populated from the instance
  configuration.
- The expected duration (snapshot: 2-30 minutes depending on size; Aurora
  clone: seconds; PITR restore: 20-45 minutes; export: 30-60 minutes).
- The expected side-effects (new snapshot in `available`, new instance in
  `available`, S3 objects in Parquet format).
- The CONFIRM gate prompt.
- The monitoring step (describe-db-snapshots to watch status transition).

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI
  (`create-db-snapshot`, `copy-db-snapshot`, `delete-db-snapshot`,
  `restore-db-instance-to-point-in-time`,
  `restore-db-cluster-to-point-in-time`,
  `create-db-cluster-from-snapshot`, `start-export-task`,
  `modify-db-snapshot-attribute`, `modify-db-instance
  --backup-retention-period`), emit:
  `CONFIRM: About to <operation> on <instance/cluster/snapshot> in
  account <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.
- Capture pre-state: `aws rds describe-db-instances --db-instance-
  identifier <id> --output json > /tmp/<id>-pre-$(date +%s).json`.
- Execute the CLI. For snapshot creation, the API returns immediately;
  the snapshot transitions `creating` -> `available`.
- Monitor: `aws rds describe-db-snapshots --db-snapshot-identifier <snap>
  --query 'DBSnapshots[0].Status'`.

### Step 4: Post-verification — OPERATION_COMPLETED

After the operation finishes, run post-verification. ALL checks must pass
for `OPERATION_COMPLETED`.

1. `describe-db-snapshots --db-snapshot-identifier <snap>` — confirm
   `Status: available`.
2. For restore: `describe-db-instances --db-instance-identifier <new-id>`
   — confirm `DBInstanceStatus: available`.
3. For copy: confirm the snapshot appears in the target region
   (`describe-db-snapshots --region <target-region>`).
4. For export: `describe-export-tasks --export-task-identifier <task>` —
   confirm `Status: COMPLETE` and S3 objects exist.
5. For share: target account confirms visibility via
   `describe-db-snapshots --include-shared --snapshot-type shared`.
6. For clone (Aurora): `describe-db-clusters --db-cluster-identifier
  <new-cluster>` — confirm `Status: available`.

If ANY verification fails, emit `VERDICT: ERROR` with the failure details
— do not claim OPERATION_COMPLETED.

## Output format (per operation)

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
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
NOTES: <schedule, monitoring, caveats>
```

### Worked example — create-snapshot (pre-upgrade)

```text
OPERATION: create-snapshot
VERDICT: OPERATION_COMPLETED
TARGET: prod-orders-db (snapshot: prod-orders-db-pre-upgrade-20260805)
PRE_CHECKS:
  - [PASS] Instance prod-orders-db exists, Status: available
  - [PASS] No existing snapshot with identifier
    prod-orders-db-pre-upgrade-20260805
  - [PASS] AllocatedStorage: 500 GB (estimated snapshot time: 10-20 min)
  - [PASS] Encrypted: true, KMS key
    arn:aws:kms:us-east-1:111111111111:key/orders-cmk Enabled
STEPS:
  1. CONFIRM: About to create manual snapshot
     prod-orders-db-pre-upgrade-20260805 on instance prod-orders-db in
     account 111111111111 region us-east-1. This will take ~10-20 minutes.
     Proceed? (yes/no)
  2. aws rds create-db-snapshot \
       --db-instance-identifier prod-orders-db \
       --db-snapshot-identifier prod-orders-db-pre-upgrade-20260805
  3. aws rds describe-db-snapshots \
       --db-snapshot-identifier prod-orders-db-pre-upgrade-20260805 \
       --query 'DBSnapshots[0].Status'
POST_VERIFY:
  - [PASS] Snapshot Status: available
  - [PASS] Snapshot Encrypted: true (KMS key matches source)
  - [PASS] AllocatedStorage: 500 GB (matches source)
NOTES:
  - This snapshot is the pre-upgrade recovery point. If the upgrade
    fails, restore from this snapshot:
    aws rds restore-db-instance-from-db-snapshot \
      --db-instance-identifier prod-orders-db-restored \
      --db-snapshot-identifier prod-orders-db-pre-upgrade-20260805 \
      --db-instance-class db.r6g.xlarge \
      --option-group-name prod-orders-options \
      --vpc-security-group-ids sg-prod-rds
  - Manual snapshots persist beyond instance deletion. Tag this
    snapshot: aws rds add-tags-to-resource \
      --resource-name arn:aws:rds:us-east-1:111111111111:snapshot:prod-orders-db-pre-upgrade-20260805 \
      --tags Key=DoNotDelete,Value=true Key=Purpose,Value=pre-upgrade
```

### Worked example — Aurora clone from snapshot

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

### Worked example — PITR restore (REVIEW_REQUIRED)

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

### Worked example — cross-region copy (DR)

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

### Worked example — snapshot lifecycle cleanup

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

## Anti-Patterns — NEVER

- NEVER delete an RDS instance without a final snapshot
  (`--skip-final-snapshot`) in production environments. Manual snapshots
  persist beyond deletion; automated backups do not. The final snapshot
  is the last-chance recovery point.

- NEVER assume automated backups replace manual snapshots for DR. Setting
  `BackupRetentionPeriod: 35` gives you a 35-day PITR window, but deleting
  the instance destroys ALL automated backups. Manual snapshots are the
  only snapshot type that survives instance deletion.

- NEVER restore a PITR or snapshot without specifying the option group.
  The DEFAULT option group does not include TDE, SSL, OEM, or other
  custom options. The restored data may be unreadable (TDE) or
  inaccessible (SSL) without the correct option group.

- NEVER assume PITR granularity is better than 5 minutes for RDS
  (non-Aurora). RDS transaction logs are 5-minute snapshots. Aurora
  supports second-level granularity. If the recovery objective requires
  sub-5-minute precision, the engine must be Aurora.

- NEVER confuse Aurora backtrack with snapshot restore. Backtrack rewinds
  the cluster in-place within the backtrack window (up to 72 hours).
  Snapshot restore creates a NEW cluster. Use backtrack for rapid logical
  rollback; use snapshot restore for DR and cross-region recovery.

- NEVER copy an encrypted snapshot cross-region without specifying a
  target-region KMS key. KMS keys are region-scoped; the copy fails
  without a target key. The source key cannot be referenced from another
  region.

- NEVER assume `DeletionProtection: true` protects snapshots. It protects
  the INSTANCE from deletion (and thus preserves automated backups).
  Manual snapshots can still be deleted with `delete-db-snapshot` even
  if the source instance has DeletionProtection.

- NEVER share an encrypted snapshot cross-account without also sharing the
  KMS key. The target account cannot decrypt the snapshot without
  `kms:Decrypt` on the source key. Use a key policy grant or KMS grants.

- NEVER set `BackupRetentionPeriod: 0` on a production instance. This
  disables ALL automated backups and immediately deletes existing
  transaction logs. PITR is permanently lost. There is no confirmation
  prompt — the setting takes effect immediately.

- NEVER assume a snapshot is small because the database is small. RDS
  snapshot billing is based on ALLOCATED storage, not used storage. A
  1 TB EBS volume with 10 GB of data costs the same to snapshot as a
  full 1 TB.

- NEVER skip the CONFIRM gate for `delete-db-snapshot`. Snapshot deletion
  is irreversible. There is no recycle bin or version history. Verify the
  snapshot is not compliance-hold or part of a DR plan before confirming.

- NEVER assume increasing `BackupRetentionPeriod` backfills historical
  logs. Changing from 7 to 35 days starts retaining 35 days FROM THE
  CHANGE TIME FORWARD. The previous 7-day window is not extended
  retroactively.

- NEVER use instance-level APIs for Aurora clusters. Aurora uses cluster-
  level APIs (`create-db-cluster-snapshot`, `restore-db-cluster-to-point-
  in-time`, `restore-db-cluster-from-snapshot`). Instance-level APIs
  fail or create inconsistent state.

- NEVER export a snapshot to S3 without verifying the IAM role trust
  policy. The export service (`export.rds.amazonaws.com`) must be in the
  trust policy, or the export task fails immediately with
  `AccessDeniedException`.

- NEVER assume Aurora clone takes the same time as RDS restore. Aurora
  clones are instant (copy-on-write at the storage layer). RDS restores
  are proportional to allocated storage. Knowing the engine determines
  whether a maintenance window is needed.

- NEVER run a Blue/Green deploy without a pre-deploy manual snapshot.
  The snapshot is the rollback path if the green environment has issues
  post-switch. Without it, rollback requires PITR (5-minute granularity
  for RDS, with potential data loss).

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

## Recent AWS features (2024-2026)

- **Aurora clone from snapshot optimization (2024-2025):** Aurora's
  copy-on-write clone mechanism now supports cross-account clones within
  the same region. The source account shares the snapshot; the target
  account clones. Storage is shared at the page level.

- **Blue/Green Deployments GA (2024):** RDS Blue/Green Deployments create
  a staging environment that mirrors production. The switch is near-zero-
  downtime. Always create a pre-deploy snapshot as the rollback recovery
  point. The Blue/Green switch itself does not create snapshots.

- **RDS Snapshot Export to S3 with column-level filtering (2024-2025):**
  The `start-export-task` API now supports exporting specific tables or
  columns via the `ExportOnly` parameter (list of
  `database.schema.table` patterns). Useful for compliance exports that
  only need specific tables.

- **Automated backup retention up to 35 days (2024):** RDS
  `BackupRetentionPeriod` supports up to 35 days (previously 35 was the
  max for Aurora; RDS was 35). Aurora supports up to 35 days of PITR with
  continuous backup.

- **Aurora backtrack window up to 72 hours (2024-2025):** Aurora MySQL
  and PostgreSQL support backtrack windows up to 72 hours. Backtrack
  rewinds the cluster in-place without creating a new cluster. Use for
  rapid logical rollback (e.g., accidental DELETE/DROP).

- **AWS Backup integration with RDS (2024-2025):** AWS Backup now
  supports RDS cross-region copy and cross-account backup vaults. Use
  AWS Backup for centralized backup governance across RDS, Aurora, and
  other AWS services.

- **Snapshot export in columnar Parquet with compression (2025):** The
  export task now supports Snappy and ZSTD compression for Parquet
  output. ZSTD reduces output size by 30-50% compared to uncompressed
  Parquet.

- **RDS Storage Auto Scaling (2024-2025):** When Storage Auto Scaling is
  enabled, snapshots capture the current allocated storage (which may
  have auto-scaled beyond the original provisioning). Restores allocate
  the snapshot's storage size, not the original.

- **DLM cross-region copy with KMS re-encryption (2024):** Data Lifecycle
  Manager policies now support cross-region snapshot copy with automatic
  KMS re-encryption. Use DLM for automated DR snapshot pipelines without
  custom Lambda.

- **CloudWatch RUM for database performance monitoring (2025):** CloudWatch
  RUM integrates with RDS Performance Insights to correlate application
  requests with database query performance. Useful for post-restore
  validation to confirm the restored instance performs as expected.

## Domain

AWS CloudOps / RDS & Aurora Snapshot Management, Backup Retention, DR &
Compliance.

## AWS documentation

- **Amazon RDS User Guide — Backing up and restoring** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_CommonTasks.BackupRestore.html
- **Creating a DB snapshot** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CreateSnapshot.html
- **Restoring from a DB snapshot** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_RestoreFromSnapshot.html
- **Point-in-time recovery** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PIT.html
- **Copying a snapshot** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_CopySnapshot.html
- **Sharing a snapshot** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ShareSnapshot.html
- **Exporting snapshot data to Amazon S3** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ExportSnapshot.html
- **Amazon Aurora cloning** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Managing.Clone.html
- **Amazon Aurora backtrack** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Managing.Backtrack.html
- **RDS Blue/Green Deployments** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/blue-green-deployments.html
- **RDS API Reference** — https://docs.aws.amazon.com/AmazonRDS/latest/APIReference/
