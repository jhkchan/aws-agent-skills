---
name: dms-task-troubleshooter
description: >-
  Diagnoses AWS Database Migration Service (DMS) replication task
  failures through a systematic diagnostic tree covering task status
  (stopped, failed, running with errors), source connection failures
  (security group ingress, IAM trust policy, missing pglogical/MySQL
  binlog/MS-Replication/Oracle LogMiner), target connection failures
  (IAM, PK/FK constraint violations), CDC latency (memory pressure,
  disk swap, Logging disabled), full load errors (table mapping,
  data type mismatches, LOB limits), and task settings (Logging,
  validation, ParallelLoadThreads). Walks symptoms to root cause with
  describe-replication-tasks, task logs, table-statistics, and CDC
  metrics (CDCLatencySource, CDCLatencyTarget). Emits
  ROOT_CAUSE_FOUND with the specific failure layer or ESCALATE.
  Latest coverage: DMS Serverless, DMS with Babelfish, DMS Fleet
  Advisor. Use when a DMS task is stopped, failed, or showing high
  CDC latency.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Offline symptom classification works from pasted
  task status and error messages. Live-account diagnosis uses aws dms
  describe-replication-tasks, describe-replication-instances, describe-
  endpoints, describe-table-statistics, aws logs filter-log-events
  (CloudWatch Logs for dms-task-<id>), aws cloudwatch get-metric-
  statistics (DMS namespace: CDCLatencySource, CDCLatencyTarget,
  CDCChangesDiskSource, CPUUtilization, FreeableMemory), aws ec2
  describe-security-groups, aws iam get-role (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - AWS DMS
  - Database Migration Service
  - replication task
  - CDC
  - change data capture
  - full load
  - source endpoint
  - target endpoint
  - binary logging
  - binlog
  - pglogical
  - MS-Replication
  - LogMiner
  - task status failed
  - task stopped
  - CDC latency
  - memory pressure
  - disk swap
  - table mapping
  - data type mismatch
  - LOB
  - primary key
  - foreign key
  - constraint violation
  - DMS Serverless
  - Babelfish
  - DMS Fleet Advisor
  - CloudWatch Logs
  - troubleshooting
tags: [aws, dms, database-migration, rds, aurora, cdc, replication, troubleshooting]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Migration
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing a DMS replication task that is stopped, failed, or
    running with errors; walking a symptom (task failed, source
    connection test failed, CDC latency climbing, full load table-
    statistics stuck at 0 rows, target constraint violation) to the
    failed layer (source endpoint, network, IAM, target endpoint,
    schema, task settings, replication instance capacity) with verify
    and fix commands; triaging a "DMS task is failing" or "CDC lag is
    growing" page where the root cause may be source binary logging
    disabled, source SG ingress blocked, IAM role trust policy wrong,
    target PK/FK constraints, memory pressure on CDC, disk swap on
    the replication instance, table-mapping wildcards excluding
    tables, data type mismatches, or LOB size limits — not necessarily
    the DMS service itself.
  when_not_to_use: >-
    Pre-migration assessment and database inventory (use Amazon DMS
    Fleet Advisor directly, not the troubleshooter), choosing source
    and target engines (use the deploy task type for endpoint
    creation), or cost optimization of DMS resources (use the
    optimize task type). This skill diagnoses runtime task failures
    and CDC latency, not greenfield planning.
  activation_triggers:
    - "DMS task failed"
    - "DMS task stopped"
    - "DMS replication task error"
    - "DMS source connection failed"
    - "DMS target connection failed"
    - "DMS CDC latency"
    - "DMS CDC lag growing"
    - "DMS full load stuck"
    - "DMS table statistics zero rows"
    - "DMS binary logging disabled"
    - "DMS pglogical not installed"
    - "DMS constraint violation"
    - "DMS data type mismatch"
    - "DMS LOB size limit"
    - "DMS memory pressure"
    - "DMS disk swap"
    - "DMS Serverless"
    - "DMS Babelfish"
    - "DMS Fleet Advisor"
  invocation_schema: >-
    Input: either (a) a symptom description (task status failed,
    observed error message, failing table, CDC latency value), paired
    with the DMS task metadata (describe-replication-tasks, describe-
    endpoints, describe-replication-instances, table-statistics
    output), OR (b) a task ARN or name for live-account diagnosis.
    Output: a deterministic TARGET / VERDICT / REASON / LAYER /
    EVIDENCE / REMEDIATION block where VERDICT is in
    {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and LAYER is in
    {SOURCE_CONNECTION, SOURCE_BINARY_LOGGING, SOURCE_PERMISSIONS,
    TARGET_CONNECTION, TARGET_CONSTRAINTS, TARGET_PERMISSIONS,
    TASK_SETTINGS, TABLE_MAPPING, DATA_TYPE_MISMATCH, LOB_LIMIT,
    INSTANCE_CAPACITY, MEMORY_PRESSURE, DISK_SWAP, NETWORK_SG,
    IAM_ROLE, DMS_SERVICE, UNKNOWN}.
---

# DMS Task Troubleshooter

## What this skill does

Diagnoses AWS DMS replication task failures by walking a symptom (task
status failed, source connection test failed, CDC latency climbing,
full-load table-statistics stuck, target constraint violation) to the
specific failed layer using a deterministic diagnostic tree. Each layer
has a single probe (CLI command, CloudWatch metric, or CloudWatch Logs
query) that proves or disproves it. Verifies the root cause with
positive evidence — a failing probe whose output matches the symptom —
then emits a fix with verification steps. Covers source-side failures
(binary logging disabled on MySQL, pglogical extension missing on
PostgreSQL, MS-Replication not enabled on SQL Server, LogMiner not
configured on Oracle), network/IAM failures (source SG ingress,
`dms-vpc-role` / `dms-cloudwatch-logs-role` trust policy), target-side
failures (PK missing, FK constraint, unique constraint), task-level
failures (table-mapping wildcards excluding the failing table, Logging
disabled hiding the cause), data-level failures (Oracle NUMBER to
PostgreSQL NUMERIC precision loss, LOB size limit at 32KB), and
instance-capacity failures (memory pressure on CDC, disk swap on the
replication instance). Emits `ROOT_CAUSE_FOUND` with the failing layer
and fix, `NEED_MORE_INFO` when a probe needs operator input, or
`ESCALATE` for AWS-side DMS service incidents.

## Quick navigation

| If the symptom is... | Go to | First probe |
|---|---|---|
| Task status `failed` immediately at start | Step 1 | `describe-replication-tasks` LastFailureMessage + task logs |
| Task status `failed` mid-migration | Step 2 | `describe-table-statistics` (which table?) + task logs |
| Source connection test fails | Step 3a | `describe-endpoints` + `test-connection` + source SG |
| Source CDC not capturing changes (Postgres) | Step 4a | `pg_create_logical_replication_slot`, `pglogical` extension |
| Source CDC not capturing changes (MySQL) | Step 4b | `binlog_format=ROW`, `binlog_retention` |
| Source CDC not capturing changes (SQL Server) | Step 4c | MS-Replication / MS-CDC enabled |
| Target connection test fails | Step 5a | `describe-endpoints` + `test-connection` + target SG |
| Target constraint violation (FK/PK/unique) | Step 5b | task logs + target schema inspection |
| CDC latency climbing, task running | Step 6a | CloudWatch `CDCLatencySource`, `CDCLatencyTarget` |
| Memory pressure on CDC | Step 6b | CloudWatch `FreeableMemory`, `SwapUsage` |
| Full-load table-statistics stuck at 0 rows | Step 7a | `describe-table-statistics` + table-mapping rules |
| Data type mismatch error in logs | Step 7b | task logs + source/target column types |
| LOB size limit error | Step 7c | task logs + `LobMaxSize` task setting |
| Task logs missing (Logging disabled) | Step 8 | task `Logging` setting + `dms-cloudwatch-logs-role` |
| Need the source engine's CDC requirements | Reference | `references/source-cdc-requirements.md` |
| Need the task settings reference | Reference | `references/task-settings-and-logging.md` |

## Pre-flight: task metadata and gather-info gate

Before running symptom-specific probes, gather the canonical task,
endpoint, instance, and table-statistics metadata. Misidentifying the
source engine (MySQL vs PostgreSQL vs Oracle) or the migration mode
(full load vs CDC vs full load + CDC) produces false root causes.

### Account-wide pre-flight commands

```bash
# 1. Task config (status, migration type, table mappings, settings)
aws dms describe-replication-tasks \
  --filters Name=replication-task-id,Values=<task-id> --output json

# 2. Replication instance (class, engine version, multi-AZ, storage)
aws dms describe-replication-instances \
  --filters Name=replication-instance-id,Values=<inst-id> --output json

# 3. Endpoints (source and target engine type, server, port, SSL)
aws dms describe-endpoints \
  --filters Name=endpoint-arn,Values=<source-arn>,Values=<target-arn> --output json

# 4. Table statistics (per-table FullLoadRowCount, Insert/Delete/Update)
aws dms describe-table-statistics --replication-task-arn <task-arn> --output json

# 5. CloudWatch Logs for the task (the highest-signal source for errors)
aws logs filter-log-events \
  --log-group-name dms-task-<task-id> \
  --start-time $(date -u -d '-1 hour' +%s)000 \
  --filter-pattern "ERROR" --output json

# 6. CloudWatch metrics — CDC latency + instance capacity
aws cloudwatch get-metric-statistics --namespace AWS/DMS \
  --metric-name CDCLatencySource \
  --dimensions Name=ReplicationTaskIdentifier,Value=<task-id> \
  --start-time $(date -u -d '-1 hour' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
# (repeat for FreeableMemory, SwapUsage with ReplicationInstanceIdentifier)

# 7. IAM roles (dms-vpc-role, dms-cloudwatch-logs-role)
aws iam get-role --role-name dms-vpc-role --output json
aws iam get-role --role-name dms-cloudwatch-logs-role --output json

# 8. Source and target security groups (ingress rules)
aws ec2 describe-security-groups --group-ids <source-sg> <target-sg> --output json
```

### Source-engine short-circuit

| `EngineName` | CDC mechanism | Effect on diagnosis |
|---|---|---|
| `mysql` | Binary log (binlog). Requires `binlog_format=ROW`, `binlog_row_image=FULL`, and the DMS user with `REPLICATION SLAVE` + `REPLICATION CLIENT` privileges. Binlog retention must be sufficient (default 0 hours on RDS — DMS falls behind). | Check `show binary logs;`, `show variables like 'binlog%';`. RDS parameter group must set `binlog_format=ROW`. |
| `postgres` | Logical replication slot (`pglogical` or `test_decoding`). Requires `wal_level=logical`, `max_replication_slots >= 1`, and the `pglogical` extension on the source database (for Aurora/RDS PostgreSQL 9.6+). Source must have a replication slot owned by the DMS user. | Check `select * from pg_replication_slots;`, `select * from pg_extension where extname='pglogical';`. RDS parameter group must set `wal_level=logical`. |
| `sqlserver` | MS-Replication (for SQL Server 2008+) or MS-CDC (for SQL Server 2012+). Requires the database enabled for MS-Replication (`sp_replicationdboption`) or MS-CDC (`sys.sp_cdc_enable_db`), and the DMS user as `sysadmin` (MS-Replication) or `db_owner` (MS-CDC). | Check `select name, is_cdc_enabled, is_published from sys.databases;`. SQL Server Express does NOT support CDC. |
| `oracle` | LogMiner (default) or Binary Reader. Requires `ARCHIVELOG` mode, supplemental logging (`ALTER DATABASE ADD SUPPLEMENTAL LOG DATA`), and the DMS user with `SELECT ANY TRANSACTION` + `EXECUTE on DBMS_LOGMNR`. Oracle Source 12c+ needs `LOGMINING` role. | Check `select log_mode from v$database;`, `select supplemental_log_data_min from v$database;`. |
| `mariadb` | Same as MySQL (binlog). | Same as MySQL. |
| `docdb` | Change streams (not binlog). Requires `change_streams` enabled on the cluster parameter group. | Check the cluster parameter group for `change_streams: enabled`. |

### Migration-type short-circuit

| `MigrationType` | Effect on diagnosis |
|---|---|
| `full-load` | Full load only. No CDC. Failures are in the load phase (table mapping, data type, LOB, target constraints). Source binary logging is NOT required. |
| `cdc` | CDC only (no initial full load). Source MUST have the CDC mechanism enabled (binlog / pglogical / MS-CDC / LogMiner) BEFORE the task starts. Failures are typically source-CDC-configuration issues. |
| `full-load-and-cdc` | Full load followed by CDC. The most common migration type. Full-load failures show in table-statistics; CDC failures show as `CDCLatencySource` climbing after the full load completes. |

If the input is malformed (missing task ARN, missing source engine type,
ambiguous error message), emit:

```text
TARGET: <task-arn or unknown>
VERDICT: NEED_MORE_INFO
REASON: Input is missing required context — at minimum the DMS task
  ARN or ID, the source and target engine types, and the observed
  symptom (task failed, CDC latency, full-load stuck). Cannot drive a
  diagnostic tree without the error layer.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the DMS task ID or ARN,
  (2) the source and target engine types (mysql, postgres, sqlserver,
  oracle, docdb), (3) the observed symptom (task status, error message
  from task logs, CDC latency value), and (4) for live diagnosis, the
  time window of the failure.
```

## Process — Diagnostic decision tree (apply in symptom order)

### Step 0: Expert knowledge — non-obvious DMS behaviors

These behaviors are easy to misjudge without operational DMS experience.
Each changes a diagnosis if ignored:

- **`LastFailureMessage` is the starting point, not the root cause.**
  The task's `LastFailureMessage` is a high-level signal ("Task was
  suspended"). The actual error is in CloudWatch Logs near the failure
  timestamp. Always pull task logs (`aws logs filter-log-events`) before
  diagnosing — the logs contain the engine-specific error that
  `LastFailureMessage` omits.

- **RDS MySQL binlog retention defaults to 0 hours.** DMS cannot read
  changes older than the current binlog. If the task restarts or falls
  behind, the binlog may be purged and unrecoverable. Set
  `binlog_retention_hours=24` via the RDS parameter group BEFORE
  starting a CDC task. This is the #1 silent CDC stall on RDS MySQL.

- **PostgreSQL source needs `wal_level=logical` BEFORE the task starts.**
  Changing `wal_level` requires an RDS reboot. Started with `replica`,
  logical replication fails immediately with "logical decoding requires
  wal_level >= logical." Check the parameter group BEFORE starting.

- **The DMS user needs `EXECUTE on DBMS_LOGMNR` for Oracle, not just
  SELECT.** Oracle LogMiner CDC requires the `LOGMINING` role (12c+) or
  explicit `EXECUTE on DBMS_LOGMNR` (11g). Missing this produces
  "ORA-01331: LogMiner session does not exist" — a permissions error,
  not a binary-logging error.

- **Table-mapping rules can silently exclude tables.** A `selection`
  rule with `filter` can exclude tables the operator expects to migrate.
  `describe-table-statistics` shows what DMS actually loaded — compare
  against the expected list. A "wasn't migrated" table is almost always
  a table-mapping issue, not a DMS bug.

- **LOB columns default to `LIMITED` mode (32KB).** CLOB/TEXT/BLOB
  columns larger than `LobMaxSize` (default 32KB) are truncated or fail.
  For LOB-heavy migrations, set `LobMaxSize=0` (unlimited, slower) or
  use `InlineLob`. Failure shows as "LOB size exceeds maximum."

- **CDC latency is measured from the source, not the target.**
  `CDCLatencySource` = lag between source's current time and last change
  DMS read. `CDCLatencyTarget` = lag between last read and last applied.
  High source = binlog/pglogical bottleneck; high target = constraint
  checks/trigger overhead.

- **The replication instance is shared across tasks.** One task's heavy
  CDC load can starve others. `FreeableMemory` near zero and `SwapUsage`
  climbing indicates capacity exhaustion, not a per-task issue.

### Step 1: task-failed-at-start

Task status is `failed` immediately or within seconds of starting.

**Probes:**

1. `aws dms describe-replication-tasks --filters
   Name=replication-task-id,Values=<task-id>` — capture `Status`,
   `StopReason`, `LastFailureMessage`.
2. `aws logs filter-log-events --log-group-name dms-task-<id>
   --filter-pattern ERROR` — capture the engine-specific error.
3. `aws dms describe-endpoints` — capture source and target
   `EngineName`, `ServerName`, `Port`, `SslMode`, and
   `ExternalTableDefinition` / `ExtraConnectionAttributes`.
4. `aws dms test-connection --replication-instance-arn <inst-arn>
   --endpoint-arn <source-arn>` — verify the source is reachable.

**Decision:**

- If task logs show "binary logging is not enabled" (MySQL) -> Step 4b.
- If task logs show "could not access file $libdir/pglogical" or
  "logical decoding requires wal_level >= logical" (PostgreSQL) ->
  Step 4a.
- If task logs show "MS-CDC is not enabled" (SQL Server) -> Step 4c.
- If task logs show "ORA-01331 LogMiner" (Oracle) -> Step 4 (Oracle).
- If `test-connection` fails for source -> Step 3a (source SG / VPC).
- If `test-connection` fails for target -> Step 5a (target SG / VPC).
- If task logs show "ResourceNotFound: role dms-vpc-role" -> Step 8
  (IAM).
- If none match -> NEED_MORE_INFO with the raw error.

### Step 2: task-failed-mid-migration

Task status is `failed` after the full load started or during CDC.

**Probes:**

1. `aws dms describe-table-statistics --replication-task-arn <arn>` —
   find the table with `LastErrorMessage` set or `FullLoadRowCount` at
   0 when others have rows.
2. `aws logs filter-log-events --log-group-name dms-task-<id>
   --filter-pattern ERROR` — capture the per-table error.
3. `aws cloudwatch get-metric-statistics --namespace AWS/DMS
   --metric-name CDCLatencySource ...` — check if CDC lag preceded
   the failure.

**Decision:**

- If task logs show "foreign key constraint violation" -> Step 5b.
- If task logs show "primary key missing on target table" -> Step 5b.
- If task logs show "ORA-01722 invalid number" or "value too long for
  type" -> Step 7b (data type mismatch).
- If task logs show "LOB size exceeds maximum" -> Step 7c (LOB).
- If `FreeableMemory` dropped to near zero before the failure -> Step
  6b (memory pressure).
- If `SwapUsage` was high before the failure -> Step 6c (disk swap).

### Step 3: source connection failures

#### Step 3a: source SG / network

**Probe:** `aws dms test-connection --replication-instance-arn <inst>
--endpoint-arn <source>` returns
`ConnectionState: failed`. **Verify:** `aws ec2 describe-security-groups
--group-ids <source-sg>` — check inbound rules allow the DMS instance's
SG on the source port (3306 MySQL, 5432 PostgreSQL, 1433 SQL Server,
1521 Oracle). **Fix:** Add an inbound rule allowing the DMS instance SG.

#### Step 3b: source IAM / credentials

**Probe:** Task logs show "Access denied for user" (MySQL) or
"authentication failed" (PostgreSQL). **Verify:** The DMS source
endpoint's `Username` / `Password` (Secrets Manager or inline). The
user must have replication privileges for the engine (see Step 4).

### Step 4: source CDC configuration (engine-specific)

#### Step 4a: PostgreSQL source — pglogical / wal_level

**Probes:** On the source: `select name, setting from pg_settings where
name in ('wal_level', 'max_replication_slots');` (`wal_level` must be
`logical`); `select * from pg_extension where extname='pglogical';`
(must return a row); `select * from pg_replication_slots where
slot_name like 'awsdms_%';` (must return the DMS slot, `active: t`).
**Fix:** Set `wal_level=logical` in the RDS parameter group and reboot.
Install `pglogical` via `CREATE EXTENSION pglogical;`. Grant the DMS
user `REPLICATION` attribute and `pglogical` role.

#### Step 4b: MySQL source — binlog

**Probes:** `show variables like 'binlog_format';` (must be `ROW`);
`show variables like 'binlog_row_image';` (must be `FULL`); `show
variables like 'binlog_retention_hours';` (should be >= 24; RDS default
0 causes CDC stalls); `show grants for '<dms-user>';` (must include
`REPLICATION SLAVE`, `REPLICATION CLIENT`). **Fix:** Set
`binlog_format=ROW` and `binlog_row_image=FULL` in the RDS parameter
group and reboot. Set `binlog_retention_hours=24`. Grant
`REPLICATION SLAVE, REPLICATION CLIENT`.

#### Step 4c: SQL Server source — MS-Replication / MS-CDC

**Probes:** `select name, is_cdc_enabled, is_published from
sys.databases where name='<db>';` (one must be `1`); the DMS user must
be `sysadmin` (MS-Replication) or `db_owner` (MS-CDC). **Fix:** Enable
MS-CDC: `use <db>; exec sys.sp_cdc_enable_db;`. Or enable MS-Replication
via SSMS. SQL Server Express does NOT support CDC — upgrade to
Web/Standard/Enterprise.

### Step 5: target connection and constraints

#### Step 5a: target SG / network

**Probe:** `aws dms test-connection --replication-instance-arn <inst>
--endpoint-arn <target>` returns failed. **Verify:** `aws ec2
describe-security-groups --group-ids <target-sg>` — check inbound rules
allow the DMS instance SG on the target port.

#### Step 5b: target constraints (PK / FK / unique)

**Probes:** Task logs show FK/PK/unique constraint violation (engine-
specific message); `describe-table-statistics` shows the failing table
with `Inserts` at non-zero but `FullLoadRowCount` not advancing; inspect
the target schema for FK constraints referencing unloaded tables.
**Fix:** Disable FK constraints on the target during full load
(`ForeignKeyChecks=0` MySQL, `session_replication_role=replica`
PostgreSQL, `ALTER TABLE ... NOCHECK CONSTRAINT` SQL Server). Use DMS
`TargetTablePrepMode=TRUNCATE_BEFORE_LOAD`. Load parent tables before
child tables (via table-mapping `table-order` or by splitting tasks).

### Step 6: CDC latency and capacity

#### Step 6a: CDC latency climbing

**Probes:** `aws cloudwatch get-metric-statistics --namespace AWS/DMS
--metric-name CDCLatencySource ...` (climbing = source bottleneck:
binlog/pglogical throughput); `--metric-name CDCLatencyTarget ...`
(climbing = target bottleneck: constraint checks, triggers, single-
threaded apply). **Decision:** High `CDCLatencySource` -> source CDC
mechanism is slow (increase `binlog_retention_hours` for MySQL, verify
`max_replication_slots` for PostgreSQL). High `CDCLatencyTarget` ->
target apply is slow (increase `ParallelApplyThreads` and
`ParallelApplyBufferSize`, disable triggers on target during sync).

#### Step 6b: memory pressure

**Probes:** CloudWatch `FreeableMemory` near zero (under 500MB for
dms.r5.large) + `CPUUtilization` sustained > 80%. **Fix:** Upgrade the
instance class (dms.r5.large -> dms.r5.xlarge). Move tasks off the
shared instance. Reduce `MaxFileSize` in task settings.

#### Step 6c: disk swap

**Probes:** CloudWatch `SwapUsage` non-zero and climbing + non-zero
`CDCChangesDiskSource` (DMS spilling CDC changes to disk). **Fix:**
Upgrade the instance class (more RAM). Increase `AllocatedStorage` if
storage-bound. Reduce the number of tasks on the shared instance.

### Step 7: full-load and data errors

#### Step 7a: table-mapping exclusions

**Probes:** `describe-table-statistics` — compare loaded tables vs
expected list. Missing tables indicate a table-mapping `filter` or
`exclude` rule. Inspect `TableMappings` JSON for `selection` rules with
exclusionary `filter` conditions. **Fix:** Adjust the `selection` rule
to `include` all required tables. Re-run the task.

#### Step 7b: data type mismatch

**Probes:** Task logs show "ORA-01722 invalid number" (Oracle source),
"value too long for type character varying(N)" (PostgreSQL target), or
"Data truncation: Data too long for column" (MySQL target). Compare
source/target column types (Oracle `NUMBER(38,0)` -> PostgreSQL
`NUMERIC` precision loss; MySQL `DATETIME` -> PostgreSQL `TIMESTAMP`
timezone; SQL Server `NVARCHAR(MAX)` -> PostgreSQL `TEXT`). **Fix:**
Add explicit `transformation` rules in `TableMappings` to cast types.
Or pre-create the target schema with wider columns and use
`TargetTablePrepMode=DO_NOTHING`.

#### Step 7c: LOB size limit

**Probes:** Task logs show "LOB size exceeds maximum"; task settings
`LobMaxSize` (default 32KB) vs actual LOB column sizes. **Fix:** Set
`LobMaxSize=0` (unlimited — slower) for LOB-heavy tables. Or use
`BulkMaxSize` with `InlineLob` for small LOBs. Pre-create the target
table with `TEXT` / `BYTEA` / `VARBINARY(MAX)` sized to the source.

### Step 8: task settings and IAM

**Probes:** Task logs empty/missing — `Logging` is `ESSENTIAL` (default)
or disabled. `aws iam get-role --role-name dms-cloudwatch-logs-role` —
trust policy must include `dms.amazonaws.com` and permissions for
`logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`.
`aws iam get-role --role-name dms-vpc-role` — trust policy must include
`dms.amazonaws.com` and permissions for `ec2:CreateNetworkInterface`,
`ec2:DescribeNetworkInterfaces`, `ec2:DeleteNetworkInterface`. **Fix:**
Recreate the IAM roles via the console or `create-replication-instance`
(which prompts to create them). Set `Logging` to `DETAILED` to capture
engine-specific error messages.

## STRICT output contract

Every response MUST be a single block in this exact format. No prose
before or after. Substitute the angle-bracket placeholders.

```text
TARGET: <task-arn> (source: <engine>, target: <engine>, instance: <class>)
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <SOURCE_CONNECTION | SOURCE_BINARY_LOGGING | SOURCE_PERMISSIONS |
        TARGET_CONNECTION | TARGET_CONSTRAINTS | TARGET_PERMISSIONS |
        TASK_SETTINGS | TABLE_MAPPING | DATA_TYPE_MISMATCH | LOB_LIMIT |
        INSTANCE_CAPACITY | MEMORY_PRESSURE | DISK_SWAP | NETWORK_SG |
        IAM_ROLE | DMS_SERVICE | UNKNOWN>
EVIDENCE:
  - <observed symptom — task status, error message, metric anomaly>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <task-arn>/<endpoint>. Proceed?
  (yes/no)"
```

### Worked example — PostgreSQL source CDC (wal_level=replica)

```text
TARGET: arn:aws:dms:us-east-1:111:task:TASK001 (source: postgres,
        target: postgres, instance: dms.r5.large)
VERDICT: ROOT_CAUSE_FOUND
REASON: The PostgreSQL source has wal_level=replica, which does not
  support logical replication. Task started in CDC mode and failed
  immediately with "logical decoding requires wal_level >= logical."
LAYER: SOURCE_BINARY_LOGGING
EVIDENCE:
  - Symptom: task status failed within 10s of start.
  - Probe: task logs: "logical decoding requires wal_level >= logical."
  - Probe (source): select setting from pg_settings where
    name='wal_level'; returns: replica.
  - Passing: source SG allows DMS SG on 5432; pglogical installed;
    DMS user has REPLICATION attribute.
REMEDIATION:
  1. aws rds modify-db-parameter-group --db-parameter-group-name
     <pg-name> --parameters ParameterName=wal_level,
     ApplyMethod=pending-reboot,ParameterValue=logical
  2. aws rds reboot-db-instance --db-instance-identifier <pg-id>
  3. Verify wal_level=logical, then: aws dms start-replication-task
     --replication-task-arn <task-arn> --start-replication-task-type
     start-replication
CONFIRM: "About to set wal_level=logical on <pg-id> and reboot.
  Brief connection drop. Proceed? (yes/no)"
```

### Worked example — CDC latency from binlog retention (MySQL RDS)

```text
TARGET: arn:aws:dms:us-east-1:111:task:TASK002 (source: mysql,
        target: postgres, instance: dms.r5.xlarge)
VERDICT: ROOT_CAUSE_FOUND
REASON: MySQL RDS source has binlog_retention_hours=0 (default),
  causing binlogs to be purged before DMS reads them. CDCLatencySource
  climbed to 86400s (24h); task cannot recover the missing changes.
LAYER: SOURCE_BINARY_LOGGING
EVIDENCE:
  - Symptom: CDCLatencySource climbing steadily over 24 hours; task
    running but not applying changes.
  - Probe: show variables like 'binlog_retention_hours'; returns 0.
  - Probe: show binary logs; returns only current binlog — older
    binlogs purged.
  - Passing: binlog_format=ROW; binlog_row_image=FULL; DMS user has
    REPLICATION SLAVE, REPLICATION CLIENT.
REMEDIATION:
  1. aws rds modify-db-parameter-group --db-parameter-group-name
     <pg-name> --parameters ParameterName=binlog_retention_hours,
     ApplyMethod=immediate,ParameterValue=24
  2. For already-purged binlogs: reload from snapshot or accept data
     loss for the gap. Restart in full-load-and-cdc mode if needed.
  3. Verify binlog_retention_hours=24; monitor CDCLatencySource.
CONFIRM: "About to set binlog_retention_hours=24 on <pg-name>. No
  reboot required. Proceed? (yes/no)"
```

### Worked example — FK constraint violation on full load

```text
TARGET: arn:aws:dms:us-east-1:111:task:TASK003 (source: oracle,
        target: postgres, instance: dms.r5.2xlarge)
VERDICT: ROOT_CAUSE_FOUND
REASON: Target PostgreSQL has FK constraint on orders.customer_id
  referencing customers.id, but customers was not loaded before
  orders. FK check failed on first orders insert.
LAYER: TARGET_CONSTRAINTS
EVIDENCE:
  - Symptom: task failed at table ORDERS, FullLoadRowCount at 0 while
    other tables loaded.
  - Probe: task logs: "insert or update on table 'orders' violates
    foreign key constraint 'orders_customer_id_fkey'."
  - Probe: describe-table-statistics shows CUSTOMERS in "loading"
    while ORDERS attempted inserts — load order did not respect FK.
  - Passing: source/target connections OK; data types compatible.
REMEDIATION:
  1. On target: set session_replication_role=replica; (disables FK
     checks for the session).
  2. Or set DMS TargetTablePrepMode=TRUNCATE_BEFORE_LOAD with table-
     order rules placing parent tables before child tables.
  3. aws dms start-replication-task --replication-task-arn <task-arn>
     --start-replication-task-type reload-target
  4. Verify: ORDERS FullLoadRowCount advancing; no constraint errors.
CONFIRM: "About to disable FK checks on the target and restart the
  task. Proceed? (yes/no)"
```

### Worked example — memory pressure causing CDC stall

```text
TARGET: arn:aws:dms:us-east-1:111:task:TASK004 (source: mysql,
        target: postgres, instance: dms.r5.large)
VERDICT: ROOT_CAUSE_FOUND
REASON: dms.r5.large (8GB RAM) running 3 CDC tasks. FreeableMemory
  dropped to 200MB, SwapUsage climbed to 2GB, causing thrashing and
  CDC disk spill.
LAYER: MEMORY_PRESSURE
EVIDENCE:
  - Symptom: CDCLatencyTarget climbing on all 3 tasks; task running
    but applying changes slowly.
  - Probe: CloudWatch FreeableMemory: avg 200MB, min 50MB (under
    500MB threshold for dms.r5.large).
  - Probe: SwapUsage: avg 2GB, climbing. CDCChangesDiskSource non-zero.
  - Passing: source binlog retention sufficient; SG rules OK; target
    constraints OK.
REMEDIATION:
  1. aws dms modify-replication-instance --replication-instance-arn
     <inst-arn> --replication-instance-class dms.r5.xlarge
     --apply-immediately
  2. Or move 1-2 tasks to a separate instance to reduce contention.
  3. Verify: FreeableMemory > 2GB; SwapUsage drops to zero;
     CDCLatencyTarget decreases on all tasks.
CONFIRM: "About to upgrade <inst-id> dms.r5.large -> dms.r5.xlarge.
  Brief task interruption. Proceed? (yes/no)"
```

## Anti-Patterns — NEVER

- NEVER diagnose a DMS task failure without first pulling the task's
  CloudWatch Logs. The `LastFailureMessage` in
  `describe-replication-tasks` is a high-level signal; the actual
  engine-specific error (binlog disabled, constraint name, column type,
  LOB size) is only in the logs. Without logs, you are guessing.

- NEVER start a CDC task on a MySQL source without verifying
  `binlog_format=ROW` AND `binlog_retention_hours >= 24`. RDS MySQL
  defaults to `binlog_retention_hours=0`, causing binlogs to be purged
  before DMS reads them. The task runs for hours then silently stalls.

- NEVER start a CDC task on a PostgreSQL source without verifying
  `wal_level=logical`. Changing `wal_level` requires a reboot; the task
  fails immediately if it's still `replica`. Check the parameter group
  BEFORE starting the task.

- NEVER assume the DMS task `Logging` setting is `DETAILED` by default.
  The default is `ESSENTIAL`. Without `DETAILED` logging, engine-
  specific errors are absent from CloudWatch Logs and diagnosis is
  impossible. Set `Logging` to `DETAILED` first when logs are empty.

- NEVER assume a replication instance has capacity headroom. A single
  dms.r5.large (8GB RAM) running 3+ CDC tasks will exhaust memory and
  swap to disk. Always check `FreeableMemory`, `SwapUsage`, and
  `CPUUtilization` before per-task latency — the root cause may be the
  instance, not the task.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`start-replication-task`, `stop-replication-task`,
  `modify-replication-task`, `modify-replication-instance`,
  `reboot-db-instance`, `modify-db-parameter-group`), emit:
  `CONFIRM: About to <operation> on <task-arn / instance / db> in
  account <account> region <region>. This will <consequence>. Proceed?
  (yes/no)`. Do NOT execute until the operator confirms.

- **Capture pre-state for audit.** Before remediation: `aws dms
  describe-replication-tasks --filters Name=replication-task-id,
  Values=<task-id> --output json > /tmp/<task-id>-pre-$(date +%s).json`.

- **Verify source CDC is enabled before restarting.** A task restart on
  a misconfigured source will fail again. Always run the source-specific
  probes (Step 4) before `start-replication-task`.

- **Verify the target can accept the load.** For full-load restarts,
  ensure FK constraints are disabled or ordered, and target tables are
  truncated if `TargetTablePrepMode=TRUNCATE_BEFORE_LOAD`.

- **Verify IAM roles exist.** `dms-vpc-role` and `dms-cloudwatch-logs-
  role` must exist with trust policy `dms.amazonaws.com`. Missing roles
  cause connection/logging failures that masquerade as engine errors.

- **Prefer source-side parameter changes over task-side workarounds.**
  Setting `binlog_format=ROW` or `wal_level=logical` on the source is
  the correct fix; increasing `ParallelApplyThreads` is a workaround.

## Expert heuristic — the top 5 non-obvious signals

A senior DMS engineer checks these five things first when a task is
failing. Each flips a diagnosis if missed:

1. **Task logs are empty — Logging is ESSENTIAL.** If
   `filter-log-events` returns nothing, `Logging` is `ESSENTIAL`
   (default) or the `dms-cloudwatch-logs-role` IAM role is missing.
   Set `Logging` to `DETAILED` and verify the role before diagnosing.

2. **RDS MySQL `binlog_retention_hours=0`.** The default on RDS MySQL;
   causes silent CDC stalls. The task runs, then hours later
   CDCLatencySource climbs to infinity because binlogs were purged.
   Always check first for MySQL CDC sources, even if previously working.

3. **PostgreSQL `wal_level=replica`.** Changing this requires a reboot.
   If the source was recently restored from a snapshot or the parameter
   group was changed, `wal_level` may have reverted. A task that worked
   yesterday may fail today.

4. **Table load order vs FK dependencies.** DMS loads tables in an
   unspecified order by default. If a child table loads before its
   parent, the FK check fails. The fix is `TargetTablePrepMode` or
   disabling FK checks during load, not removing the constraints.

5. **Shared instance capacity.** A single replication instance running
   multiple CDC tasks is the most common cause of "all tasks are slow
   at the same time." The root cause is the instance's `FreeableMemory`
   and `SwapUsage`, not any individual task. Check instance-level
   metrics first when multiple tasks degrade simultaneously.

## Recent AWS features (2024-2026)

- **DMS Serverless (2024 GA):** Auto-provisions replication capacity,
  scaling up/down automatically. Eliminates manual instance-class
  tuning. No fixed replication instance; capacity is Data Migration
  Units (DMUs). Instance-capacity probes become DMU-utilization probes.

- **DMS with Babelfish for Aurora PostgreSQL (2024 GA):** Babelfish
  enables T-SQL on Aurora PostgreSQL. DMS migrates SQL Server to
  Aurora PostgreSQL with Babelfish; target understands T-SQL
  constraints. Target-side diagnosis must account for Babelfish's
  T-SQL-to-PostgreSQL translation.

- **Amazon DMS Fleet Advisor (2024 GA):** Pre-migration assessment tool
  that inventories databases, analyzes complexity, recommends target
  engines. Runs BEFORE the DMS task — not a troubleshooting tool.

- **DMS data validation (2024 enhancement):** Validates data between
  source and target (row count, checksum, full comparison). Enable via
  `Validation` in task settings. Failures appear in `awsdms_control`
  schema tables and task logs. Catches silent data loss.

- **DMS Zero-ETL integration (2025):** For Aurora/RDS PostgreSQL to
  Redshift, native Zero-ETL (no DMS task required). Different pipeline
  — do not confuse with DMS CDC.

- **DMS support for MySQL 8.0 and PostgreSQL 16 (2024-2026):** Improved
  binlog performance and logical replication slot management. Older
  engine versions may have CDC bugs fixed in newer releases.

## Domain

AWS CloudOps / Database Migration Service Replication, CDC Pipeline
Health, and Cross-Engine Migration Diagnostics.

## AWS documentation

- **AWS Database Migration Service User Guide** — https://docs.aws.amazon.com/dms/latest/userguide/
- **Troubleshooting migration tasks** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Troubleshooting.html
- **DMS task settings** — https://docs.aws.amazon.com/dms/latest/userguide/TASK_Settings.html
- **Source engines for DMS** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.html
- **Target engines for DMS** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Target.html
- **Using a PostgreSQL source** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.PostgreSQL.html
- **Using a MySQL source** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Source.MySQL.html
- **DMS Serverless** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Serverless.html
- **DMS data validation** — https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Validating.html
- **DMS Fleet Advisor** — https://docs.aws.amazon.com/dms/latest/userguide/fleet-advisor.html
