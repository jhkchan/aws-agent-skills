---
name: dynamodb-backup-operator
description: Operates DynamoDB backup and restore workflows safely — on-demand backups via create-backup, point-in-time recovery (PITR) enable/verify via update-continuous-backups, AWS Backup cross-region/cross-account vault plans, restore-table-from-backup, restore-table-to-point-in-time (with selective attribute projection), and cross-region restore via export-to-S3/import-from-S3. Runs deterministic pre-checks (PITR enabled, backup AVAILABLE, target table name free, IAM permissions present, billing-mode/capacity drift), executes the operation behind a CONFIRM gate, and emits a verdict (READY | BLOCKED | COMPLETED) per operation with the exact CLI sequence, expected side-effects (new table name — must update application connection strings, no auto-scaling/streams/TTL/alarms/IAM copied), and verification commands. Use when creating on-demand backups, enabling PITR, restoring a DynamoDB table to a point in time, restoring from a backup, copying a table cross-region, or recovering from accidental data loss.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline plan classification. Live-account operations use aws dynamodb describe-table, describe-continuous-backups, describe-backup, list-backups, create-backup, update-continuous-backups, restore-table-from-backup, restore-table-to-point-in-time, export-table-to-point-in-time, import-table, and aws backup start-restore-job (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: operate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY | BLOCKED | COMPLETED
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: dynamodb, databases, backup, restore, pitr, recovery, aws-backup, disaster-recovery
  dependencies: aws-orchestrator
  keywords: DynamoDB, on-demand backup, create-backup, point-in-time recovery, PITR, continuous backups, update-continuous-backups, restore-table-from-backup, restore-table-to-point-in-time, AWS Backup, cross-region backup, cross-account backup, backup vault, export-to-S3, import-table, table recovery, disaster recovery, selective restore, partial restore
  when_to_use: Creating an on-demand DynamoDB backup, enabling or verifying PITR, restoring a DynamoDB table to a point in time, restoring from a backup, copying a table cross-region or cross-account, exporting a table to S3 for import elsewhere, recovering from accidental writes or deletes, or planning a backup/restore drill.
  activation_triggers: create DynamoDB backup, enable DynamoDB PITR, restore DynamoDB table, restore DynamoDB to point in time, PITR restore DynamoDB, restore DynamoDB from backup, copy DynamoDB table cross-region, export DynamoDB to S3, import DynamoDB from S3, DynamoDB pre-migration backup, recover DynamoDB data, DynamoDB AWS Backup plan, verify DynamoDB restore
  invocation_schema: 'Input: either (a) a DynamoDB table configuration with the intended operation (create-backup, enable-pitr, pitr-restore, snapshot- restore, export, import, aws-backup-restore), OR (b) a table-name / backup-ARN + operation for live-account execution. Output: deterministic OPERATION/VERDICT/PRE_CHECKS/STEPS/POST_VERIFY block per operation, where VERDICT is one of READY, BLOCKED, COMPLETED.'
---

# DynamoDB Backup Restore Operator

## What this skill does

Executes DynamoDB backup and restore operations correctly and safely.
Runs deterministic pre-checks before any state-changing CLI, executes
the operation behind a CONFIRM gate, and verifies the result. Every
restore produces a NEW table — the skill always surfaces the
application connection-string update step, the auto-scaling / streams /
TTL / IAM reconfiguration steps, and the cleanup plan.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **§ Quick reference** | Verdict thresholds (BLOCKED/READY/COMPLETED) + pre-check priority order | Before any operation |
| **§ Mindset** | Why PITR is required, the new-table surprise, restore does NOT copy side config | Understanding the safety model |
| **§ Pre-flight** | Table metadata gate — status, PITR, backup state, IAM, capacity mode | Before executing any CLI |
| **§ Process** | Per-operation planning: on-demand backup, enable-PITR, PITR restore, snapshot restore, cross-region, AWS Backup | When choosing which operation to run |
| **§ Output format** | Structured output template with VERDICT, COMMANDS, ENDPOINT, VERIFICATION | Formatting the response |
| **§ Anti-Patterns** | NEVER list — common mistakes that cause data loss or silent failures | Review before risky operations |
| **§ Pre-flight safety** | Additional checks before any remediation CLI | Defense-in-depth |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `BLOCKED` | One or more pre-checks failed (PITR not enabled for PITR restore, backup CREATING or missing, target table name exists, IAM permission missing, table in CREATING/DELETING) | List failures, do NOT execute |
| `READY` | All pre-checks passed; awaiting CONFIRM gate | Emit exact CLI sequence, wait for operator yes |
| `COMPLETED` | Operation finished and post-verification passed (new table ACTIVE, item count matches, side config re-applied) | Emit table ARN, verification results, cleanup steps |

**Priority order for pre-checks (apply in this sequence, all must pass
for READY):**

1. **Table status** — must be `ACTIVE` (or `UPDATING` for read-only
   operations). `CREATING`, `DELETING`, `ARCHIVING`, `INACCESSIBLE_
   ENCRYPTION_CREDENTIALS` → BLOCKED.
2. **PITR state** — `restore-table-to-point-in-time` requires
   `PointInTimeRecoveryStatus: ENABLED`. Verify via
   `describe-continuous-backups`; BLOCKED with the
   `update-continuous-backups` remediation if disabled.
3. **Backup state** — `restore-table-from-backup` requires the backup
   ARN to exist and `BackupStatus: AVAILABLE`. `CREATING` → BLOCKED with
   "wait for AVAILABLE before restore".
4. **Target table name free** — restore creates a NEW table; the target
   name must not already exist. `ResourceInUseException` otherwise.
5. **IAM permissions** — caller needs `dynamodb:CreateBackup`,
   `dynamodb:RestoreTableFromBackup`,
   `dynamodb:RestoreTableToPointInTime`, plus `kms:Decrypt`/`kms:GenerateDataKey`
   on the source table's CMK for encrypted tables.
6. **Capacity / billing mode drift awareness** — restore does NOT copy
   auto-scaling policies. Plan to re-register scalable targets +
   policies on the restored table (or switch to on-demand).

**Cost/time baselines (2026):**

- On-demand backup create time: minutes for small tables, scaling with
  table size (DynamoDB service-managed, stored within DynamoDB — NOT S3).
- Restore time: proportional to source data size; the new table is not
  ACTIVE until restore completes (status transitions RESTORING → ACTIVE).
- PITR cost: ~$0.20/GB-month for continuous-backup storage + ~$0.10/GB
  for restore data read.
- On-demand backup storage: ~$0.10/GB-month (DynamoDB service-managed).
- Export to S3: ~$0.008/GB read from DynamoDB + S3 storage of the
  exported Parquet/JSON; import from S3: ~$0.008/GB write to the new
  table + S3 GET cost.

## Mindset

**One-line takeaway:** restore always creates a NEW table with a NEW
name — the original is untouched, and the new table is missing
auto-scaling, streams, TTL, alarms, and IAM policies. Operators who
expect an in-place rewind will miss the cutover and break their
application. Driven by three DynamoDB realities:

- **PITR is REQUIRED for second-level recovery.** Without
  `PointInTimeRecoveryStatus: ENABLED`, you can only restore to the
  timestamp of an on-demand or AWS Backup snapshot. Data written and
  deleted between snapshots is unrecoverable. Enable PITR by default on
  every production table — the cost (~$0.20/GB-month) is negligible
  versus the recovery exposure.
- **Restore is non-destructive and incomplete.** `restore-table-to-
  point-in-time` and `restore-table-from-backup` create a NEW table
  that copies schema + data + GSI/LSI definitions, but does NOT copy
  auto-scaling policies, CloudWatch alarms, IAM resource policies,
  DynamoDB Streams, TTL, or tags (unless explicitly re-applied). The
  new table defaults to the source's billing mode and provisioned
  throughput settings, but autoscaling policies must be re-registered.
- **Two recovery mechanisms are NOT interchangeable.** PITR
  (continuous, 35-day window, second-level granularity) and on-demand
  / AWS Backup snapshots (point-in-time at the snapshot instant) are
  complementary. A table with snapshots but no PITR cannot recover
  data lost between snapshots.

## Pre-flight: table metadata gate

Run before classification. Misclassifying these produces wrong plans.

**Pagination:** `list-backups` paginates at 100/page — drain
`--starting-token` to completion. `describe-continuous-backups` and
`describe-table` are single-record calls (no pagination).

**Live-account pre-flight (skip if offline plan audit):**
1. `aws dynamodb describe-table --table-name <name>` — confirm
   `TableStatus: ACTIVE`. Capture `BillingModeSummary`,
   `ProvisionedThroughput`, `TableSizeBytes`, `ItemCount`,
   `SSEDescription`, `GlobalSecondaryIndexes`, `LocalSecondaryIndexes`,
   `DeletionProtectionEnabled`, `StreamSpecification`.
2. `aws dynamodb describe-continuous-backups --table-name <name>` —
   capture `ContinuousBackupsStatus` and
   `PointInTimeRecoveryStatus`. `EarliestRestorableDateTime` and
   `LatestRestorableDateTime` define the PITR window (up to 35 days).
3. `aws dynamodb list-backups --table-name <name>` — list available
   backups (filter `--backup-type USER` for on-demand only).
4. `aws dynamodb describe-backup --backup-arn <arn>` — verify a specific
   backup is `AVAILABLE` before restore.
5. `aws application-autoscaling describe-scaling-policies
   --service-namespace dynamodb --resource-ids table/<name>` — capture
   autoscaling policies that must be re-registered on the restored
   table.
6. `aws backup list-protected-resources --resource-type DynamoDB` —
   check whether AWS Backup is also protecting this table.
7. `aws dynamodb describe-time-to-live --table-name <name>` — capture
   TTL config to re-apply on the restored table.
8. `aws kms describe-key --key-id <cmk-arn>` — verify CMK access for
   encrypted-table restore (`kms:Decrypt`, `kms:GenerateDataKey`,
   `kms:CreateGrant`).

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Table/operation
configuration is not valid JSON or is missing required fields — cannot
plan.` and `REMEDIATION: Re-fetch with aws dynamodb describe-table
--table-name <name> --output json and re-plan.`

| Table attribute | Effect on operation |
|---|---|
| `TableStatus: ACTIVE` | Pre-check passes for stateful operations. |
| `TableStatus: CREATING` | BLOCKED — wait for `ACTIVE` (table not yet readable). |
| `TableStatus: DELETING` | BLOCKED — table is being deleted. |
| `TableStatus: UPDATING` | Read-only operations OK; backup create OK if not mid-billing-mode switch. Restore-from-source OK. |
| `TableStatus: INACCESSIBLE_ENCRYPTION_CREDENTIALS` | BLOCKED — active outage (CMK inaccessible). Treat as incident; restore from a known-good backup to a new table. |
| `PointInTimeRecoveryStatus: ENABLED` | PITR restore allowed. Recovery window is `[EarliestRestorableDateTime, LatestRestorableDateTime]`. |
| `PointInTimeRecoveryStatus: DISABLED` | PITR restore BLOCKED — only on-demand/AWS Backup snapshot restore possible. |
| `DeletionProtectionEnabled: true` | Restore to a new table is allowed (does not modify the source). Deleting the source later requires disabling protection first. |
| `SSEDescription.SSEType: KMS` | Encrypted table. Restore requires CMK access in the target account/region; cross-account restore requires the source account's CMK policy grant. |
| `BillingModeSummary.BillingMode: PAY_PER_REQUEST` | Restore copies on-demand mode. New table is on-demand; no autoscaling re-registration needed. |
| `BillingModeSummary.BillingMode: PROVISIONED` | Restore copies provisioned throughput settings, but does NOT copy autoscaling policies. The new table is provisioned at the snapshot's RCU/WCU — register autoscaling targets + policies after restore. |
| `Replicas` present (Global Table) | Restoring a global-table replica is unusual; restore the primary and re-add replicas. The restore is regional — it does NOT replicate the global-table config. |
| `BackupStatus: AVAILABLE` | Restore-from-backup allowed. |
| `BackupStatus: CREATING` | Restore BLOCKED — backup not yet complete; wait via `aws dynamodb wait` or poll `describe-backup`. |
| `BackupStatus: DELETED` | Restore BLOCKED — backup no longer exists. |

## Process — operation planning (apply in order)

### Step 0: Expert knowledge — non-obvious DynamoDB backup/restore behaviors

These behaviors are easy to misjudge without operational DynamoDB
experience. Each changes a plan if ignored:

- **PITR restore recovers to any second in the 35-day window, not just
  snapshot instants.** `restore-table-to-point-in-time
  --restore-date-time <ts>` accepts any timestamp within
  `[EarliestRestorableDateTime, LatestRestorableDateTime]` with
  second-level precision. `LatestRestorableDateTime` typically lags
  real-time by a few seconds (NOT 5 minutes like RDS). On-demand
  snapshots are only needed for longer-term retention beyond 35 days.

- **Restore creates a NEW table with a NEW name.** Always. The source
  table is untouched. Operators must update application connection
  strings, IAM resource policies, CloudWatch alarms, and DNS aliases
  to point at the new table name. This is the single most common
  DynamoDB restore surprise.

- **Restore does NOT copy: autoscaling, alarms, IAM resource policies,
  Streams, TTL, tags.** The restored table inherits schema, GSI/LSI
  definitions, billing mode, and provisioned throughput from the
  snapshot/PITR source — but everything else must be reconfigured
  manually. Plan a post-restore checklist.

- **On-demand backups are stored within DynamoDB service, NOT S3.**
  `create-backup` produces a backup ARN stored and managed by DynamoDB
  (~$0.10/GB-month). For S3-based backup (analytics, cross-region,
  longer retention), use `export-table-to-point-in-time` (exports to
  S3 in Parquet/DynamoDB JSON) — that is a different feature with a
  different cost model.

- **PITR cost is charged on the change volume, not the table size.**
  DynamoDB bills PITR storage based on the bytes modified during the
  35-day window. A read-heavy table with low write volume costs very
  little in PITR. A write-heavy table can approach ~2x the data size
  in PITR storage over 35 days.

- **`restore-table-to-point-in-time` supports selective restore.** The
  optional `--sse-specification-override`, `--billing-mode-override`,
  and the new (2024-2025) selective-restore projection filter (project
  specific attributes) let you build a smaller restored table. Use
  this for partial recovery (e.g., only one partition key range).

- **Restore does NOT copy the table class.** A source table on
  `STANDARD_INFREQUENT_ACCESS` restores to `STANDARD` by default. Set
  `--table-class-override STANDARD_INFREQUENT_ACCESS` explicitly.

- **On-demand backup retention is unlimited but billed.** On-demand
  backups (created via `create-backup`) do NOT auto-expire — they
  persist until explicitly deleted via `delete-backup`. Set a
  retention reminder (tags or AWS Backup plan) to avoid perpetual
  billing.

- **Cross-region restore via AWS Backup.** AWS Backup vaults support
  cross-region copy and cross-account restore for DynamoDB. The
  source backup must be in an AWS Backup vault (not just a
  DynamoDB-managed on-demand backup). Use
  `aws backup start-restore-job` with the recovery-point ARN.

- **Cross-region restore via S3 export/import.** For tables NOT in an
  AWS Backup vault, the cross-region path is: `export-table-to-point-
  in-time` in source region → S3 bucket (with cross-region replication
  or a copy step) → `import-table` in target region. The import
  creates a new table from the S3 data.

- **GSI/LSI are recreated on restore, but their data must rebuild.**
  The restored table's GSI/LSI definitions are copied from the source,
  but the index data is rebuilt as the base-table data streams in.
  GSIs are not queryable until the rebuild completes — monitor
  `IndexStatus` transitioning to `ACTIVE`.

- **`restore-table-from-backup` with a backup ARN is the snapshot-
  style restore.** `restore-table-to-point-in-time` uses the
  continuous backup (PITR) — different code path, different CLI.
  Choose by what recovery point you need (a snapshot instant vs any
  second in the window).

- **`DeletionProtectionEnabled` on the source does NOT block restore.**
  Restore creates a new table — the source's deletion protection is
  irrelevant. However, the new table does NOT inherit
  `DeletionProtectionEnabled`; enable it post-restore if needed.

- **`export-table-to-point-in-time` requires PITR enabled on the
  source.** Even though the export target is S3, the export reads from
  the continuous-backup store. A table with `PITRStatus: DISABLED`
  cannot export.

- **`import-table` requires a fresh, empty target table definition.**
  The import creates a new table; you cannot import into an existing
  table. The S3 source must be in the same region as the import. The
  input format (DynamoDB JSON or Parquet) must match the export
  format.

- **Cross-account backup via AWS Backup requires both KMS key policy
  and backup vault policy grants.** Sharing an encrypted backup cross-
  account needs the source account's KMS key policy to grant the
  recipient `kms:Decrypt` AND the destination backup vault policy to
  accept the source account. Without both, the copy fails at the
  encryption step.

- **AWS Backup Vault Lock (compliance mode) makes backups immutable.**
  A vault in Vault Lock `COMPLIANCE` mode cannot be deleted by anyone
  (including root) until the retention period expires. This is the
  recommended posture for ransomware-resilient DynamoDB backups. Use
  `GOVERNANCE` mode for softer guardrails (deletable with
  `backup:DismissGrant`).

### Step 1: Pre-check gate — BLOCKED if any check fails

Run ALL of the following pre-checks. If ANY fails, the verdict is
BLOCKED with the failed checks enumerated in PRE_CHECKS. Do NOT execute
the operation.

**For ALL operations:**
1. `TableStatus` is `ACTIVE` (or `UPDATING` for read-only ops).
2. The operation is not already in progress (no concurrent restore to
   the same target name).
3. IAM role for the operator holds the required DynamoDB permissions.

**For on-demand backup (`create-backup`):**
4. `TableStatus: ACTIVE`.
5. Backup name (or generated name) does not already exist
   (`list-backups --backup-type USER`).

**For enable-PITR (`update-continuous-backups`):**
4. `ContinuousBackupsStatus: ENABLED` but
   `PointInTimeRecoveryStatus: DISABLED` (PITR can be toggled on).
5. Table is not in `CREATING`/`DELETING` state.

**For PITR restore (`restore-table-to-point-in-time`):**
4. `PointInTimeRecoveryStatus: ENABLED`.
5. `LatestRestorableDateTime` >= `--restore-date-time` >=
   `EarliestRestorableDateTime`.
6. Target `--target-table-name` does NOT already exist.
7. Caller holds `dynamodb:RestoreTableToPointInTime` on the source
   table ARN.
8. For encrypted tables: CMK is accessible in the target account
   (`kms:Decrypt`, `kms:GenerateDataKey`).

**For snapshot-style restore (`restore-table-from-backup`):**
4. Backup ARN exists (`describe-backup`).
5. `BackupStatus: AVAILABLE`.
6. Target `--target-table-name` does NOT already exist.
7. Caller holds `dynamodb:RestoreTableFromBackup` on the backup ARN.

**For AWS Backup restore (`backup start-restore-job`):**
4. Recovery point exists and is `COMPLETED` in the backup vault.
5. IAM role for restore has `dynamodb:CreateTable`,
   `dynamodb:RestoreTableFromBackup`, plus KMS grants.
6. Target table name is free.

**For export to S3 (`export-table-to-point-in-time`):**
4. `PointInTimeRecoveryStatus: ENABLED` (PITR required for export).
5. `--s3-bucket` exists and the export role has `s3:PutObject`,
   `s3:ListBucket`, `kms:Decrypt`/`kms:GenerateDataKey` on the
   destination KMS key.
6. `--export-time` is within the PITR window.

**For import from S3 (`import-table`):**
4. S3 source exists in the same region as the import.
5. Input format matches the export format (DynamoDB JSON or Parquet).
6. Caller has `dynamodb:CreateTable`, `s3:GetObject`, `s3:ListBucket`.

### Step 2: READY — emit operation plan

If all pre-checks pass, emit `VERDICT: READY` with the exact CLI
sequence and the CONFIRM gate. The plan includes:

- The exact AWS CLI command with all flags populated from the source
  table configuration.
- The expected duration (backup create minutes-to-hours, restore
  minutes-to-hours scaling with table size, export minutes-to-hours).
- The expected side-effects (new table name for restore, new backup ARN
  for create-backup, new export job ARN for S3 export).
- The CONFIRM gate prompt.

### Step 3: Execute behind CONFIRM gate

- **MANDATORY CONFIRMATION GATE.** Before any state-changing CLI, emit:
  `CONFIRM: About to <operation> on table <name> / backup <arn> in
  account <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.
- Capture pre-state for audit: `aws dynamodb describe-table --table-name
  <name> --output json > /tmp/<name>-pre-$(date +%s).json`.
- Execute the CLI. Capture the operation ID (backup ARN, restore table
  ARN, export job ARN, restore job ID).
- For long-running operations, poll the operation via
  `describe-table` (for restore: status RESTORING → ACTIVE),
  `describe-backup` (for create-backup: CREATING → AVAILABLE),
  `describe-export` (for export: IN_PROGRESS → COMPLETED).

### Step 4: Post-verification — COMPLETED

After the operation finishes, run post-verification. ALL checks must
pass for `COMPLETED`.

1. `describe-table --table-name <new-name>` — confirm
   `TableStatus: ACTIVE`.
2. Compare `ItemCount` (approximate) between source and restored table.
   The restored count should match the source at the restore point.
3. Run a sentinel query (`get-item` on a known key) to verify data
   integrity.
4. Verify GSI/LSI are `ACTIVE` (not `BUILDING`/`CREATING`).
5. Reconfigure what restore does NOT copy:
   - Auto-scaling policies (if PROVISIONED): `register-scalable-target`
     + `put-scaling-policy` for the table AND each GSI.
   - DynamoDB Streams: `update-table --stream-specification`.
   - TTL: `update-time-to-live`.
   - CloudWatch alarms: re-create alarms on the new table name.
   - IAM resource policies: update any inline or managed policies
     referencing the source table ARN.
   - Tags: re-apply tags (`tag-resource`).
   - `DeletionProtectionEnabled`: enable if the source had it.
6. Update application connection strings (env vars, config files,
   Secrets Manager, Parameter Store, IAM policies).
7. Clean up the temporary restored table when the cutover is verified.

If ANY verification fails, emit `VERDICT: ERROR` with the failure
details — do not claim COMPLETED.

## Output format (per operation)

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
  3. <next step>
POST_VERIFY:
  - [PASS] <verification description>
  - [FAIL] <verification description> — <reason>
TABLE_ARN: <new table ARN if restore, "unchanged" if backup-create>
NOTES: <connection-string update, side-config re-apply, cleanup, caveats>
```

### Worked example — PITR restore

```text
OPERATION: pitr-restore
VERDICT: READY
TARGET: prod-orders-table -> prod-orders-table-pitr-2026-08-09
PRE_CHECKS:
  - [PASS] prod-orders-table TableStatus is ACTIVE
  - [PASS] PointInTimeRecoveryStatus is ENABLED
  - [PASS] RestoreDateTime 2026-08-09T10:00:00Z is within window
    [2026-07-05T00:00:00Z, 2026-08-09T10:59:30Z]
  - [PASS] Target table name prod-orders-table-pitr-2026-08-09 does not exist
  - [PASS] Caller IAM role has dynamodb:RestoreTableToPointInTime
  - [PASS] CMK arn:aws:kms:us-east-1:111111111111:key/prod-key accessible
STEPS:
  1. CONFIRM: About to restore-table-to-point-in-time on prod-orders-table
     to 2026-08-09T10:00:00Z, creating prod-orders-table-pitr-2026-08-09 in
     account 111111111111 region us-east-1. This will create a NEW table
     (original unchanged). Estimated duration: 20-40 minutes for ~80 GB.
     Proceed? (yes/no)
  2. aws dynamodb restore-table-to-point-in-time \
       --source-table-name prod-orders-table \
       --target-table-name prod-orders-table-pitr-2026-08-09 \
       --restore-date-time 2026-08-09T10:00:00Z \
       --billing-mode-override PAY_PER_REQUEST
  3. Poll: aws dynamodb describe-table \
       --table-name prod-orders-table-pitr-2026-08-09 \
       --query 'Table.TableStatus'
     Wait for ACTIVE (RESTORING -> ACTIVE).
POST_VERIFY:
  - (pending execution)
TABLE_ARN: (pending — will be arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table-pitr-2026-08-09)
NOTES:
  - The new table has a NEW name. Update application connection strings.
  - Restore does NOT copy: autoscaling, CloudWatch alarms, IAM resource
    policies, DynamoDB Streams, TTL, tags, DeletionProtectionEnabled.
  - Reconfigure each of the above after restore completes.
  - The original prod-orders-table is unchanged and continues to bill.
  - Plan cleanup: delete the restored table after migration cutover.
```

### Worked example — pre-check failure (PITR disabled)

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

### Worked example — snapshot-style restore (from on-demand backup)

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

## Anti-Patterns — NEVER

- NEVER execute `restore-table-to-point-in-time` or
  `restore-table-from-backup` without explicitly surfacing that a NEW
  table with a NEW name will be created. Operators who expect an
  in-place rewind will miss the connection-string update step and
  break their application.

- NEVER attempt a PITR restore on a table with
  `PointInTimeRecoveryStatus: DISABLED`. There is no continuous
  recovery window. Always check via `describe-continuous-backups` first
  and BLOCK with the `update-continuous-backups` remediation.

- NEVER assume restore copies side configuration. Restore does NOT
  copy: auto-scaling policies, CloudWatch alarms, IAM resource
  policies, DynamoDB Streams, TTL, tags, DeletionProtectionEnabled.
  The post-restore checklist must enumerate each reconfiguration step.

- NEVER attempt `restore-table-from-backup` while `BackupStatus` is
  `CREATING`. The backup is not yet complete; restore fails. Poll
  `describe-backup` until `AVAILABLE`.

- NEVER restore to a target table name that already exists. The API
  returns `ResourceInUseException`. Always verify target name is free
  via `describe-table` first.

- NEVER confuse DynamoDB on-demand backups (stored in DynamoDB
  service) with S3 exports. `create-backup` produces a DynamoDB-managed
  backup ARN; `export-table-to-point-in-time` writes Parquet/JSON to
  your S3 bucket. They have different costs, different regions, and
  different restore paths.

- NEVER rely solely on AWS Backup snapshots for production recovery.
  AWS Backup provides scheduled snapshots (RPO = snapshot interval);
  PITR provides second-level RPO. They are complementary. A production
  table should have BOTH.

- NEVER skip the GSI/LSI rebuild check after restore. Restored indexes
  start in `CREATING`/`BUILDING` and are not queryable until `ACTIVE`.
  Verify via `describe-table --query 'Table.GlobalSecondaryIndexes'`.

- NEVER skip the `INACCESSIBLE_ENCRYPTION_CREDENTIALS` status check.
  This status means the CMK is disabled or pending deletion — every
  read/write on the table is failing. This is an active outage, not a
  backup problem. Treat as incident and restore from a known-good
  backup to a NEW table while the CMK is restored.

- NEVER delete the original table after a restore until the new table
  is verified AND application traffic is cut over. Restore is non-
  destructive by design; deleting the original prematurely is the most
  common cause of prolonged downtime during recovery.

- NEVER recommend disabling PITR to "save cost." The PITR charge
  (~$0.20/GB-month on change volume) is negligible versus the recovery
  exposure. Disabling PITR loses the entire 35-day continuous recovery
  window — irreversibly for the unbacked-up period.

- NEVER assume cross-account AWS Backup restore "just works." It needs
  BOTH the source KMS key policy grant (`kms:Decrypt` to the recipient
  account) AND the destination backup vault policy accepting the
  source account. Missing either side fails at the encryption step.

- NEVER recommend setting `BillingMode: PROVISIONED` on the restored
  table without re-registering autoscaling. Restore copies the
  provisioned throughput but NOT the autoscaling policies — the table
  is statically provisioned until you re-register scalable targets.

- NEVER execute `export-table-to-point-in-time` on a table with PITR
  disabled. Export reads from the continuous-backup store; no PITR, no
  export. Enable PITR first.

- NEVER execute `import-table` into an existing table. Import CREATES
  a new table; calling it against an existing name returns
  `ResourceInUseException`. The S3 source must be in the same region
  as the import.

- NEVER assume an on-demand backup auto-expires. On-demand backups
  persist indefinitely until `delete-backup` is called. Set a
  retention reminder or use AWS Backup plans with Vault Lock for
  compliance retention.

- NEVER auto-execute a state-changing DynamoDB CLI without the CONFIRM
  gate. Restore, backup create, and export all have side effects (new
  table bill, backup storage charge, S3 write cost). Always emit
  CONFIRM and wait.

- NEVER confuse `restore-table-from-backup` (uses a backup ARN) with
  `restore-table-to-point-in-time` (uses the continuous-backup window,
  no ARN). They are different CLI commands for different recovery
  points.

- NEVER forget that AWS Backup Vault Lock in COMPLIANCE mode is
  irrevocable. Once enabled with a retention period, no one (not even
  root) can delete backups before retention expires. This is the
  correct posture for ransomware resilience — but verify the retention
  value before locking.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-backup`, `update-continuous-backups`,
  `restore-table-from-backup`, `restore-table-to-point-in-time`,
  `export-table-to-point-in-time`, `import-table`, `delete-backup`,
  `delete-table`, `aws backup start-restore-job`), emit:
  `CONFIRM: About to <operation> on <target> in account <account>
  region <region>. This will <consequence>. Proceed? (yes/no)`. Do NOT
  execute until the operator confirms.

- **Capture pre-state for rollback.** Before restore:
  `aws dynamodb describe-table --table-name <name> --output json >
  /tmp/<name>-pre-$(date +%s).json`. DynamoDB table state is not
  versioned.

- **Verify PITR BEFORE PITR restore.**
  `PointInTimeRecoveryStatus: ENABLED` AND
  `LatestRestorableDateTime >= --restore-date-time >=
  EarliestRestorableDateTime`.

- **Verify backup BEFORE snapshot restore.** `describe-backup
  --backup-arn <arn>` returns `BackupStatus: AVAILABLE`. CREATING →
  poll until AVAILABLE.

- **Verify CMK access for encrypted restores.** Cross-account restore
  requires source KMS key policy grant. Cross-region via AWS Backup
  requires destination-region KMS key.

- **Plan connection-string cutover BEFORE restore completes.** Restore
  produces a new table name. Application config, IAM policies,
  Secrets Manager references, CloudWatch alarms must all be updated
  atomically with cutover.

- **Plan cleanup BEFORE creating temporary tables.** A verification
  restore creates a billable table. Tag it (`temp: true, delete-after:
  2026-08-16`) and schedule deletion after cutover.

- **Deletion protection.** Restored tables do NOT inherit
  `DeletionProtectionEnabled`. Enable it after verification:
  `aws dynamodb update-table --table-name <new> --deletion-protection-
  enabled`.

## Recent AWS features (2024-2026)

- **DynamoDB selective restore (2024-2025):** `restore-table-to-point-
  in-time` now supports attribute projection filters, allowing partial
  restores of specific keys/attributes. Reduces restore time and new-
  table cost when only a subset of data is needed. Verify the CLI
  version supports the `--restore-date-time` paired with the projection
  expression flags.

- **AWS Backup Vault Lock GA for DynamoDB (2024):** Vault Lock in
  COMPLIANCE mode makes DynamoDB backups immutable for the retention
  period — no one (including root) can delete early. Recommended for
  ransomware-resilient backups. Verify retention before locking.

- **Export to S3 with Parquet columnar format (2024):** Exports now
  support Parquet in addition to DynamoDB JSON, reducing S3 storage
  cost ~3-5x for large tables and enabling Athena/Glue analytics
  directly on the export.

- **Incremental export to S3 (2024-2025):** Exports now support an
  incremental mode that exports only items changed since a prior
  export, reducing export time and S3 cost for recurring backups.

- **Cross-account AWS Backup restore (2025):** AWS Backup now supports
  cross-account restore for DynamoDB, simplifying the KMS key policy
  coordination that previously made cross-account restore error-prone.

- **PITR cost visualization in AWS Cost Explorer (2024-2025):**
  DynamoDB PITR charges now broken out by table in Cost Explorer,
  making it easier to identify write-heavy tables driving PITR storage
  cost.

## Domain

AWS CloudOps / DynamoDB Backup, Restore & Disaster Recovery.

## Expert heuristic: backup cost vs table cost

DynamoDB on-demand backups are billed at ~$0.10/GB-month for the
stored backup size — separately from and in addition to the table's
own storage cost. Backup cost scales LINEARLY with both table size and
retention count, which makes long-term backup retention in DynamoDB
the #1 DynamoDB cost surprise.

**Worked example — 1 TB table, daily backups, 30-day retention:**
- Table storage (Standard): 1 TB × $0.25/GB-month = $250/month.
- 30 backups × 1 TB × $0.10/GB-month = 30 TB-month × $0.10 = **$3,000/month**.
- Backups cost 12× the table itself.

**Decision rule — when to keep backups in DynamoDB vs S3:**

| Retention | Table size | Recommendation |
|---|---|---|
| <= 35 days | Any | Use PITR ($0.20/GB-month on change volume) — no separate backup management needed |
| 35-90 days | < 100 GB | On-demand backups in DynamoDB — simplicity outweighs cost |
| 35-90 days | >= 100 GB | S3 export via `export-table-to-point-in-time` — Parquet in S3 is ~95% cheaper |
| > 90 days | Any | ALWAYS use S3 export. Move to S3 Glacier Flexible Retrieval for compliance archives |

**S3 export cost model (2026):**
- One-time export: ~$0.008/GB read from DynamoDB + S3 storage
  ($0.023/GB Standard, $0.0036/GB Glacier Flexible Retrieval).
- 1 TB exported to Glacier: $8 export + $3.60/month storage — vs
  $100/month for a single DynamoDB backup.
- Incremental export (2024+) reduces repeat-export cost by ~90%.

**Action:** when an operator asks for "more backups" or "longer
retention" on a DynamoDB table, ALWAYS compute the backup-storage cost
and surface S3 export as the alternative. A blanket "keep 30 days of
daily backups" on a 500 GB table is a $1,500/month decision.

## Edge case: PITR restore and GSI rebuild cost

`restore-table-to-point-in-time` and `restore-table-from-backup` copy
the GSI/LSI DEFINITIONS from the source — but the GSI data is rebuilt
as base-table data streams in. For large tables with many GSIs, this
creates two operational surprises:

1. **The restored table is not immediately queryable via GSIs.** Index
   status transitions `CREATING` → `BUILDING` → `ACTIVE`. Queries
   against a BUILDING GSI return stale or empty results. Monitor via
   `describe-table --query 'Table.GlobalSecondaryIndexes[*].{name:IndexName,status:IndexStatus}'`.
2. **The rebuild consumes write capacity on the restored table.** For
   PROVISIONED-mode restores, the rebuild burns the new table's
   provisioned WCU — if the operator copied the source's modest WCU,
   the rebuild takes hours-to-days. For PAY_PER_REQUEST restores, the
   rebuild bills at on-demand rates (~5x provisioned) — a 1 TB table
   with 3 GSIs can cost ~$1,000+ in rebuild write charges alone.

**Edge case — selective restore (2024+) and AWS Backup cross-region
restore may NOT recreate GSIs at all.** The selective-restore
projection filter and certain AWS Backup restore paths create the base
table only; GSI definitions must be added manually post-restore via
`update-table`. Plan for a manual GSI recreation step in the runbook.

**Diagnostic:** if a restored table appears to have no GSIs, run
`describe-table` and inspect `GlobalSecondaryIndexes`. If empty, add
each GSI manually:

```bash
aws dynamodb update-table \
  --table-name <restored-table> \
  --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk1,AttributeType=S \
  --global-secondary-index-updates '[{"Create":{"IndexName":"gsi1","KeySchema":[{"AttributeName":"pk"},{"AttributeName":"sk1"}],"Projection":{"ProjectionType":"ALL"},"ProvisionedThroughput":{"ReadCapacityUnits":10,"WriteCapacityUnits":10}}}]'
```

**Fix:** for large tables, restore with `--billing-mode-override
PAY_PER_REQUEST` to let the rebuild consume whatever capacity it
needs, then switch to PROVISIONED once GSIs are ACTIVE and autoscaling
is registered.

## AWS documentation

- **Amazon DynamoDB Developer Guide** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Welcome.html
- **DynamoDB Backup and Restore** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BackupRestore.html
- **Point-in-time recovery** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html
- **On-demand backup and restore** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/OnDemandBackup.html
- **DynamoDB export to S3** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3.html
- **DynamoDB import from S3** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataImport.html
- **AWS Backup for DynamoDB** — https://docs.aws.amazon.com/aws-backup/latest/devguide/dynamodb-backups.html
- **AWS CLI DynamoDB reference** — https://docs.aws.amazon.com/cli/latest/reference/dynamodb/
