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
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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
Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

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
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

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
Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

### Worked example — snapshot-style restore (from on-demand backup)
Moved verbatim to [references/worked-examples.md](references/worked-examples.md) - load on demand (see References below).

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
Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) - load on demand (see References below).

## Recent AWS features (2024-2026)
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (pre-check failure, snapshot restore) moved from SKILL.md
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 expert knowledge, cost heuristics, edge cases, 2024-2026 features moved from SKILL.md
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — live pre-flight + pre-remediation safety checks moved from SKILL.md
- [references/backup-restore-procedures.md](references/backup-restore-procedures.md) — canonical per-operation procedures

## Domain

AWS CloudOps / DynamoDB Backup, Restore & Disaster Recovery.

## Expert heuristic: backup cost vs table cost
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## Edge case: PITR restore and GSI rebuild cost
Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) - load on demand (see References below).

## AWS documentation

- **Amazon DynamoDB Developer Guide** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Welcome.html
- **DynamoDB Backup and Restore** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BackupRestore.html
- **Point-in-time recovery** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html
- **On-demand backup and restore** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/OnDemandBackup.html
- **DynamoDB export to S3** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3.html
- **DynamoDB import from S3** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/S3DataImport.html
- **AWS Backup for DynamoDB** — https://docs.aws.amazon.com/aws-backup/latest/devguide/dynamodb-backups.html
- **AWS CLI DynamoDB reference** — https://docs.aws.amazon.com/cli/latest/reference/dynamodb/
