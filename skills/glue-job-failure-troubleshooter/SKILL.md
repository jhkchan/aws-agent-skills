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

Four behaviours separate a senior Glue engineer from a generalist:

- **`Container killed by YARN` is a memory sizing problem, not a
  script bug.** YARN kills an executor when its container exceeds the
  allocated memory. The fix is either more DPUs (more parallelism, so
  each executor handles less data), a larger worker type (G.2X doubles
  the heap per executor), or repartitioning the input so no single
  executor holds too much data. Operators who "debug the script" for
  hours miss that the same script succeeded last week on a smaller
  dataset.
- **G.2X is Spark-optimised; G.1X is the default.** G.2X provides two
  Spark executors per worker, doubling executor parallelism for the
  same DPU count. G.1X provides one executor per worker. For
  memory-bound Spark workloads (large shuffles, wide transformations),
  G.2X halves the per-executor data volume and frequently resolves OOM
  without any script change. G.025X is for Python shell jobs only
  (0.0625 DPU per worker) — it cannot run Spark.
- **Bookmark state is per-job-run and tied to partition keys.** Glue
  bookmarking saves the last-processed partition value (typically the
  date or hour column) in the job-bookmark state. On the next run, the
  job reads only partitions newer than the bookmark. If the
  `partition_keys` argument in `glue_context.create_dynamic_frame.
  from_catalog` changes, or the source table's partition columns
  change, the bookmark cannot compare and the job reprocesses
  everything. Operators who "enabled bookmarking" but see the job
  reprocess all data every run usually changed the partition keys
  without resetting the bookmark.
- **JDBC connectivity requires the Glue connection, the security
  group, AND the route.** The Glue connection object stores the JDBC
  URL, the VPC, subnet, and security group. The security group
  attached to the Glue connection must allow outbound to the database.
  The database's security group must allow inbound from the Glue
  connection's security group on the database port. The subnet's route
  table must reach the database's subnet (same VPC, peered VPC, or
  TGW). A failure at any of these three points produces
  `Connection timed out` with no further detail.

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

```bash
# 1. Job configuration (WorkerType, NumberOfWorkers, Timeout, GlueVersion,
#    SecurityConfiguration, Arguments, Command, Role)
aws glue get-job --job-name <name> --output json

# 2. Job run details (state, execution time, error message, arguments)
aws glue get-job-run --job-name <name> --run-id <run-id> --output json

# 3. Recent job runs (state transitions, failure patterns)
aws glue get-job-runs --job-name <name> --output json

# 4. CloudWatch Logs for the failed run
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/default \
  --filter-pattern '"Container killed by YARN" OR "Table not found" OR "Connection timed out" OR "OutOfMemoryError"' \
  --start-time $(date -d '-2 hours' +%s)000 --output json

# 5. Security configuration (CloudWatch encryption, S3 encryption, KMS key)
aws glue get-security-configuration --name <sec-config-name> --output json 2>/dev/null
```

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

- **`Container killed by YARN` is the #1 Glue failure mode.** YARN
  kills an executor when its container exceeds memory. The fix is
  more DPUs, G.2X, or repartitioning — not script changes.
- **G.025X cannot run Spark.** It is for Python shell only (0.0625
  DPU, 1 GB memory). Any Spark job on G.025X produces chronic OOM.
- **MSCK REPAIR TABLE is required after partition data lands
  externally.** Crawlers add partitions automatically; external
  processes (Firehose, S3 copy, EMR) do not. The table exists but
  returns 0 rows until a crawl or `MSCK REPAIR` runs.
- **CloudWatch Logs need `logs:CreateLogStream` and
  `logs:PutLogEvents` on the job's IAM role.** `AWSGlueServiceRole`
  includes these; custom roles may omit them. The job runs but logs
  are empty.
- **DynamicFrame has overhead vs RDD.** Convert to DataFrame early
  (`dynamicframe.toDF()`) and use native Spark APIs for large
  workloads.
- **The default job timeout is 2.5 hours (150 minutes).** Raise for
  known long-running workloads (large backfills).
- **Job metrics require `--enable-metrics`.** Spark UI requires
  `--enable-spark-ui` and `--spark-event-logs-path s3://<bucket>`.
  Without these, the diagnostics dashboards are empty.
- **Python shell jobs do NOT use Spark.** `Command.Name: pythonshell`
  runs a single Python process. If the script expects a Spark session,
  it fails immediately. Use `Command.Name: glueetl` for Spark jobs.

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

Symptom: `Container killed by YARN for exceeding memory limits` in
CloudWatch Logs. The executor's container exceeded its allocated
memory and YARN killed it.

```bash
aws glue get-job --job-name <name> --output json | \
  jq '.Job.{WorkerType, NumberOfWorkers, GlueVersion, Command}'
```

#### 2a: Worker type assessment

| WorkerType | Executors per worker | Heap per executor | Use case |
|---|---|---|---|
| `G.025X` | 0 (no Spark) | 1 GB total | Python shell only |
| `G.1X` | 1 | 10 GB | Default Spark; small-to-medium datasets |
| `G.2X` | 2 | 10 GB each (20 GB total) | Spark-optimised; large datasets, wide transformations |

If `WorkerType: G.025X` on a Spark job (`Command.Name: glueetl`),
**ROOT_CAUSE_IDENTIFIED** with `LAYER: GLUE_WORKER_TYPE_WRONG`. G.025X
cannot run Spark. Fix: switch to G.1X or G.2X.

If `WorkerType: G.1X` and the dataset has grown significantly since
the last successful run, the single executor per worker is now
handling too much data. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_DPU_INSUFFICIENT` (if more workers would help) or
`LAYER: GLUE_WORKER_TYPE_WRONG` (if switching to G.2X would double
executor parallelism).

#### 2b: Number of workers

```bash
aws glue get-job --job-name <name> --output json | jq '.Job.NumberOfWorkers'
```

The minimum for G.1X and G.2X is 2 workers (Spark driver + executor).
The minimum for G.025X is 1. If `NumberOfWorkers` is at the minimum
and the dataset is large, raise the worker count.

#### 2c: Verify with CloudWatch metrics

```bash
aws cloudwatch get-metric-statistics --namespace Glue \
  --metric-name glue.executor.memory.maxUsed \
  --dimensions Name=JobName,Value=<name> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

If `Maximum` is close to the heap limit (10 GB for G.1X), the
executors are at the edge. The YARN kill is the expected outcome.

### Step 3: Data Catalog table not found

Symptom: `AnalysisException: Table or view not found: '<database>.<table>'`
or `Table <database>.<table> not found`.

```bash
aws glue get-table --database <database> --name <table> --output json
```

If `EntityNotFoundException`, the table does not exist in the Data
Catalog. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_DATA_CATALOG_TABLE_NOT_FOUND`. Fix: create the table (run
a crawler, or create it manually with `create-table`), or verify the
database and table names in the job script.

If the table exists, check the database:

```bash
aws glue get-database --name <database> --output json
```

The Data Catalog database must exist and the job's IAM role must have
`glue:GetTable` on the table ARN.

### Step 4: S3 source path wrong

Symptom: `Path does not exist: s3://<bucket>/<prefix>` or the source
returns no data despite the table existing.

```bash
# Check the table's StorageDescriptor.Location
aws glue get-table --database <db> --name <table> --output json | \
  jq '.Table.StorageDescriptor.Location'

# Verify the S3 path exists and has objects
aws s3 ls s3://<bucket>/<prefix>/ --recursive | head -20
```

If the S3 path is empty or does not exist, **ROOT_CAUSE_IDENTIFIED**
with `LAYER: GLUE_S3_SOURCE_PATH_WRONG`. Common causes: typo in the
bucket or prefix, cross-account S3 access without bucket policy, or
the data was written to a different prefix than the catalog expects.

Also check if the job script hardcodes the S3 path:

```python
# In the script — this bypasses the Data Catalog
datasource = glue_context.create_dynamic_frame.from_options(
    connection_type="s3",
    connection_options={"paths": ["s3://wrong-bucket/data/"]},
    format="parquet")
```

If the hardcoded path differs from the Data Catalog location, that is
the error source.

### Step 5: Partitions not loaded (MSCK REPAIR)

Symptom: the table exists, the S3 path has data, but
`dynamicframe.count()` returns 0.

```bash
aws glue get-partitions --database <db> --table-name <table> --output json | \
  jq '.Partitions | length'
```

If 0 partitions but S3 has partitioned data
(`s3://bucket/data/year=2026/month=08/`), the partitions are not
registered in the Data Catalog. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_PARTITION_NOT_LOADED`. Fix:

```bash
# Option 1: MSCK REPAIR TABLE (via Athena)
aws athena start-query-execution \
  --query-string "MSCK REPAIR TABLE <database>.<table>" \
  --work-group <workgroup> --output json

# Option 2: Run a Glue crawler on the S3 path
aws glue start-crawler --name <crawler-name>
```

### Step 6: Bookmark corrupted / partition-key mismatch

Symptom: the job succeeds but reprocesses all data on every run
despite `--job-bookmark-option: job-bookmark-enable`.

```bash
# Check the job run's bookmark option
aws glue get-job-run --job-name <name> --run-id <run-id> --output json | \
  jq '.JobRun.Arguments["--job-bookmark-option"]'

# Check the job's default arguments
aws glue get-job --job-name <name> --output json | \
  jq '.Job.DefaultArguments["--job-bookmark-option"]'
```

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

```bash
aws glue reset-job-bookmark --job-name <name> --output json
```

Then run the job again with `--job-bookmark-option: job-bookmark-enable`.
The first run after reset reprocesses all data (expected); subsequent
runs should process only new partitions.

### Step 7: JDBC connection error

Symptom: `Connection timed out`, `Connection refused`, or
`org.postgresql.util.PSQLException` when connecting to RDS/Redshift.

```bash
# Get the Glue connection
aws glue get-connection --name <connection-name> --output json | \
  jq '.Connection.{ConnectionType, ConnectionProperties, PhysicalConnectionRequirements}'

# Check the security group on the Glue connection
SG=$(aws glue get-connection --name <connection-name> --output json | \
  jq -r '.Connection.PhysicalConnectionRequirements.SecurityGroupIdList[]')
aws ec2 describe-security-groups --group-ids "$SG" --output json | \
  jq '.SecurityGroups[].IpPermissions'
```

#### 7a: Glue connection does not exist

If `EntityNotFoundException`, the Glue connection was never created or
was deleted. **ROOT_CAUSE_IDENTIFIED** with
`LAYER: GLUE_JDBC_CONNECTION_ERROR`. Fix: create the connection with
the JDBC URL, VPC, subnet, and security group.

#### 7b: Security group inbound missing on the database

The database's security group must allow inbound from the Glue
connection's security group on the database port:

```bash
aws ec2 describe-security-groups \
  --filters Name=group-id,Values=<db-sg-id> --output json | \
  jq '.SecurityGroups[].IpPermissions[] | select(.FromPort==<db-port>)'
```

If no inbound rule matches the Glue connection's SG,
**ROOT_CAUSE_IDENTIFIED** with `LAYER: GLUE_JDBC_CONNECTION_ERROR`.
Fix: add an inbound rule to the database's SG allowing the Glue
connection's SG on the database port.

#### 7c: Route table missing

The Glue connection's subnet must have a route to the database's
subnet (same VPC, peered VPC, or TGW). Check the route table:

```bash
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=<glue-subnet-id> --output json | \
  jq '.RouteTables[].Routes'
```

### Step 8: Job timeout

Symptom: the job run transitions to `TIMEOUT` after the configured
`Timeout` value (default 150 minutes = 2.5 hours).

```bash
aws glue get-job --job-name <name> --output json | jq '.Job.Timeout'
aws glue get-job-run --job-name <name> --run-id <run-id> --output json | \
  jq '.JobRun.{ExecutionTime, CompletedOn, ErrorMessage}'
```

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

```bash
# Check if the job has a security configuration with CloudWatch encryption
aws glue get-job --job-name <name> --output json | \
  jq '.Job.SecurityConfiguration'

# Check the IAM role for logs permissions
ROLE_NAME=$(aws glue get-job --job-name <name> --output json | jq -r '.Job.Role' | cut -d/ -f2)
aws iam list-attached-role-policies --role-name "$ROLE_NAME" --output json
```

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

```bash
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/default \
  --filter-pattern '"Traceback" OR "py4j" OR "PythonException"' \
  --start-time $(date -d '-2 hours' +%s)000 --output json
```

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

```bash
# Check if metrics are enabled
aws glue get-job --job-name <name> --output json | \
  jq '.Job.DefaultArguments["--enable-metrics"]'
```

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

```text
TARGET: etl-hourly-events (JobRunId: jr_def456)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The job has --job-bookmark-option=job-bookmark-enable but
  reprocesses all data on every run. The script was updated 3 days ago
  to change partition_keys from ["event_date"] to
  ["event_date","event_hour"]. The bookmark state references the old
  single-key schema and cannot compare; the job treats every run as a
  full reload (Step 6).
LAYER: GLUE_BOOKMARK_CORRUPTED
EVIDENCE:
  - Symptom: CloudWatch Logs show "Processing 2,400,000 records" on
    every run; the source grows by ~100,000/hour, so a bookmarked run
    should process ~100,000, not 2.4M.
  - Probe: aws glue get-job-run returns
    Arguments["--job-bookmark-option"]="job-bookmark-enable".
  - Probe: the script uses partition_keys=["event_date","event_hour"];
    get-job-bookmark references only "event_date".
  - Passing: table exists; partitions loaded; G.2X workers (not memory).
REMEDIATION:
  1. Reset the bookmark: aws glue reset-job-bookmark --job-name etl-hourly-events
  2. Re-run with --job-bookmark-option=job-bookmark-enable (first run
     after reset reprocesses all — expected).
  3. Verify the second run processes only ~100,000 new records.
CONFIRM: Before resetting: "CONFIRM: About to reset the bookmark for
  etl-hourly-events. The next run will reprocess all data. Proceed?"
```

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
