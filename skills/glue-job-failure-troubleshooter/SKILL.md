---
name: glue-job-failure-troubleshooter
description: 'Diagnoses AWS Glue job failures through a fifteen-layer diagnostic tree: ETL script errors (PySpark/Scala exceptions), DPU allocation insufficient (executor YARN OOM, max capacity reached), Python shell vs Spark shell errors, Data Catalog table not found, S3 source data path wrong, partition not loaded (MSCK REPAIR missing), bookmark errors (state corrupted or partition-key mismatch), JDBC connection errors (Glue connection / security group to RDS/Redshift), dynamic frame vs RDD performance, CloudWatch Logs not enabled, job timeout (default 2.5h), worker type mismatch (G.1X vs G.2X vs G.025X), job metrics analysis, and Spark UI DAG inspection. Walks symptoms to a verified root cause with evidence-backed read-only probes; emits ROOT_CAUSE_IDENTIFIED or INSUFFICIENT_DATA.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline symptom classification works from pasted error messages and job configuration. Live-account diagnosis uses aws glue get-job, get-job-run, get-job-runs, get-security-configuration, batch-get-jobs, aws logs get-log-events / filter-log-events, aws glue get-table / get-partitions, aws glue get-connection, aws ec2 describe-security-groups, and aws s3 ls / head-object (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
  when_to_use: Diagnosing an AWS Glue job failure (job run transitions to FAILED, executor YARN kills container for OOM, Data Catalog table not found, S3 source path returns no data, partitions not loaded after MSCK REPAIR, job bookmark reprocessing all data on every run, JDBC connection to RDS/Redshift times out, job exceeds the 2.5h default timeout, G.025X worker too weak for the Spark workload, or CloudWatch Logs are empty). Use when the symptom is "the Glue job failed" and the cause may be DPU allocation, worker type, bookmark state, JDBC connection, partition loading, script error, or worker-type mismatch.
  when_not_to_use: Provisioning a new Glue job (use glue-crawler-deployer for crawlers or the job deployer), Glue Data Quality rule evaluation (use the Data Quality skill), Glue Studio notebook interactive development (use the notebook tooling), or Athena query failures (use athena-query-optimizer). This skill diagnoses job-run failures at execution time; it does not provision or tune steady-state ETL pipelines.
  activation_triggers: Glue job FAILED, Glue executor YARN killed container, Glue out of memory, Glue container killed by YARN, Glue Data Catalog table not found, Glue S3 source path wrong, Glue partition not loaded, MSCK REPAIR TABLE, Glue job bookmark corrupted, Glue bookmark reprocessing all data, Glue JDBC connection error, Glue cannot connect to RDS, Glue cannot connect to Redshift, Glue job timeout, Glue worker type wrong, Glue G.025X too weak, Glue CloudWatch Logs empty, troubleshoot Glue job failure
  invocation_schema: 'Input: either (a) a symptom description ("Glue job failed with executor OOM", "bookmark reprocesses all data every run", "JDBC connection times out"), optionally paired with the job configuration (JobName, worker type, DPU count, script path), OR (b) a JobName plus JobRunId and the CloudWatch Logs error for live-account diagnosis. Output: a deterministic TARGET/VERDICT/REASON/LAYER/EVIDENCE/REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_IDENTIFIED, INSUFFICIENT_DATA} and LAYER ∈ {GLUE_ETL_SCRIPT_ERROR, GLUE_DPU_INSUFFICIENT, GLUE_PYTHON_SHELL_ERROR, GLUE_SPARK_SHELL_ERROR, GLUE_DATA_CATALOG_TABLE_NOT_FOUND, GLUE_S3_SOURCE_PATH_WRONG, GLUE_PARTITION_NOT_LOADED, GLUE_BOOKMARK_CORRUPTED, GLUE_JDBC_CONNECTION_ERROR, GLUE_DYNAMIC_FRAME_PERFORMANCE, GLUE_CLOUDWATCH_LOGS_DISABLED, GLUE_JOB_TIMEOUT, GLUE_WORKER_TYPE_WRONG, GLUE_JOB_METRICS_ANALYSIS, GLUE_SPARK_UI_DAG, UNKNOWN}.'
  invocation_example: '# Minimal valid input (offline symptom classification):

    Symptom: "Glue job etl-daily-orders failed at 03:17 UTC. CloudWatch

    Logs show ''Container killed by YARN for exceeding memory limits''.

    The job runs on G.1X with 10 workers. The same job succeeded last

    week on a smaller dataset."

    JobName: etl-daily-orders

    JobRunId: jr_abc123

    WorkerType: G.1X

    NumberOfWorkers: 10

    Timeout: 150 (minutes, default 2.5h)

    GlueVersion: glue-4.0

    Last successful run: 2026-08-03 (dataset was 50 GB)

    Failed run dataset: 250 GB (5x growth)'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Glue, Glue job, PySpark, Scala, DPU, executor, YARN, out of memory, Python shell, Spark shell, Data Catalog, table not found, S3 source path, partition, MSCK REPAIR, job bookmark, bookmark corrupted, JDBC connection, RDS, Redshift, security group, dynamic frame, CloudWatch Logs, job timeout, worker type, G.1X, G.2X, G.025X, job metrics, Spark UI, troubleshooting
  tags: glue, analytics, troubleshooting, etl, spark, job-failure, dpu, bookmark, jdbc, worker-type
---

# Glue Job Failure Troubleshooter

## Quick start

- **Symptom → layer map (first plausible match drives the first probe):**
  `Container killed by YARN for exceeding memory limits` →
  GLUE_DPU_INSUFFICIENT / GLUE_WORKER_TYPE_WRONG; `Table not found`
  or `AnalysisException: Table or view not found` →
  GLUE_DATA_CATALOG_TABLE_NOT_FOUND; `Path does not exist` on S3
  source → GLUE_S3_SOURCE_PATH_WRONG; table exists but returns 0 rows
  → GLUE_PARTITION_NOT_LOADED (MSCK REPAIR missing); bookmark
  reprocesses all data on every run → GLUE_BOOKMARK_CORRUPTED; JDBC
  `Connection refused` or `Connection timed out` →
  GLUE_JDBC_CONNECTION_ERROR; job run exceeds Timeout →
  GLUE_JOB_TIMEOUT; `CloudWatch Logs` empty for the job run →
  GLUE_CLOUDWATCH_LOGS_DISABLED.
- **Always verify with a read-only probe, never guess.** Each layer
  has a single command that proves or disproves it. A
  ROOT_CAUSE_IDENTIFIED verdict requires positive evidence — a
  failing probe that matches the symptom — not a process of
  elimination.
- **Worker type determines executors per worker.** G.1X gives 1
  executor per worker (1 vCPU / 10 GB heap). G.2X gives 2 executors
  per worker (2 vCPU / 20 GB heap) and is Spark-optimised — the
  same DPU count on G.2X doubles the executor parallelism. G.025X
  (micro) is for Python shell jobs only; running a Spark job on
  G.025X produces chronic OOM.
- **Bookmark state must match the partition keys.** Glue bookmarking
  tracks the last-processed partition value. If the job script's
  `partition_keys` argument changes, or the source table's partition
  columns change, the bookmark state no longer matches and the job
  reprocesses all data on every run. A bookmark reset is required
  after any partition-key schema change.
- **JDBC connections need a Glue connection AND a security group.**
  The Glue connection object holds the JDBC URL, the VPC, subnet, and
  security group. The security group must allow inbound from the Glue
  job's ENI on the database port. Operators who "created the JDBC
  connection" but never added the inbound rule to the RDS security
  group produce a silent `Connection timed out`.

## Mindset

A Glue job failure is almost always a resource, configuration, or
data-catalog problem wearing a "Spark is broken" costume. The ETL
script is fine in the majority of cases; the broken thing is DPU
allocation, worker type, bookmark state, JDBC networking, partition
loading, or CloudWatch Logs enablement. Treat the script as innocent
until the DPU, worker type, bookmark, connection, and catalog layers
are proven clean.

## Philosophy

The four senior-engineer behaviours moved to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

## Quick reference — symptom triage table

| Symptom phrase / error | Most likely layer | First probe |
|---|---|---|
| `Container killed by YARN for exceeding memory limits` | GLUE_DPU_INSUFFICIENT / GLUE_WORKER_TYPE_WRONG | `get-job` (WorkerType, NumberOfWorkers), CloudWatch Logs executor memory |
| `AnalysisException: Table or view not found`, `Table not found` | GLUE_DATA_CATALOG_TABLE_NOT_FOUND | `aws glue get-table --database <db> --name <table>` |
| `Path does not exist: s3://...`, `AmazonS3Exception: NoSuchKey` | GLUE_S3_SOURCE_PATH_WRONG | `aws s3 ls <path>`, `aws glue get-table` (StorageDescriptor.Location) |
| Table exists but `df.count()` returns 0 | GLUE_PARTITION_NOT_LOADED | `aws glue get-partitions`, run `MSCK REPAIR TABLE` |
| Job succeeds but reprocesses all data every run | GLUE_BOOKMARK_CORRUPTED | `get-job-run` (Arguments `--job-bookmark-option`), bookmark state |
| `Connection refused`, `Connection timed out` to JDBC source | GLUE_JDBC_CONNECTION_ERROR | `aws glue get-connection`, security group rules on both sides |
| Job run transitions to TIMEOUT after 150 minutes | GLUE_JOB_TIMEOUT | `get-job` (Timeout), CloudWatch Logs last activity |
| CloudWatch Logs for the job run are empty | GLUE_CLOUDWATCH_LOGS_DISABLED | `get-job` (SecurityConfiguration, CloudWatch encryption), logs group |
| `py4j.Py4JException` or `PythonException` | GLUE_PYTHON_SHELL_ERROR | CloudWatch Logs Python traceback |
| Job runs but is very slow; `glue_context` overhead | GLUE_DYNAMIC_FRAME_PERFORMANCE | Job metrics, DynamicFrame vs RDD usage |
| None of the above, weird runtime error | UNKNOWN | CloudWatch Logs full traceback, Spark UI DAG |

## Pre-flight: job state and gather-info gate

Before symptom-specific probes, gather the canonical job configuration
and short-circuit on job states that mimic execution failures.

### Pre-flight commands

Pre-flight CLI (get-job, get-job-run, get-job-runs, CloudWatch Logs filter, security configuration) moved to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

### Job-run-state short-circuit

| `JobRunState` | Effect on diagnosis |
|---|---|
| `SUCCEEDED` | The job completed; if the symptom is data-correctness, the failure is downstream, not in the job run. |
| `RUNNING` / `STARTING` / `STOPPING` | The job is in flight. Memory/timeout symptoms are not yet final; wait for `FAILED` or `TIMEOUT`. |
| `FAILED` | The job encountered an error. `ErrorMessage` on the run identifies the category (YARN OOM, script exception, connection error). |
| `TIMEOUT` | The job exceeded the configured `Timeout` (default 150 minutes = 2.5h). This is GLUE_JOB_TIMEOUT unless the job was genuinely making progress and the timeout is too low. |
| `STOPPED` | An operator cancelled the run. Not a failure. |
| `RUNNING` but no CloudWatch Logs | CloudWatch Logs encryption or IAM permission issue — the job is running but logs are not delivered. |

### Malformed-input fallback

If the input is missing JobName, JobRunId, or a symptom description,
emit `VERDICT: INSUFFICIENT_DATA` with `LAYER: UNKNOWN`, list the
missing fields, and re-prompt for: (1) the JobName, (2) the JobRunId,
(3) the error message from CloudWatch Logs or the run's
`ErrorMessage`, and (4) the job's WorkerType and NumberOfWorkers.

## Process — Diagnostic decision tree (apply in symptom order)

Pick the entry point based on the symptom. Each layer ends with
either a positive root-cause confirmation or a pass that moves to the
next layer. **Never emit ROOT_CAUSE_IDENTIFIED without a failing probe
that matches the symptom.**

### Step 0: Operational gotchas that change diagnosis

Operational gotchas moved to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.

### Step 1: Symptom entry

| Symptom | Branch |
|---|---|
| `Container killed by YARN`, executor OOM | Step 2 — DPU / worker type |
| `Table or view not found`, `Table not found` | Step 3 — Data Catalog |
| `Path does not exist`, S3 source returns no data | Step 4 — S3 path |
| Table exists but `df.count()` is 0 | Step 5 — Partitions |
| Job reprocesses all data every run | Step 6 — Bookmark |
| `Connection timed out`, `Connection refused` to JDBC | Step 7 — JDBC |
| Job transitions to `TIMEOUT` | Step 8 — Timeout |
| CloudWatch Logs empty for the job run | Step 9 — Logs |
| Python traceback, `py4j` exception | Step 10 — Python shell |
| Job slow, DynamicFrame overhead | Step 11 — Performance |
| None of the above | Step 12 — UNKNOWN |

### Step 2: DPU allocation / worker type

Step 2 probes (worker-type table, worker-count check, CloudWatch memory metrics) moved to [references/glue-worker-type-and-dpu-reference.md](references/glue-worker-type-and-dpu-reference.md) — load on demand.

### Step 3: Data Catalog table not found

Symptom: `AnalysisException: Table or view not found: '<database>.<table>'`
or `Table <database>.<table> not found`.

Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 3 get-table.

If `EntityNotFoundException`, the table does not exist in the Data
Catalog. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_DATA_CATALOG_TABLE_NOT_FOUND`. Fix: create the table (run
a crawler, or create it manually with `create-table`), or verify the
database and table names in the job script.

If the table exists, check the database:

Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 3 get-database.

The Data Catalog database must exist and the job's IAM role must have
`glue:GetTable` on the table ARN.

### Step 4: S3 source path wrong

Symptom: `Path does not exist: s3://<bucket>/<prefix>` or the source
returns no data despite the table existing.

Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 4 StorageDescriptor.Location and s3 ls.

If the S3 path is empty or does not exist, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: GLUE_S3_SOURCE_PATH_WRONG`. Common causes: typo in the
bucket or prefix, cross-account S3 access without bucket policy, or
the data was written to a different prefix than the catalog expects.

Also check if the job script hardcodes the S3 path:

Hardcoded-path script example (Step 4) moved to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

If the hardcoded path differs from the Data Catalog location, that is
the error source.

### Step 5: Partitions not loaded (MSCK REPAIR)

Symptom: the table exists, the S3 path has data, but
`dynamicframe.count()` returns 0.

Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 5 get-partitions count.

If 0 partitions but S3 has partitioned data
(`s3://bucket/data/year=2026/month=08/`), the partitions are not
registered in the Data Catalog. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_PARTITION_NOT_LOADED`. Fix:

Fix commands (MSCK REPAIR via Athena, start-crawler — Step 5) moved to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.

### Step 6: Bookmark corrupted / partition-key mismatch

Symptom: the job succeeds but reprocesses all data on every run
despite `--job-bookmark-option: job-bookmark-enable`.

Bookmark option probes (Step 6) moved to [references/glue-bookmark-and-jdbc-reference.md](references/glue-bookmark-and-jdbc-reference.md) — load on demand.

If `--job-bookmark-option` is `job-bookmark-disable`, bookmarking is
off — the job reprocesses by design. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_BOOKMARK_CORRUPTED` (config issue).

If `--job-bookmark-option` is `job-bookmark-enable` but the job still
reprocesses, the bookmark state's partition keys do not match the
current job script's `partition_keys` argument. This happens after a
script change that altered the `partition_keys` in
`create_dynamic_frame.from_catalog`, or after a table schema change
that altered the partition columns.

Fix: reset the bookmark state:

Bookmark reset command (Step 6 fix) moved to [references/glue-bookmark-and-jdbc-reference.md](references/glue-bookmark-and-jdbc-reference.md) — load on demand.

Then run the job again with `--job-bookmark-option: job-bookmark-enable`.
The first run after reset reprocesses all data (expected); subsequent
runs should process only new partitions.

### Step 7: JDBC connection error

Step 7 probes (get-connection, SG checks, route table) and branches 7a/7b/7c moved to [references/glue-bookmark-and-jdbc-reference.md](references/glue-bookmark-and-jdbc-reference.md) — load on demand.

### Step 8: Job timeout

Symptom: the job run transitions to `TIMEOUT` after the configured
`Timeout` value (default 150 minutes = 2.5 hours).

Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 8 Timeout/ExecutionTime.

If `ExecutionTime` is close to `Timeout` and the CloudWatch Logs show
the job was still making progress (not stuck), the timeout is too low
for the workload. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_JOB_TIMEOUT`. Fix: raise the `Timeout` value.

If the logs show the job was stuck (no log activity for the last 30
minutes before timeout), the root cause is upstream (a hung JDBC
read, a stuck shuffle) — the timeout is a symptom, not the cause.
Investigate the last log activity before the timeout.

### Step 9: CloudWatch Logs disabled

Symptom: the job ran but CloudWatch Logs for the run are empty.

Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 9 SecurityConfiguration and IAM role check.

If the role does not have `AWSGlueServiceRole` (or equivalent inline
permissions with `logs:CreateLogStream` and `logs:PutLogEvents`),
**ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_CLOUDWATCH_LOGS_DISABLED`. Fix: attach the
`AWSGlueServiceRole` managed policy or add the log permissions inline.

If a SecurityConfiguration with CloudWatch KMS encryption is set,
verify the KMS key is enabled and the role has `kms:Decrypt` on it.

### Step 10: Python shell error

Symptom: `py4j.Py4JException`, `PythonException`, or a Python
traceback in CloudWatch Logs.

Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 10 Traceback/py4j log filter.

If the job's `Command.Name` is `pythonshell` and the script uses
`SparkContext.getOrCreate()` or `glue_context`,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: GLUE_PYTHON_SHELL_ERROR`.
Python shell jobs do not have a Spark context. Fix: change
`Command.Name` to `glueetl` if Spark is needed.

If the job's `Command.Name` is `glueetl` and the error is a Python
traceback (not a JVM exception), the script has a Python-level bug.
**ROOT_CAUSE_IDENTIFIED** with `LAYER: GLUE_ETL_SCRIPT_ERROR`. Fix:
address the Python error in the script.

### Step 11: Performance — DynamicFrame vs RDD

Symptom: the job runs but is very slow; execution time is dominated
by `glue_context` overhead rather than Spark transformations.

Probe: [references/diagnostic-commands.md](references/diagnostic-commands.md) — Step 11 --enable-metrics check.

If `--enable-metrics` is not set, enable it and re-run. Then inspect
the job metrics dashboard for executor skew, spill, and GC overhead.

Common DynamicFrame performance issues:
- Using `dynamicframe.toDF()` too late — the DynamicFrame serialises
  on every transformation. Convert to DataFrame early.
- Using `dynamicframe.show()` for debugging on large frames — it
  materialises the entire frame.
- Using `ApplyMapping` with thousands of columns — it is O(n^2) on
  the column count.

If the job uses DynamicFrame operations where native Spark DataFrame
operations would work, **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_DYNAMIC_FRAME_PERFORMANCE`. Fix: convert to DataFrame
early and use native Spark APIs.

### Step 12: UNKNOWN / INSUFFICIENT_DATA

- **INSUFFICIENT_DATA** — A specific probe requires operator input
  (the full CloudWatch Logs traceback, the Glue connection name, the
  Data Catalog database name). List the missing pieces and the next
  probe to run once the info is available.
- **UNKNOWN** — All probes passed and the symptom persists. Escalate
  to AWS Support with the JobName, JobRunId, the full CloudWatch Logs
  for the run, and the Spark UI DAG (if enabled).

## Output format

```text
TARGET: <job-name (JobRunId)>
VERDICT: ROOT_CAUSE_IDENTIFIED | INSUFFICIENT_DATA
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <GLUE_ETL_SCRIPT_ERROR | GLUE_DPU_INSUFFICIENT |
        GLUE_PYTHON_SHELL_ERROR | GLUE_SPARK_SHELL_ERROR |
        GLUE_DATA_CATALOG_TABLE_NOT_FOUND | GLUE_S3_SOURCE_PATH_WRONG |
        GLUE_PARTITION_NOT_LOADED | GLUE_BOOKMARK_CORRUPTED |
        GLUE_JDBC_CONNECTION_ERROR | GLUE_DYNAMIC_FRAME_PERFORMANCE |
        GLUE_CLOUDWATCH_LOGS_DISABLED | GLUE_JOB_TIMEOUT |
        GLUE_WORKER_TYPE_WRONG | GLUE_JOB_METRICS_ANALYSIS |
        GLUE_SPARK_UI_DAG | UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or observed behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <job-name> in <region>. Proceed?
  (yes/no)"
```

### Worked example — DPU insufficient, G.1X → G.2X

```text
TARGET: etl-daily-orders (JobRunId: jr_abc123)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The job runs on G.1X with 10 workers (10 executors, 10 GB heap
  each). The input dataset grew from 50 GB to 250 GB (5x) since the
  last successful run. CloudWatch Logs show "Container killed by YARN
  for exceeding memory limits" on 3 executors. The same script
  succeeded on 50 GB; the failure is memory sizing, not a script bug.
  G.2X would double the executor count to 20 (2 per worker) and halve
  the per-executor data volume (Step 2a/2b).
LAYER: GLUE_DPU_INSUFFICIENT
EVIDENCE:
  - Symptom: job transitions to FAILED after 23 minutes. CloudWatch
    Logs contain "Container killed by YARN for exceeding memory
    limits. Container [pid=1234] was killed." on 3 executors.
  - Probe: aws glue get-job returns WorkerType=G.1X,
    NumberOfWorkers=10, GlueVersion=glue-4.0.
  - Probe: aws cloudwatch get-metric-statistics on
    glue.executor.memory.maxUsed shows Maximum 9.7 GB (out of 10 GB
    heap) in the 5 minutes before the kill.
  - Passing: the job script has not changed since the last successful
    run; the Data Catalog table exists; partitions are loaded; no JDBC
    connection in play.
REMEDIATION:
  1. Switch the worker type to G.2X (doubles executor parallelism):
     aws glue update-job --job-name etl-daily-orders \
       --job-update '{"WorkerType":"G.2X","NumberOfWorkers":10}'
  2. Optionally increase NumberOfWorkers to 15 if G.2X alone is not
     enough.
  3. Re-run the job and monitor glue.executor.memory.maxUsed; it
     should peak below 5 GB per executor (half the data per executor).
CONFIRM: Before updating the job, emit and await:
  "CONFIRM: About to switch etl-daily-orders from G.1X to G.2X with
   10 workers. Proceed? (yes/no)"
```

### Worked example — Bookmark partition-key mismatch

Full bookmark partition-key-mismatch example moved to [references/worked-examples.md](references/worked-examples.md) — load on demand.

## Anti-Patterns — NEVER

- NEVER declare ROOT_CAUSE_IDENTIFIED without a failing probe that
  matches the symptom.
- NEVER assume a `Container killed by YARN` error is a script bug. It
  is memory sizing — fix with more DPUs, G.2X, or repartitioning.
- NEVER run a Spark job on G.025X. G.025X is for Python shell only.
- NEVER assume "bookmarking is enabled" means only new data is
  processed. Bookmark state is tied to partition keys. Reset after
  any partition-key change.
- NEVER assume a Glue JDBC connection alone is sufficient. The
  database's SG must allow inbound from the Glue connection's SG.
- NEVER assume the Data Catalog knows about new S3 partitions
  automatically. Run `MSCK REPAIR TABLE` or a crawler after external
  data lands.
- NEVER assume CloudWatch Logs are on by default. The job's IAM role
  needs `logs:CreateLogStream` and `logs:PutLogEvents`.
- NEVER use DynamicFrame where native Spark DataFrame would work —
  DynamicFrame adds serialisation overhead. Convert early.
- NEVER keep the default 2.5h timeout for known long-running jobs.
  NEVER diagnose a `TIMEOUT` without checking the last log activity
  (stuck vs. making progress).
- NEVER enable Spark UI without an S3 log path
  (`--spark-event-logs-path`).
- NEVER perform state-changing operations as diagnostic probes. Every
  probe is read-only. State changes are remediations, gated behind
  CONFIRM.

## Pre-flight safety checks (run before any state-changing CLI)

- **MANDATORY CONFIRMATION GATE.** Before `update-job`,
  `reset-job-bookmark`, `start-job-run`, `stop-job-run`, or
  `create-connection`, emit and await operator approval.
- **Read-only first.** Every probe is read-only.
- **Updating a job** (`update-job`) is safe for config-only changes
  (WorkerType, NumberOfWorkers, Timeout). The next run uses the new
  config.
- **Resetting a bookmark** causes the next run to reprocess all data.
  Confirm before resetting on large datasets.
- **Starting a job run** consumes DPUs (G.2X = 2x G.1X cost). Confirm
  the budget impact.
- **Bulk remediation batch limit.** Batch into groups of at most 5
  jobs, emit a single CONFIRM per batch, verify between batches.

## Remediation guidance (command index)

- **GLUE_DPU_INSUFFICIENT**: `update-job` — raise `NumberOfWorkers`
- **GLUE_WORKER_TYPE_WRONG**: `update-job` — switch `WorkerType` to G.2X (or from G.025X to G.1X)
- **GLUE_DATA_CATALOG_TABLE_NOT_FOUND**: run a crawler or `create-table`
- **GLUE_S3_SOURCE_PATH_WRONG**: fix the path in the script or table `StorageDescriptor.Location`
- **GLUE_PARTITION_NOT_LOADED**: `MSCK REPAIR TABLE` (Athena) or `start-crawler`
- **GLUE_BOOKMARK_CORRUPTED**: `reset-job-bookmark` then re-run with `--job-bookmark-option=job-bookmark-enable`
- **GLUE_JDBC_CONNECTION_ERROR**: `create-connection` + add inbound SG rule on the database
- **GLUE_JOB_TIMEOUT**: `update-job` — raise `Timeout`
- **GLUE_CLOUDWATCH_LOGS_DISABLED**: attach `AWSGlueServiceRole` or add `logs:*` permissions
- **GLUE_PYTHON_SHELL_ERROR**: change `Command.Name` to `glueetl` for Spark
- **GLUE_DYNAMIC_FRAME_PERFORMANCE**: convert to DataFrame early, use native Spark APIs

See `references/glue-worker-type-and-dpu-reference.md` for the full
worker-type / DPU mapping and `references/glue-bookmark-and-jdbc-reference.md`
for bookmark and JDBC connection detail.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples (bookmark partition-key mismatch).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight CLI and per-step read-only probe commands (Steps 3-5, 8-11).
- [references/advanced-patterns.md](references/advanced-patterns.md) — philosophy deep dive and Step 0 operational gotchas.
- [references/glue-worker-type-and-dpu-reference.md](references/glue-worker-type-and-dpu-reference.md) — Step 2 worker-type/DPU probes and branch logic.
- [references/glue-bookmark-and-jdbc-reference.md](references/glue-bookmark-and-jdbc-reference.md) — Step 6 bookmark probes and Step 7 JDBC probes/branches.

## Domain

AWS CloudOps / Glue Analytics, ETL Job Diagnostics, DPU Allocation,
Worker Type Sizing, Data Catalog Partition Management, Job Bookmark
State, and JDBC Connectivity.

## AWS documentation

- **AWS Glue Developer Guide** — https://docs.aws.amazon.com/glue/latest/dg/
- **Glue job runs** — https://docs.aws.amazon.com/glue/latest/dg/monitor-debug-operations.html
- **Glue job bookmarks** — https://docs.aws.amazon.com/glue/latest/dg/monitor-continuations.html
- **Glue connections (JDBC)** — https://docs.aws.amazon.com/glue/latest/dg/populate-add-connection.html
- **Glue worker types** — https://docs.aws.amazon.com/glue/latest/dg/aws-glue-programming-etl-glue-arguments.html
- **Glue security configurations** — https://docs.aws.amazon.com/glue/latest/dg/console-security-configurations.html
- **Glue job metrics** — https://docs.aws.amazon.com/glue/latest/dg/monitor-profile-metrics.html
- **Glue Spark UI** — https://docs.aws.amazon.com/glue/latest/dg/monitor-spark-ui.html
- **MSCK REPAIR TABLE** — https://docs.aws.amazon.com/athena/latest/ug/msck-repair-table.html
- **AWS Health** — https://docs.aws.amazon.com/health/latest/ug/
