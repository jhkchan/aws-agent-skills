# DMS Task Troubleshooter — advanced patterns (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

## Step 0: Expert knowledge — non-obvious DMS behaviors (moved from SKILL.md)


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


## Expert heuristic — the top 5 non-obvious signals (moved from SKILL.md)


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


## Recent AWS features 2024-2026 (moved from SKILL.md)


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

