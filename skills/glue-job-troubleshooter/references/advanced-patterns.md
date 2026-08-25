# Advanced Patterns — Glue Job Troubleshooter

Expert-knowledge deep dives moved verbatim from SKILL.md (progressive disclosure — load on demand).

## Step 0: Non-obvious behaviours that change the diagnosis

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

