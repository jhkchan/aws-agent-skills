# AWS Glue Runtime Reference

Supplementary reference for the Glue Job Troubleshooter skill. Loaded
on-demand when the diagnosis needs the Glue version matrix, worker type
specs, Spark UI interpretation guidance, or the detailed bookmark and
JDBC connection behaviour.

## Glue version matrix

| Glue version | Spark | Python | Default DPU | Notes |
|---|---|---|---|---|
| 0.9 | 2.2 | 2.7 | 10 (max 100) | Deprecated. Migrate immediately. |
| 1.0 | 2.4 | 2.7 / 3.6 | 10 (max 100) | Legacy. Migrate to 3.0+. |
| 2.0 | 2.4 | 3.7 | 10 (max 100) | Introduced restartable job runs. |
| 3.0 | 3.1 | 3.9 | 10 (max 100) | Spark 3.x; tighter SQL; new memory model. |
| 4.0 | 3.3 | 3.10 | 10 (max 100) | Pandas UDF improvements; stricter schema. |
| 5.0 (preview) | 3.5 | 3.11 | 10 (max 100) | Preview; check region availability. |

Glue version also affects which `--conf` defaults are applied. Always
re-state the version when emitting remediation.

### Version-upgrade breakage patterns

| Source → Target | Likely breakage | Mitigation |
|---|---|---|
| 2.0 → 3.0 | Spark SQL nullability strictness | `--conf spark.sql.legacy.allowNullComparisonsInSetOperations=true` |
| 2.0 → 3.0 | Pandas UDF signature change (PyArrow) | Update `pandas_udf` decorators to new Iterator API. |
| 3.0 → 4.0 | Date/time calendar change (Julian → Proleptic Gregorian) | `--conf spark.sql.legacy.timeParserPolicy=LEGACY` |
| 3.0 → 4.0 | Hive external catalog stricter | Re-crawl; fix table property `external.table.purge`. |
| 4.0 → 5.0 | Iceberg v2 vs v1 default | Specify `format-version=2` explicitly on Iceberg writes. |

## Worker types

| Worker type | DPU | vCPU | Disk | Executor heap (approx) | Use case |
|---|---|---|---|---|---|
| Standard | 1 | 4 | 50 GB | ~4 GB | Legacy Glue 0.9 / 1.0 jobs. |
| G.1X | 1 | 4 | 16 GB | ~6 GB | Memory-safe default; cost-efficient. |
| G.2X | 2 | 8 | 32 GB | ~12 GB | Memory-intensive transforms; ML inference. |
| G.025X | 0.25 | 0.5 | 4 GB | ~1 GB | Streaming ETL only (Glue 3.0+). |
| Z.2X | 2 | 8 | 32 GB | n/a (Ray) | Ray jobs (Glue 4.0+); not Spark. |

`NumberOfWorkers` minimum: 2 (Spark) or 1 (Ray). For Spark streaming,
minimum is 2.

### DPU vs NumberOfWorkers

DPUs allocated = `NumberOfWorkers` (for G.1X, 1 DPU per worker). The
driver counts as 1 DPU on G.1X, so an N-worker G.1X job has N-1
executors doing work. On G.2X, the driver takes 1 DPU but the worker
count still drives executor count — confirm with the Spark UI
"Executors" tab.

## Spark UI interpretation cheat sheet

### Stage detail — task metrics

The "Tasks" table on the stage detail page exposes the per-task
distribution. The key columns:

- **Duration (min / median / max / 75th / 25th):** max / median ratio
  is the skew signal. Healthy ratio is < 3x. > 10x is severe skew. > 50x
  is a hot-key problem.
- **GC Time:** high GC Time / Duration ratio (> 30%) means executor
  heap pressure. Move to G.2X or reduce `spark.sql.shuffle.partitions`.
- **Spill (Memory) / Spill (Disk):** any non-zero spill indicates
  shuffle data exceeded memory; raise partitions or move to G.2X.
- **Input (Bytes) / Shuffle Read (Bytes):** max / median > 10x on input
  bytes is source-side skew (e.g., a hot partition key in S3). Max /
  median > 10x on shuffle read is join-side skew.

### Executors tab

- **Max Memory / Used Memory:** if any executor's Used is > 90% of Max,
  it will OOM soon.
- **Task Counts:** uneven distribution (one executor with 4x the task
  count) is a partitioning problem — repartition before the wide
  transform.

### SQL / DataFrame tab

Glue 4.0+ exposes the physical plan. Use this to confirm:

- `BroadcastHashJoin` vs `SortMergeJoin` — a broadcast on a too-large
  table is the classic OOM pattern.
- `Exchange hashpartitioning(...)` — the partition count here is
  `spark.sql.shuffle.partitions`; raise it if a single reducer is
  overloaded.
- `Filter` pushed below `Join` — partition pushdown is working; if not,
  pass `push_down_predicate` to `from_catalog`.

## Bookmark deep reference

### Bookmark lifecycle

1. Job starts with `--job-bookmark-option=enable`.
2. Glue writes the bookmark after the job's `commit` (DataSource
   `commit` for JDBC, S3 `Marker` for object stores).
3. Next run reads the bookmark at job init and prunes source partitions
   below the marker.
4. If `--job-bookmark-option=disable`, no bookmark is read or written —
   every run is a full reprocess.
5. `reset-job-bookmark` clears the marker; the next run reprocesses
   everything and re-establishes the marker.

### Bookmark failure patterns

| Pattern | Symptom | Root cause |
|---|---|---|
| Bookmark Attempt count keeps climbing | Marker write failing | IAM role lacks `glue:UpdateJobBookmark`. |
| Source partition column renamed | Full reprocess | Layout drift — bookmark's `partitionKeys` reference old column. |
| Bookmark points to a deleted partition | Job reads nothing | Source cleanup removed the marker partition; reset. |
| Cross-region source | Bookmark read slow / fails | KMS cross-region key not shared; or IAM missing `kms:Decrypt`. |
| Job ran on Glue 2.0, upgraded to 3.0 | First run reprocesses all | Bookmark serialization format changed; reset once. |
| Iceberg source | Bookmark ignored | Iceberg snapshots are the bookmark; `partitionKeys` does not apply. |

### Bookmark-safe source patterns

- **Append-only S3 keys:** Glue's bookmark is a high-water mark on the
  S3 key list. New files are picked up; overwritten files reprocess.
  Design sources as append-only.
- **JDBC sources with a monotonic column:** pass `hashfield=<column>` or
  `hashexpression=<column>` and use the bookmark to track the column's
  max value seen.
- **Iceberg sources:** rely on snapshot IDs; do NOT pass
  `--job-bookmark-option` (it's a no-op for Iceberg).

## JDBC connection deep reference

### Glue connection components

A Glue connection is a stored network configuration (subnet, security
group, JDBC URL, optional Secrets Manager reference). When a job uses
the connection, Glue provisions an ENI in the connection's subnet and
attaches the connection's SG. The ENI lives only for the job's
duration.

### The four-rule network path

For a JDBC read to succeed, four security-group / network rules MUST
align:

1. **Database SG inbound** — allow the Glue connection's SG on the db
   port (e.g., 5432, 3306, 1433, 1521, 5439).
2. **Glue connection SG egress** — allow the database's IP / SG /
   CIDR on the db port. The default `0.0.0.0/0` egress usually suffices,
   but a locked-down SG may block it.
3. **Glue connection SG self-referencing rule** — allow the Glue SG to
   talk to itself on all ports. Without this, the ENI's control plane
   setup intermittently fails.
4. **Route table** — the Glue connection's subnet MUST have a route to
   the database's subnet (via VPC peering, TGW, or LPG for cross-VPC).

### Common JDBC failure signatures

| ErrorMessage | Likely missing rule |
|---|---|
| `Connection refused` | Database SG inbound on db port |
| `Connection timed out` | Route table or NACL |
| `VPC Connection error: Failed to provision ENI` | Subnet deleted, or IP exhausted in subnet |
| `Access denied for user` | JDBC credentials (Secrets Manager or URL) — not network |
| `SSL connection required` | Database enforces TLS; add `?sslmode=require` to JDBC URL |
| `FATAL: no pg_hba.conf entry` | Database-side IP allowlist; add Glue subnet CIDR |

## Glue job argument reference

| Argument | Purpose | Default |
|---|---|---|
| `--job-bookmark-option` | `enable` / `disable` / `pause` | `disable` on creation |
| `--enable-spark-ui` | Surface Spark UI link in console | `false` |
| `--spark-event-logs-path` | S3 path for event logs | (none) |
| `--enable-continuous-cloudwatch-log` | Stream CloudWatch Logs live | `true` (Glue 2.0+) |
| `--enable-metrics` | Push Spark metrics to CloudWatch | `true` |
| `--enable-glue-datacatalog` | Use Glue as the Hive metastore | `true` (Glue 3.0+) |
| `--use-glue-datacatalog-schema` | Force catalog schema on DynamicFrame | `false` |
| `--additional-python-modules` | Pip install extra packages | (none) |
| `--extra-jars` | Extra JARs on the classpath | (none) |
| `--conf` | Spark configuration override | (none) |
| `--min-workers` / `--max-workers` | Auto-scaling range (Glue 3.0+) | = `NumberOfWorkers` |

## Spark conf defaults that matter for Glue

| Conf | Glue default | When to change |
|---|---|---|
| `spark.sql.shuffle.partitions` | 200 | Raise to 1000+ for TB-scale joins. |
| `spark.sql.autoBroadcastJoinThreshold` | 10 MB | Lower if broadcast OOMs. |
| `spark.sql.adaptive.enabled` | `true` (Glue 3.0+) | Leave on; AQE handles skew partially. |
| `spark.sql.adaptive.skewJoin.enabled` | `true` (Glue 3.0+) | Leave on; salt only if AQE is insufficient. |
| `spark.sql.legacy.timeParserPolicy` | `EXCEPTION` (Glue 4.0) | Set `LEGACY` if date strings use the old calendar. |
| `spark.sql.sources.partitionOverwriteMode` | `static` | Set `dynamic` for partition-aware overwrites. |
| `spark.executor.memory` | worker-type default | Override only after profiling. |
| `spark.executor.cores` | worker-type default | Override only after profiling. |
| `spark.openlineage.transport.url` | (none) | Set if integrating with a lineage backend. |

## CloudWatch Logs structure

Glue writes to up to three log groups per job:

- `/aws-glue/jobs/output` — the standard output and error stream
  (Python `print`, logger.info, exceptions). Log stream name = RunId.
- `/aws-glue/jobs/error` — error-only stream (filtered from above).
- `/aws-glue/jobs/output-v2` — continuous logging (Glue 2.0+) with
  structured driver / executor / heartbeats. Log stream name =
  `<RunId>-<attempt>`.

For diagnosis, always pull `/aws-glue/jobs/output` first (it has the
Python traceback). Pull `output-v2` only if you need per-executor
detail.

## AWS Health escalation

Before attributing a failure to a Glue bug, check AWS Health for active
incidents on the Glue service in the job's region:

```bash
aws health describe-events \
  --filter eventStatusCodes=OPEN,services=GLUE \
  --region us-east-1 --output json
```

If an event is open in the job's region during the failure window,
emit ESCALATE with the event ARN. Do NOT continue script-level
diagnosis when the platform is degraded — re-run after AWS resolves
the incident.

## Helpful error-string lookup table

| ErrorMessage substring | Most likely CATEGORY |
|---|---|
| `Traceback (most recent call last)` | SCRIPT_EXCEPTION |
| `Container killed by YARN` | SPARK_OOM |
| `GC overhead limit exceeded` | SPARK_OOM |
| `Connection refused` / `timed out` / `VPC` | JDBC_VPC |
| `Access denied` / `authentication failed` | JDBC_CRED |
| `EntityNotFoundException` (Table / Database) | CATALOG_MISSING |
| `partition ... not found` | CATALOG_PARTITION |
| `ResolveChoice` / `Cannot coerce` | DYNAMICFRAME_SCHEMA / TYPE |
| `Lost task` (retried N times) | SPARK_STAGE |
| `FLEX_EXECUTION_PREEMPTED` | (preemption; re-run, not a real failure) |
| `No ErrorReason` | Pull CloudWatch Logs to classify |
