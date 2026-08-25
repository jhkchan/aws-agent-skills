# Advanced Patterns — Glue Job Failure Troubleshooter

Expert-knowledge deep dives moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Philosophy — four behaviours of a senior Glue engineer

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

## Step 0: Operational gotchas that change diagnosis

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

