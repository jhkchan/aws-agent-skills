# Glue Worker Type and DPU Reference Guide

Supplementary reference for the Glue Job Failure Troubleshooter skill.
Loaded on-demand when a diagnostic needs worker-type specifications,
DPU allocation rules, executor mapping, or performance-tuning guidance.

## Worker types

| WorkerType | DPU per worker | Spark executors per worker | Heap per executor | Max workers | Min workers | Use case |
|---|---|---|---|---|---|---|
| `G.025X` | 0.0625 | 0 (no Spark) | 1 GB total | 1 | 1 | Python shell only |
| `G.1X` | 1 | 1 | 10 GB | 299 | 2 | Default Spark; small-to-medium datasets |
| `G.2X` | 2 | 2 | 10 GB each (20 GB total) | 299 | 2 | Spark-optimised; large datasets, wide transformations |

### Key sizing rules

- **G.2X doubles executor parallelism vs G.1X** for the same worker
  count. 10 workers on G.1X = 10 executors; 10 workers on G.2X = 20
  executors. Each executor handles half the data, halving the per-
  executor memory pressure.
- **G.025X cannot run Spark.** It provides 0.0625 DPU per worker with
  1 GB of memory and no Spark executor. It is exclusively for Python
  shell jobs (`Command.Name: pythonshell`). A Spark ETL job
  (`Command.Name: glueetl`) on G.025X produces chronic OOM.
- **Minimum workers for G.1X and G.2X is 2** (1 driver + 1 executor).
  The driver consumes 1 DPU and does not run executors.
- **Maximum workers is 299** for G.1X and G.2X.
- **DPU cost**: G.1X = 1 DPU/hour per worker; G.2X = 2 DPU/hour per
  worker. The driver DPU is additional. 10 G.2X workers = 22 DPUs
  (20 executor + 2 driver).

### When to switch from G.1X to G.2X

| Symptom | Recommendation |
|---|---|
| `Container killed by YARN` on G.1X with large dataset | Switch to G.2X (doubles executor count, halves per-executor data) |
| Wide transformations (joins, groupBy) on G.1X cause OOM | Switch to G.2X (more executors for shuffle parallelism) |
| Job runs slowly on G.1X but does not OOM | Increase NumberOfWorkers first; switch to G.2X if still slow |
| Python shell job only | Use G.025X (cost-effective for non-Spark) |
| ML inference or heavy UDFs | Use G.2X (more vCPU per worker) |

### When to increase NumberOfWorkers vs switch worker type

- **Increase workers** when the job is CPU-bound (not enough
  parallelism). More workers = more executors = more task slots.
- **Switch to G.2X** when the job is memory-bound (each executor
  holds too much data). G.2X does not increase per-executor heap (10
  GB each), but doubles the executor count so each handles half the
  data.
- **Both** when the dataset is very large and both parallelism and
  per-executor memory are tight.

## Job configuration commands

```bash
# Get the job configuration
aws glue get-job --job-name <name> --output json | \
  jq '.Job.{WorkerType, NumberOfWorkers, Timeout, GlueVersion, Command, Role, DefaultArguments, SecurityConfiguration}'

# Update worker type and worker count
aws glue update-job --job-name <name> \
  --job-update '{"WorkerType":"G.2X","NumberOfWorkers":10}'

# Update timeout (in minutes)
aws glue update-job --job-name <name> \
  --job-update '{"Timeout":300}'

# Start a job run
aws glue start-job-run --job-name <name> \
  --arguments '{"--job-bookmark-option":"job-bookmark-enable"}'

# Get job run details
aws glue get-job-run --job-name <name> --run-id <run-id> --output json | \
  jq '.JobRun.{JobRunState, ExecutionTime, ErrorMessage, Arguments, CompletedOn, StartedOn}'

# Get recent job runs
aws glue get-job-runs --job-name <name> --output json | \
  jq '.JobRuns[] | {JobRunId, JobRunState, ExecutionTime, ErrorMessage, StartedOn}'
```

## Job run states

| State | Effect |
|---|---|
| `STARTING` | Job is being provisioned. |
| `RUNNING` | Job is executing. |
| `STOPPING` | Operator cancelled; job is shutting down. |
| `STOPPED` | Operator cancelled; run was stopped. |
| `SUCCEEDED` | Job completed successfully. |
| `FAILED` | Job encountered an error. `ErrorMessage` identifies the category. |
| `TIMEOUT` | Job exceeded the configured `Timeout` (default 150 min = 2.5h). |
| `ERROR` | Job encountered a system error (rare; usually AWS-side). |

## GlueVersion matrix

| GlueVersion | Spark version | Python | Notes |
|---|---|---|---|
| `glue-3.0` | Spark 3.1.1 | Python 3.7 | Legacy; deprecated |
| `glue-4.0` | Spark 3.3.0 | Python 3.10 | Current default |
| `glue-5.0` | Spark 3.5.0 | Python 3.11 | Latest (2024-2025) |

Always check `GlueVersion` against the current support list. Jobs on
`glue-3.0` may block updates and should be migrated to `glue-4.0` or
`glue-5.0`.

## CloudWatch metrics for Glue jobs

| Metric | What it measures | When to use |
|---|---|---|
| `glue.executor.memory.maxUsed` | Max heap used per executor | OOM diagnosis; compare against 10 GB heap |
| `glue.executor.memory.used` | Current heap per executor | Memory trend within a run |
| `glue.executor.cpuSystemTime` / `cpuUserTime` | CPU usage per executor | CPU-bound diagnosis |
| `glue.executor.activeTasks` | Active tasks per executor | Parallelism; skew detection |
| `glue.executor.completedTasks` | Completed tasks per executor | Progress tracking |
| `glue.driver.memory.maxUsed` | Driver heap | Driver OOM (rare) |
| `glue.ALL_Stage` | Per-stage task counts | Stage-level progress via Spark UI |

Metrics require `--enable-metrics` in the job's arguments. Without
this flag, the metrics dashboard is empty.

```bash
# Check if metrics are enabled
aws glue get-job --job-name <name> --output json | \
  jq '.Job.DefaultArguments["--enable-metrics"]'

# Query executor memory usage
aws cloudwatch get-metric-statistics --namespace Glue \
  --metric-name glue.executor.memory.maxUsed \
  --dimensions Name=JobName,Value=<name> \
  --start-time $(date -d '-2 hours' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output json
```

## Spark UI

Spark UI provides the DAG (execution plan), stage details, and task-
level metrics. It is the only way to diagnose wide transformations,
shuffle skew, and executor-level issues.

```bash
# Check if Spark UI is enabled
aws glue get-job --job-name <name> --output json | \
  jq '.Job.DefaultArguments["--enable-spark-ui"], .Job.DefaultArguments["--spark-event-logs-path"]'
```

Requirements:
- `--enable-spark-ui` must be set to `true`.
- `--spark-event-logs-path` must point to an S3 path where Glue can
  write Spark event logs.
- The job's IAM role must have `s3:PutObject` on the S3 path.

After a job run, the Spark UI is accessible from the Glue Console
(job run detail page) for up to 30 days.

## Common DPU allocation failure patterns

| Pattern | Cause |
|---|---|
| Job succeeded on 50 GB, fails on 250 GB with YARN OOM | Dataset grew; G.1X executors now handle too much data. Switch to G.2X or add workers. |
| Job OOMs on the first run after a GlueVersion upgrade | New Spark version has different memory defaults. Check executor heap. |
| Job OOMs intermittently (some runs OK, some fail) | Data skew — one partition is much larger. Repartition or use salting. |
| Job OOMs on a wide join | Shuffle produces too much data per executor. Use broadcast join for small dimensions, or switch to G.2X. |
| Job never OOMs but runs very slowly | CPU-bound or I/O-bound. Increase workers (CPU) or check S3 throughput. |
| Python shell job OOMs | G.025X (1 GB) is too small. There is no larger Python shell worker; optimise the script. |

## DynamicFrame vs DataFrame performance

| Aspect | DynamicFrame | DataFrame |
|---|---|---|
| Convenience | High (Glue-native, schema inference) | Moderate (Spark-native) |
| Performance | Overhead from DynamicFrame serialisation | Native Spark performance |
| Use case | Exploratory, schema-flexible | Production, large-scale ETL |
| Conversion | `dynamicframe.toDF()` | `df.toDF()` (from DynamicFrame) |

Best practice: use DynamicFrame for the initial read (from_catalog),
then immediately convert to DataFrame (`dynamicframe.toDF()`) for all
transformations. This minimises DynamicFrame overhead while keeping
the convenient catalog integration.
