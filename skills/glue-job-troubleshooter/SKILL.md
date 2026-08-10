---
name: glue-job-troubleshooter
description: >-
  Diagnoses AWS Glue ETL job failures through a seven-category diagnostic
  tree — Python script exceptions (KeyError, AttributeError, import
  errors), job timeout (insufficient DPU, long-running transforms, skewed
  reads), JDBC connection errors (VPC security group, subnet, network ACL,
  self-referencing rule), job bookmark errors (not advancing, reprocessing
  data, partition format change), Data Catalog errors (table not found,
  partition not found, stale crawler), Spark errors (executor OOM, stage
  failures, data skew, GC overhead), and DynamicFrame errors (schema
  mismatch, type coercion). Reads get-job-run ErrorMessage and
  ExecutionTime, CloudWatch logs (/aws-glue/jobs/), Spark UI exported to
  S3, and get-job-bookmark state. Emits ROOT_CAUSE_FOUND with the failing
  probe and positive evidence, NEED_MORE_INFO when a probe requires
  operator input, or ESCALATE for AWS-side incidents. Use when a Glue job
  shows FAILED, TIMEOUT, RUNNING past expected duration, or is
  reprocessing data the bookmark should have skipped.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline classification works from a pasted job-run ErrorMessage,
  CloudWatch Logs excerpt, or Spark stage failure summary. Live-account
  diagnosis uses aws glue get-job-run, get-job-runs, get-job-bookmark,
  get-connection, aws logs filter-log-events on /aws-glue/jobs, aws s3 cp
  for Spark UI event logs, aws glue get-table and get-partitions for
  catalog validation, and aws ec2 describe-security-groups /
  describe-network-acls / describe-route-tables for JDBC VPC verification
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - AWS Glue
  - Glue ETL
  - Glue job failure
  - Glue job timeout
  - Glue bookmark
  - DynamicFrame
  - Spark OOM
  - data skew
  - JDBC connection
  - Glue Data Catalog
  - Glue version 4.0
  - DPU capacity
  - Glue Spark UI
  - CloudWatch logs
  - Glue connection
  - crawler
  - partition pruning
  - Python shell job
  - Ray job
  - Analytics
tags:
  - glue
  - analytics
  - etl
  - troubleshoot
  - spark
  - data-catalog
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  when_to_use: >-
    Diagnosing an AWS Glue ETL job that FAILED, hit TIMEOUT, is RUNNING
    past its expected duration, is reprocessing data the bookmark should
    have skipped, is throwing Python exceptions, is unable to reach a JDBC
    source in a VPC, is reporting Spark executor OOM or stage failures, or
    is surfacing Data Catalog "table not found" / "partition not found"
    errors.
  when_not_to_use: >-
    Glue Data Quality rule evaluation (use the Data Quality service
    directly), AWS Lake Formation permission errors (use Lake Formation
    admin tooling), Glue Studio notebook interactive development (not a
    job-run diagnosis), or Glue crawler schema inference tuning (use a
    crawler classification specialist). This skill diagnoses job-run
    failures, not data quality or governance.
  activation_triggers:
    - "Glue job failed"
    - "Glue job timeout"
    - "Glue bookmark not advancing"
    - "Glue reprocessing data"
    - "Glue JDBC connection error"
    - "Glue Spark OOM"
    - "Glue stage failure"
    - "Glue table not found"
    - "Glue partition not found"
    - "DynamicFrame schema mismatch"
    - "Glue DPU capacity"
    - "Glue job RUNNING too long"
    - "Glue version 2.0 vs 3.0 vs 4.0"
    - "diagnose Glue ETL failure"
    - "Spark UI Glue"
  invocation_schema: >-
    Input: either (a) a Glue JobName + RunId + live-account context, (b)
    a pasted ErrorMessage from glue:get-job-run, OR (c) a CloudWatch Logs
    / Spark stage failure excerpt. Output: a deterministic TARGET /
    VERDICT / REASON / CATEGORY / EVIDENCE / REMEDIATION block per job
    run, where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and
    CATEGORY ∈ {SCRIPT_EXCEPTION, TIMEOUT_DPU, TIMEOUT_SKEW, JDBC_VPC,
    JDBC_CRED, BOOKMARK_STALL, CATALOG_MISSING, CATALOG_PARTITION,
    SPARK_OOM, SPARK_STAGE, DYNAMICFRAME_SCHEMA, DYNAMICFRAME_TYPE,
    UNKNOWN}.
  invocation_example: |-
    # Minimal valid input (offline classification from ErrorMessage):
    JobName: nightly-sales-aggregation
    RunId: jr_abc123def456
    State: FAILED
    ErrorMessage: "Traceback (most recent call last):
      File \"tmp/script.py\", line 47, in <module>
        df = df.withColumn('revenue', col('price') * col('qty'))
      ... AttributeError: 'NoneType' object has no attribute '_jvc'"
    ExecutionTime: 42
    GlueVersion: 4.0
    WorkerType: G.1X
    NumberOfWorkers: 5
    Emit the standard diagnostic block (TARGET, VERDICT, REASON,
    CATEGORY, EVIDENCE, REMEDIATION).
---

# Glue Job Troubleshooter

## What this skill does

Diagnoses AWS Glue ETL job failures by walking a seven-category decision
tree that maps the observed symptom (job FAILED, TIMEOUT, RUNNING too
long, or reprocessing bookmarked data) to a specific root cause with
positive evidence. The skill is verdict-driven: it never emits a fix
without first producing the failing probe that confirms the cause.

## STRICT output contract

Every invocation MUST emit exactly one diagnostic block per job run
in this shape — no prose before, no commentary after:

```text
TARGET: <job-name>/<run-id> or <job-name> if RunId unknown
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failing category and the probe>
CATEGORY: SCRIPT_EXCEPTION | TIMEOUT_DPU | TIMEOUT_SKEW |
          JDBC_VPC | JDBC_CRED | BOOKMARK_STALL | CATALOG_MISSING |
          CATALOG_PARTITION | SPARK_OOM | SPARK_STAGE |
          DYNAMICFRAME_SCHEMA | DYNAMICFRAME_TYPE | UNKNOWN
EVIDENCE:
  - <observed symptom — ErrorMessage, state, duration>
  - <failing probe — command and output that confirms the cause>
  - <passing probes — categories ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

A block missing VERDICT, CATEGORY, EVIDENCE, or REMEDIATION is a
contract violation — re-emit the full block. NEVER combine multiple job
runs in a single block; one run per block.

## Quick start

- **Start with `get-job-run` — not the script.** ErrorMessage and
  ExecutionTime narrow the category before you open the script. A short
  ExecutionTime with a Python traceback points to SCRIPT_EXCEPTION; a
  timeout at the configured Timeout minutes points to TIMEOUT_*; a long
  run with no traceback points to skew or DPU starvation.
- **Bookmark problems hide in `get-job-bookmark`.** If a job that should
  skip old data is reprocessing it, the bookmark is stale, missing, or
  tracking the wrong partition column. The bookmark is per-job.
- **JDBC failures are almost never Glue.** They are VPC security group,
  subnet route table, or self-referencing rule problems on the Glue
  connection. Verify connection SG, database SG, and route table before
  assuming a Glue bug.
- **Spark OOM is a skew or shuffling problem, not a memory problem.**
  Throwing more DPU at an OOM rarely fixes it; the fix is salting the
  skewed key, repartitioning before a wide transform, or moving to
  `G.2X` only if the executor genuinely needs more heap.
- **Glue version matters.** 2.0 = Spark 2.4 / Python 3.7; 3.0 = Spark
  3.1 / Python 3.9; 4.0 = Spark 3.3 / Python 3.10. A script that ran on
  2.0 may fail on 4.0 because of Spark SQL strictness, PyArrow
  incompatibility, or removed DataFrameWriter options.

## Mindset

A Glue job run is a Spark application wrapped in an AWS-managed control
plane. Most failures are not Glue bugs — they are configuration drift
between the job, the Data Catalog, the VPC, and the source data. The
skill's job is to find the layer that drifted. The fastest path to root
cause is to read `get-job-run` first, then narrow to the category that
matches the symptom signature, then run the category-specific probe
before opening the script.

## Quick reference — verdict thresholds

| Observation | Verdict | Category |
|---|---|---|
| `ErrorMessage` contains Python `Traceback` | **ROOT_CAUSE_FOUND** | SCRIPT_EXCEPTION |
| `ExecutionTime` == `Timeout`, no traceback | **ROOT_CAUSE_FOUND** | TIMEOUT_DPU / TIMEOUT_SKEW |
| Spark UI: one task reads 100x median bytes | **ROOT_CAUSE_FOUND** | TIMEOUT_SKEW |
| `ErrorMessage` mentions `Connection refused` / `VPC` | **ROOT_CAUSE_FOUND** | JDBC_VPC |
| `ErrorMessage` mentions `Access denied` / `auth failed` | **ROOT_CAUSE_FOUND** | JDBC_CRED |
| Source grew but `get-job-bookmark` shows old marker | **ROOT_CAUSE_FOUND** | BOOKMARK_STALL |
| `EntityNotFoundException: Table not found` | **ROOT_CAUSE_FOUND** | CATALOG_MISSING |
| `ErrorMessage` mentions `partition` + `not found` | **ROOT_CAUSE_FOUND** | CATALOG_PARTITION |
| Spark UI executor: `OOM` / `Container killed by YARN` | **ROOT_CAUSE_FOUND** | SPARK_OOM |
| Spark UI: failed stage with one slow task | **ROOT_CAUSE_FOUND** | SPARK_STAGE / TIMEOUT_SKEW |
| `ResolveChoice` / `apply_mapping` schema errors | **ROOT_CAUSE_FOUND** | DYNAMICFRAME_SCHEMA |
| `ExecutionTime` long but job succeeded, no probe run | **NEED_MORE_INFO** | (need Spark UI) |
| AWS Health event for Glue in region | **ESCALATE** | (AWS-side incident) |

## Pre-flight: data gate (run before any diagnosis)

Glue diagnosis requires three data sources: job-run metadata (state,
ErrorMessage, ExecutionTime, configuration), CloudWatch Logs excerpt for
the failing run, and — for performance/skew diagnoses — the Spark UI
event log exported to S3.

```bash
# 1. Job-run metadata
RUN_ID=jr_abc123def456
aws glue get-job-run --job-name nightly-sales-aggregation \
  --run-id $RUN_ID --output json > job-run.json

# 2. Recent runs (was this the first failure?)
aws glue get-job-runs --job-name nightly-sales-aggregation \
  --max-results 20 --output json > job-runs.json

# 3. CloudWatch Logs for the failing run (/aws-glue/jobs/output)
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/output \
  --log-stream-name $RUN_ID --filter-pattern "ERROR" \
  --output json > job-errors.json

# 4. Bookmark state (for bookmark-stall category)
aws glue get-job-bookmark --job-name nightly-sales-aggregation \
  --run-id $RUN_ID --output json > bookmark.json

# 5. Spark UI event log (when enabled via --spark-event-logs-path)
LOG_PATH=$(jq -r '.JobRun.Arguments["--spark-event-logs-path"] // empty' job-run.json)
aws s3 cp "$LOG_PATH/$RUN_ID/" ./spark-ui/ --recursive
```

### Data-quality short-circuits

| Condition | Effect on diagnosis |
|---|---|
| `get-job-run` returns `RunId not found` | Job never started under that id; verify via `get-job-runs`. |
| `ErrorMessage` is `No ErrorReason` but `State=FAILED` | Need CloudWatch Logs to surface the exception. Emit NEED_MORE_INFO with the log-fetch step. |
| CloudWatch log group missing | Logging disabled (`--enable-continuous-cloudwatch-log false`). Cannot diagnose script-level failures. NEED_MORE_INFO. |
| Spark UI not enabled | Cannot diagnose skew / OOM / stage failures with evidence. NEED_MORE_INFO; recommend `--enable-spark-ui` and `--spark-event-logs-path` for future runs. |
| `get-job-bookmark` returns `{}` | Bookmark reset or never written. Reprocessing is expected, not a bug. |
| Job still `RUNNING` (not FAILED) | Diagnose as TIMEOUT_* candidate; do NOT wait for failure if past SLA. |

When `ExecutionTime` and CloudWatch Logs disagree, trust CloudWatch for
the failure moment and `get-job-run` for overall duration. The
ExecutionTime counts the control-plane wrapper; the Spark application
may have failed earlier.

## Process — Diagnostic decision tree (apply in order)

### Step 0: Non-obvious behaviours that change the diagnosis

- **`ErrorMessage` is frequently `No ErrorReason` even when the script
  threw.** Glue's control plane surfaces a high-level state (FAILED) but
  only captures the Python traceback if continuous logging is enabled.
  Always check `--enable-continuous-cloudwatch-log` before assuming
  "no error."
- **Job timeout is the configured `Timeout` minutes, not a Spark kill.**
  A job with `Timeout: 60` that runs exactly 60 minutes and fails was
  killed by the Glue control plane. The fix is either raising `Timeout`
  or fixing the slowness — never both at once.
- **Bookmark tracks the source's partition column, not the job's
  output.** A job reading from `s3://bucket/year=2025/month=01/` with
  `partitionKeys=["year","month"]` bookmarks the highest `(year, month)`
  seen. If source layout changes to `dt=2025-01-01`, the bookmark is
  orphaned and the job reprocesses everything.
- **Glue 4.0 tightened Spark SQL strictness.** A script that ran on 3.0
  may fail on 4.0 with `SparkUpgradeException` on date parsing (Julian
  → Proleptic Gregorian calendar). Pass
  `--conf spark.sql.legacy.timeParserPolicy=LEGACY` to restore.
- **JDBC reads succeeding in dev fail in prod when the Glue connection's
  SG lacks a self-referencing rule.** The Glue ENI's own SG must allow
  egress back to itself for the database port, in addition to the
  database SG allowing ingress from the Glue SG.
- **`G.1X` vs `G.2X` changes executor heap, not just DPU count.**
  `G.1X` ≈ 6 GB executor heap; `G.2X` ≈ 12 GB. OOM on `G.1X` may resolve
  on `G.2X` — but only if the OOM is genuine heap pressure, not skew.
- **Spark UI event logs land in S3 only after the run ends.** For a live
  RUNNING job, the Spark UI is accessible from the Glue Console; for
  historical runs, the S3 path is the source of truth.
- **`NumberOfWorkers` minimum is 2 (Spark) or 1 (Ray).** Auto-scaling
  (Glue 3.0+) can lower the floor, but a static job with
  `NumberOfWorkers: 1` will fail to start.
- **Data Catalog "table not found" is usually the database name or IAM
  permission, not the table.** `EntityNotFoundException` fires when the
  table doesn't exist AND when the job's IAM role lacks `glue:GetTable`
  on it. Both look identical.

### Step 1: Job failure (Python script exceptions)

**Signature:** `ErrorMessage` contains `Traceback`, OR short
`ExecutionTime` (< 5 min) with `State=FAILED`.

**Failing probe:** CloudWatch Logs for the run, filtered to `Traceback`.

```bash
aws logs filter-log-events \
  --log-group-name /aws-glue/jobs/output \
  --log-stream-name $RUN_ID --filter-pattern "Traceback" \
  --output json
```

| Exception in trace | Root cause | Fix |
|---|---|---|
| `KeyError: '<column>'` | Schema changed since last crawl | Re-crawl; or fix script to tolerate missing column. |
| `AttributeError: 'NoneType'...` | DataFrame API on None (read returned empty) | Check source S3 path; check partition filter. |
| `ImportError: No module named '<pkg>'` | External Python package not installed | Add `--additional-python-modules` (Glue 3.0+). |
| `AnalysisException: Path does not exist` | S3 source path wrong or empty | Verify `s3://` prefix; check source crawler. |
| `SparkUpgradeException` (date parsing) | Glue version calendar change | `--conf spark.sql.legacy.timeParserPolicy=LEGACY`. |
| `Py4JJavaError` (wrapping Java) | Spark internal — read nested cause | Surface nested Java stack; route to Step 6. |
| `AnalysisException: cannot resolve '<col>'` | Typo or case-sensitivity | Glue 4.0 is case-sensitive; quote column names. |

**Passing probes:** `ExecutionTime < Timeout` (not timeout category); no
"Connection refused" (not JDBC); no YARN kill (not OOM).

### Step 2: Job timeout (DPU capacity vs long-running transform)

**Signature:** `ExecutionTime` == `Timeout` (±1 min), `State=TIMEOUT`
or `FAILED`, no Python traceback.

**Failing probe:** compare duration to `Timeout`; pull Spark UI stage
summary for task progression.

```bash
jq '{state: .JobRun.State, exec: .JobRun.ExecutionTime,
     timeout: .JobRun.Timeout, workers: .JobRun.NumberOfWorkers,
     workerType: .JobRun.WorkerType}' job-run.json
```

| Observation | Root cause | Fix |
|---|---|---|
| All tasks slow; `NumberOfWorkers` < 5 | DPU-starved | Raise `NumberOfWorkers` (min 5 for prod ETL). |
| One task running 50x median | Data skew | Salt the skewed key; repartition before wide transform. |
| Many tasks stuck on S3 `LIST`/`HEAD` | Too many small files | Compact source; `--conf spark.sql.sources.partitionOverwriteMode=dynamic`. |
| `from_catalog` slow, no partition pushdown | Full scan | Pass `push_down_predicate='year=2025 and month>=01'`. |
| JDBC read, no partition column | Single-threaded JDBC | Add `hashfield` / `hashexpression` predicate. |
| `G.1X`, executor heap exhausted | Heap pressure | Move to `G.2X` or tune `--executor-memory`. |
| Long-running Python UDF in `map`/`flatMap` | UDF serial bottleneck | Replace with native Spark SQL; broadcast hot data. |

### Step 3: JDBC connection errors (VPC, subnet, security group)

**Signature:** `ErrorMessage` mentions `Connection refused`, `timed
out`, `VPC configuration`, `Network interface`, `ENI`, or `Could not
connect`.

**Failing probe:** verify Glue connection's SG, subnet route table, and
the database SG ingress.

```bash
aws glue get-connection --name nightly-rds-conn --output json > conn.json
CONN_SG=$(jq -r '.Connection.Properties.SECURITY_GROUP_ID' conn.json)
CONN_SUBNET=$(jq -r '.Connection.Properties.SUBNET_ID' conn.json)

aws ec2 describe-security-groups --group-ids $CONN_SG --output json
aws ec2 describe-security-groups --group-ids $DB_SG --output json
aws ec2 describe-route-tables \
  --filters Name=association.subnet-id,Values=$CONN_SUBNET --output json
```

| Missing config | Symptom | Fix |
|---|---|---|
| DB SG lacks ingress from Glue SG on db port (5432/3306) | `Connection refused` / `timed out` | Add inbound: source = Glue SG, port = db port. |
| Glue SG lacks egress to DB | `timed out` (egress blocked) | Add outbound: dest = DB SG / CIDR, port = db port. |
| Glue SG lacks self-referencing rule | Intermittent ENI setup fails | Add inbound: source = Glue SG itself, all ports. |
| Subnet route table missing path to DB subnet | `timed out` | Add route via TGW / peering / LPG. |
| Glue subnet in different AZ than single-AZ DB | `Connection refused` | Use a Glue connection subnet in the DB's AZ. |
| NACL stateful mismatch | Intermittent | NACLs are stateless; check in+out on both subnets. |
| Glue connection points to deleted subnet | ENI provisioning fails | Recreate connection with current subnet. |

**Passing probes:** run `nc -vz <db-host> <port>` from a Glue dev
endpoint or EC2 in the same subnet. If `nc` succeeds, the path is clear
and the issue is authentication — route to Step "JDBC credentials"
(JDBC_CRED) and check the connection's JDBC URL / Secrets Manager
reference.

### Step 4: Job bookmark errors (not advancing, reprocessing data)

**Signature:** source S3 prefix grew, but job reprocesses files already
run. `get-job-bookmark` shows old or empty marker.

**Failing probe:**

```bash
aws glue get-job-bookmark --job-name nightly-sales-aggregation \
  --run-id $RUN_ID --output json
# Inspect: bookmark["JobBookmarks"]["Attempt"],
# "Args" / "Paths" / "partitionKeys" structure
```

| Bookmark observation | Root cause | Fix |
|---|---|---|
| Returns `{}` | Bookmark disabled or reset | `--job-bookmark-option=enable`; or accept reprocess if disabled intentionally. |
| `partitionKeys` present but source path layout changed | Layout drift | `reset-job-bookmark`; update `partitionKeys` in script. |
| `Attempt` count > 1 across runs | Bookmark write failing | Add `glue:UpdateJobBookmark` to job role. |
| Source has nested partitions not in `partitionKeys` | Job reads all sub-partitions | Recrawl; update `partitionKeys`. |
| Same S3 key reprocessed | File overwritten in place | Glue bookmarks by key — overwritten files always reprocess. Design for appends. |
| KMS-encrypted bookmark fails to read | Role lacks `kms:Decrypt` on bookmark CMK | Add KMS decrypt to job role. |
| Glue 2.0 → 3.0+ upgrade, bookmark unreadable | Bookmark schema changed | `reset-job-bookmark` once post-upgrade; accept one reprocess. |

**Passing probes:** IAM policy simulator on the job's role for
`glue:GetJobBookmark` and `glue:UpdateJobBookmark`. Both MUST be Allow.

### Step 5: Data Catalog errors (table / partition not found)

**Signature:** `ErrorMessage` mentions `EntityNotFoundException`,
`Table not found`, `Database not found`, or `Partition not found`.

**Failing probe:**

```bash
aws glue get-table --database-name analytics_prod \
  --name sales_raw --output json
aws glue get-partitions --database-name analytics_prod \
  --table-name sales_raw --output json
aws glue get-database --name analytics_prod --output json
```

| Probe result | Root cause | Fix |
|---|---|---|
| `get-table` returns `EntityNotFoundException` | Table missing | Re-run crawler; or fix job table name. |
| Table exists but in a different database | Wrong `database_name` | Fix script; database name is case-sensitive. |
| `get-partitions` empty | Crawler never ran on partitions | Re-crawl; or `MSCK REPAIR TABLE` via Athena. |
| Partition exists but job can't see it | Role lacks `glue:GetPartition` | Add `glue:GetPartition(s)` to job role. |
| `from_catalog` with stale schema | Catalog schema != S3 data | Re-crawl; or `additional_options={"useCatalogSchema": False}`. |
| Cross-account catalog access | Role lacks cross-account `glue:*` | Add resource-account IAM; use catalog ARN. |
| Lake Formation tag blocks read | LF `DESCRIBE` missing | Grant LF `DESCRIBE` on table to job role. |

### Step 6: Spark errors (executor OOM, stage failures, data skew)

**Signature:** `ErrorMessage` mentions `OutOfMemoryError`, `Container
killed by YARN`, `Java heap space`, `GC overhead limit`, or stage
failure with `Lost task` retries.

**Failing probe:** Spark UI event log — identify the failed stage, task
attempt counts, and executor memory metrics.

```bash
LOG_BUCKET=$(jq -r '.JobRun.Arguments["--spark-event-logs-path"]' job-run.json)
aws s3 ls "$LOG_BUCKET/$RUN_ID/" --recursive
# Inspect with spark-events-reader or the Glue Console "Spark UI" tab
```

| Spark symptom | Root cause | Fix |
|---|---|---|
| One task reads 100x median bytes | Data skew | Salt the skewed key: `df.withColumn("salt", (rand()*10).cast("int"))`. |
| `Container killed by YARN...memory limits` | Executor OOM | `G.1X` → `G.2X`; or reduce `spark.sql.shuffle.partitions` default. |
| Stage retries exhausted (4 attempts) | Speculative task failures | Inspect task stack; often OOM or bad input row. |
| `GC overhead limit exceeded` | Many small objects / UDF churn | Replace PyRDD UDFs with Spark SQL; broadcast small DFs. |
| Long pause before stage starts | Shuffle write bottleneck | Raise `spark.sql.shuffle.partitions` (200 → 1000+ for TB). |
| Broadcast join OOM | Broadcast hash table too large | Lower `spark.sql.autoBroadcastJoinThreshold` (default 10 MB). |
| Python worker OOM (`map`/`flatMap`) | UDF returning huge objects | Paginate; or `applyInPandas` with chunking. |

**Passing probes:** source volume consistent with previous successful
runs; if so, skew is the new factor.

### Step 7: DynamicFrame errors (schema mismatch, type coercion)

**Signature:** log mentions `ResolveChoice`, `apply_mapping`,
`Cannot coerce`, or `Category="DYNAMICFRAME"`.

**Failing probe:**

```bash
aws glue get-table --database-name analytics_prod \
  --name sales_raw --output json | jq '.Table.StorageDescriptor.Columns'
```

| Symptom | Root cause | Fix |
|---|---|---|
| `ResolveChoice` throws `CONFlict` | Multiple types across partitions | `resolve_choice(spec=...)` with explicit `cast:double` before joins. |
| `apply_mapping` fails on missing column | Schema drifted | Re-crawl; or `from_catalog(additional_options={"useCatalogSchema": False})`. |
| `Cannot coerce type string to int` | Mixed types | Cast via `to_number` in Spark SQL; or `DynamicFrame.unnest()`. |
| `DropField` errors on nested struct | Path doesn't match | Inspect actual nested path with `printSchema()`. |
| Joins produce unexpected nulls | `ResolveChoice` not called before join | `resolve_choice` on both sides before `join`. |
| `SparkSession` vs `GlueContext` mismatch | Glue 4.0 stricter | Use `DynamicFrame` for catalog reads; convert to DF only when needed. |

**Passing probes:** script ran unchanged on prior successful runs; if
so, the source schema changed (crawler drift).

### Step 8: AWS-side incident escalation

If AWS Health shows an active Glue incident in the job's region during
the run window, emit ESCALATE with the AWS Health event ARN. Do NOT
continue diagnosing script-level causes when the platform is degraded.

```bash
aws health describe-events \
  --filter eventStatusCodes=OPEN,services=GLUE \
  --region us-east-1 --output json
```

### Step 9: Final verdict

- If a single category's failing probe produced positive evidence,
  emit **ROOT_CAUSE_FOUND** with that CATEGORY.
- If two categories overlap (e.g., SCRIPT_EXCEPTION with underlying
  SPARK_OOM), pick the **most-specific** category (SPARK_OOM) and note
  the script layer in EVIDENCE.
- If a probe requires operator input (Spark UI not enabled, log group
  missing), emit **NEED_MORE_INFO** with the data gap.
- If AWS Health shows an active Glue incident, emit **ESCALATE**.

## Output format — worked examples

### Worked example — script exception

```text
TARGET: nightly-sales-aggregation/jr_abc123def456
VERDICT: ROOT_CAUSE_FOUND
REASON: CloudWatch Logs for the run contain an AttributeError on
  line 47 of the script — from_catalog returned None when the table
  was empty. ExecutionTime was 42s.
CATEGORY: SCRIPT_EXCEPTION
EVIDENCE:
  - State=FAILED, ExecutionTime=42, ErrorMessage="No ErrorReason"
  - Failing probe:
    aws logs filter-log-events --log-group-name /aws-glue/jobs/output
      --log-stream-name jr_abc123def456 --filter-pattern "Traceback"
    → AttributeError: 'NoneType' object has no attribute '_jvc'
      at line 47 (df.withColumn('revenue', col('price')*col('qty')))
  - Passing probes: ExecutionTime=42 < Timeout=60 (not TIMEOUT_*);
    no 'Connection refused' (not JDBC_VPC); no YARN kill (not OOM)
REMEDIATION:
  1. Re-crawl to confirm data is present in analytics_prod.sales_raw:
     aws glue start-crawler --name sales-raw-crawler
  2. Add a None guard in the script before line 47:
     if df is None or df.rdd.isEmpty():
         logger.warning("source empty; skipping")
         return
     df = df.withColumn("revenue", col("price") * col("qty"))
  3. Re-run with bookmark=enable to skip processed partitions:
     aws glue start-job-run --job-name nightly-sales-aggregation \
       --arguments '{"--job-bookmark-option":"enable"}'
```

### Worked example — JDBC VPC security group

```text
TARGET: orders-etl-job/jr_def789abc012
VERDICT: ROOT_CAUSE_FOUND
REASON: Glue connection nightly-rds-conn uses SG sg-glue123, but the
  database SG sg-rds456 lacks inbound on port 5432 from sg-glue123.
  The TCP SYN was dropped at the database SG.
CATEGORY: JDBC_VPC
EVIDENCE:
  - State=FAILED, ExecutionTime=18, ErrorMessage="VPC Connection error"
  - Failing probe:
    aws ec2 describe-security-groups --group-ids sg-rds456
    → IpPermissions lack port 5432 with sg-glue123 source
  - Passing probes: route table for Glue subnet reaches DB subnet;
    Glue SG has egress to 0.0.0.0/0 on 5432; last successful 3 days ago
REMEDIATION:
  1. Add inbound to database SG:
     aws ec2 authorize-security-group-ingress --group-id sg-rds456 \
       --ip-permissions IpProtocol=tcp,FromPort=5432,ToPort=5432,\
         UserIdGroupPairs=[{GroupId=sg-glue123}]
  2. Add self-referencing rule to Glue SG (idempotent):
     aws ec2 authorize-security-group-ingress --group-id sg-glue123 \
       --ip-permissions IpProtocol=-1,FromPort=-1,ToPort=-1,\
         UserIdGroupPairs=[{GroupId=sg-glue123}]
  3. Verify from a Glue dev endpoint in the same subnet:
     nc -vz orders-db.cluster-abc.us-east-1.rds.amazonaws.com 5432
  4. Re-run:
     aws glue start-job-run --job-name orders-etl-job
```

### Worked example — bookmark stall

```text
TARGET: hourly-events-rollup/jr_xyz987abc321
VERDICT: ROOT_CAUSE_FOUND
REASON: Source layout changed from year=/month= to dt= but the
  bookmark tracks (year, month). The bookmark cannot advance on the
  new layout, so the job reprocesses everything on every run.
CATEGORY: BOOKMARK_STALL
EVIDENCE:
  - Reprocessed_bytes near total source bytes on each run
  - Failing probe:
    aws glue get-job-bookmark --job-name hourly-events-rollup
    → bookmark Args partitionKeys == ["year","month"],
      but source layout is now dt=
  - Passing probes: IAM role has glue:UpdateJobBookmark (Allow);
    --job-bookmark-option=enable
REMEDIATION:
  1. Reset the bookmark (one-time; forces full reprocess once):
     aws glue reset-job-bookmark --job-name hourly-events-rollup
  2. Update the script to read from dt= and set partition_keys=["dt"].
  3. Re-crawl to register dt partitions:
     aws glue start-crawler --name events-crawler
  4. Verify subsequent runs skip processed dt partitions.
```

### Worked example — Spark OOM with data skew

```text
TARGET: big-join-batch/jr_oom456def789
VERDICT: ROOT_CAUSE_FOUND
REASON: Executor OOM in stage 7 (join on customer_id). Spark UI shows
  one task reading 380 GB vs median 1.2 GB — 316x skew. OOM is from
  shuffling the hot key, not DPU shortage.
CATEGORY: SPARK_OOM
EVIDENCE:
  - State=FAILED, ExecutionTime=23, ErrorMessage="Container killed by
    YARN for exceeding memory limits"
  - Failing probe: Spark UI stage 7 — min=12s, median=45s, max=2h17m;
    one task processed 380 GB (single customer_id "ACME-001")
  - Passing probes: NumberOfWorkers=10 (not DPU-starved);
    ExecutionTime=23 < Timeout=240; no Python traceback
REMEDIATION:
  1. Salt the skewed join key:
     hot="ACME-001"
     df_small = df_small.withColumn("join_key",
       when(col("customer_id")==hot,
         concat(col("customer_id"), lit("_"),
           (rand()*8).cast("int")))
       .otherwise(col("customer_id")))
     # Replicate df_big rows 8x for the hot key (see reference)
  2. Raise shuffle partitions before the join:
     spark.conf.set("spark.sql.shuffle.partitions", "2000")
  3. Re-run at the same DPU count (do NOT raise workers yet):
     aws glue start-job-run --job-name big-join-batch
```

### Worked example — NEED_MORE_INFO

```text
TARGET: long-running-extract/jr_qrs654tuv321
VERDICT: NEED_MORE_INFO
REASON: Job RUNNING for 90 minutes against a 60-min SLA, but Spark UI
  was not enabled for this run. Cannot determine whether slowness is
  skew, DPU starvation, or a stuck task.
CATEGORY: UNKNOWN
EVIDENCE:
  - State=RUNNING, ExecutionTime=90, Timeout=180
  - CloudWatch logs show normal progress, no errors
  - Spark UI event log path not configured
REMEDIATION:
  1. Let the current run finish (do NOT cancel; data may be valid).
  2. Enable Spark UI on the job:
     aws glue update-job --job-name long-running-extract \
       --job-update '{"DefaultArguments":{
         "--enable-spark-ui":"true",
         "--spark-event-logs-path":"s3://glue-spark-logs-us-east-1/long-running-extract/"}}'
  3. Add a bucket lifecycle policy on the Spark UI logs (30-day expiry).
  4. Re-run and re-invoke this skill with the new RunId.
```

## Anti-Patterns — NEVER do these things

- **NEVER recommend raising `NumberOfWorkers` to fix an OOM without
  checking the Spark UI skew ratio.** DPU-scale rarely fixes data skew;
  the hot key stays hot. Check `max/median task bytes`; if > 10x, skew
  is the cause and salting is the fix.
- **NEVER recommend `reset-job-bookmark` as a first response to
  reprocessing complaints.** Reset discards the marker and forces a
  one-time full reprocess. First inspect the existing bookmark; reset
  only when the source layout actually changed.
- **NEVER assume a Glue JDBC connection failure is a Glue bug.** Glue's
  ENI is the network interface; the database SG ingress is the most
  common cause. Verify SG, subnet route, and self-referencing rule
  before opening an AWS Support ticket.
- **NEVER upgrade a Glue 2.0 job to 3.0 / 4.0 in production without
  running it in dev first.** The Spark version change (2.4 → 3.1 → 3.3)
  tightens SQL strictness, changes the date/time calendar, and may
  break PyArrow/pandas UDFs.
- **NEVER diagnose "table not found" without checking the database name
  and IAM role permissions.** `EntityNotFoundException` fires identically
  when the table doesn't exist AND when the role lacks `glue:GetTable`.
- NEVER cancel a long-running RUNNING job without first checking the
  Spark UI for genuine stuckness vs normal progress. Cancelling wastes
  all work and obscures diagnostic data.
- NEVER edit the script and re-run without reproducing the failure in
  dev. The fix-and-pray loop on prod data masks whether the fix worked.
- NEVER rely solely on `ErrorMessage`. Glue's control plane summary is
  frequently `No ErrorReason` even when the script threw. Always check
  CloudWatch Logs.
- NEVER recommend `G.2X` as a blanket OOM fix. `G.2X` doubles cost per
  DPU; if the OOM is skew, the fix is salting (free).
- NEVER skip the IAM permission check when diagnosing Data Catalog
  errors. The role MUST have `glue:GetTable`, `glue:GetPartition(s)`,
  `glue:GetDatabase`, and (Lake Formation) the LF `DESCRIBE` grant.

## Quick navigation

| You want to... | Jump to |
|---|---|
| Diagnose a Python traceback | Step 1 — Script exception |
| Diagnose a job that ran to Timeout | Step 2 — Job timeout |
| Diagnose a JDBC connection failure | Step 3 — JDBC connection |
| Diagnose reprocessing data | Step 4 — Bookmark stall |
| Diagnose "table not found" | Step 5 — Data Catalog |
| Diagnose Spark OOM / skew | Step 6 — Spark errors |
| Diagnose ResolveChoice errors | Step 7 — DynamicFrame |
| Handle missing logs / Spark UI | Pre-flight data gate |
| Handle AWS Health incident | Step 8 — Escalate |
| Look up Glue version / worker types | references/glue-runtime-reference.md |

## Expert heuristic — the 60-second triage

When handed a failing Glue job and asked "what's wrong?", run this
60-second triage before deep-diving any single category:

1. **Pull `get-job-run`.** ExecutionTime vs Timeout and the ErrorMessage
   narrow the category:
   - Traceback → Step 1 (SCRIPT_EXCEPTION).
   - `ExecutionTime == Timeout` (no traceback) → Step 2 (TIMEOUT_*).
   - "Connection refused" / "VPC" → Step 3 (JDBC_VPC).
   - "Table not found" / "Partition not found" → Step 5 (CATALOG_*).
   - "OutOfMemoryError" / "YARN" → Step 6 (SPARK_OOM).
2. **Pull CloudWatch Logs.** The run's log stream surfaces the actual
   Python/Java exception even when ErrorMessage is empty.
3. **Pull `get-job-bookmark`** if the complaint is reprocessing.
4. **Pull the Glue connection's SG and subnet** if the symptom is JDBC.
5. **Pull the Spark UI** if the symptom is slowness, OOM, or stage
   failure. Without Spark UI, emit NEED_MORE_INFO rather than guessing.

If none of the five steps produces a failing probe, the category is
UNKNOWN and the next step is to enable Spark UI + continuous logging on
the next run.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`start-job-run`, `update-job`, `reset-job-bookmark`, `start-crawler`,
  `authorize-security-group-ingress`), emit and await operator approval.
  Never auto-execute remediation.
- **Never `reset-job-bookmark` in production without flagging the
  one-time full reprocess.** Confirm the operator understands the cost.
- **Never `update-job` to change `GlueVersion` outside a dev window.**
  Glue version changes are non-reversible in the job's history.
- **Never modify a security group without recording the prior rule set:**
  ```bash
  aws ec2 describe-security-groups --group-ids $SG_ID \
    --output json > sg-backup-$(date +%s).json
  ```
- **One category per maintenance window.** Script changes, SG changes,
  and bookmark resets each alter the failure surface; stacking them
  obscures which fix produced the recovery.
- **Bulk operation safety limit.** When diagnosing a fleet of failing
  jobs, slice into batches of at most 3 jobs; emit per-job REMEDIATION
  and a single CONFIRM per batch; verify each batch before proceeding.
  Never emit remediation CLI for more than 3 jobs in one output block.

## Verdict semantics

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `ROOT_CAUSE_FOUND` | A failing probe produced positive evidence for one category. | Primary — terminal for actionable findings. |
| `NEED_MORE_INFO` | A required probe is unavailable (no logs, no Spark UI, run still RUNNING). | Pre-decision — emit with the specific data gap. |
| `ESCALATE` | AWS Health shows an active Glue incident in the region during the run. | Pre-decision — surface event ARN; do NOT diagnose script-level causes. |

## Recent AWS features (2024-2026)

- **Glue version 5.0 (2025 preview):** Spark 3.5, Python 3.11, faster
  Iceberg support. Test in dev before promoting prod jobs.
- **Glue auto-scaling (Glue 3.0+, broadened 2024):** Cluster scales down
  to `--min-workers` when idle. Removes over-provisioning for spiky loads.
- **Glue Iceberg support (Glue 4.0+):** Native Iceberg reads via
  `from_catalog` with `format="iceberg"`. Bookmark behavior differs —
  Iceberg snapshots are the bookmark, not partition keys.
- **Glue Ray jobs (Glue 4.0+, 2024):** Ray workload type (Z.2X workers).
  Different failure modes from Spark; this skill covers Spark only.
- **Glue Schema Registry (2023-2024):** Avro/Protobuf/JSON schemas enforced at the DynamicFrame layer.
- **Glue flexible execution class (2024):** Lower-cost DPUs with
  potential preemption. A FAILED run on flexible execution may be
  preemption — check ErrorMessage for `FLEX_EXECUTION_PREEMPTED` before
  diagnosing.
- **Glue Data Quality (2023-2024):** Separate service; route rule failures there, not to this skill.

## Domain

AWS CloudOps / Analytics — Glue ETL job failure diagnosis.

## AWS documentation

- **AWS Glue Developer Guide** — https://docs.aws.amazon.com/glue/latest/dg/what-is-glue.html
- **Glue job bookmarks** — https://docs.aws.amazon.com/glue/latest/dg/monitor-continuations.html
- **Glue Spark UI** — https://docs.aws.amazon.com/glue/latest/dg/monitor-spark-ui.html
- **Glue connection (JDBC) properties** — https://docs.aws.amazon.com/glue/latest/dg/setup-connection.html
- **Glue worker types** — https://docs.aws.amazon.com/glue/latest/dg/add-job.html
- **Glue Continuous Logging** — https://docs.aws.amazon.com/glue/latest/dg/continuous-logging.html
- **Glue Data Catalog** — https://docs.aws.amazon.com/glue/latest/dg/populate-data-catalog.html
- **Glue version upgrades** — https://docs.aws.amazon.com/glue/latest/dg/release-upgrade-glue-30-to-40.html
- **AWS Health** — https://health.aws.amazon.com/health/status
