---
name: athena-query-optimizer
description: >-
  Optimizes Amazon Athena query performance and cost via a layered analysis
  framework covering partitioning (partition projection, dynamic partition
  pruning), file format selection (Parquet vs CSV vs JSON — Parquet is 10-100x
  faster via columnar pruning), compression (Snappy vs GZIP vs ZSTD),
  bucketing for JOIN optimization, workgroup settings (data scanned limits,
  query timeout), CTAS (CREATE TABLE AS SELECT for materialization), query
  rewriting (avoid SELECT *, enforce partition filters, use APPROXIMATE
  functions), and cost modeling ($5/TB scanned). Supports Athena query result
  reuse, Athena federated queries, and Spark notebook integration. Emits a
  deterministic verdict (OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL) with
  estimated cost and performance impact. Use for Athena cost reduction, slow
  query tuning, partition projection setup, file format migration, or workgroup
  spend limits.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline recommendation classification works from pasted DDL, EXPLAIN
  output, and query history. Live-account optimization uses aws athena
  get-query-execution, start-query-execution, batch-get-query-execution,
  get-work-group, aws ce get-cost-and-usage for Athena spend, aws glue
  get-table, get-partitions for table metadata, and aws s3 ls for data lake
  layout inspection (AWS CLI v2, SSO or key-based credentials).
keywords:
  - Athena
  - query optimization
  - partitioning
  - partition projection
  - Parquet
  - columnar format
  - Snappy
  - compression
  - bucketing
  - workgroup
  - data scanned
  - CTAS
  - materialization
  - SELECT *
  - APPROXIMATE
  - $5/TB
  - result reuse
  - federated queries
  - Spark notebook
tags: [aws, athena, analytics, optimize, query-performance, cost-optimization, partitioning, parquet]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Analytics
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL"
  when_to_use: >-
    Optimizing Athena query performance and cost: reducing data scanned via
    partitioning and columnar formats, setting up partition projection,
    evaluating CTAS for materialization, tuning workgroup settings (data
    scanned limits, query timeout), rewriting queries (avoid SELECT *, add
    partition filters, use APPROXIMATE functions), or planning a file format
    migration from CSV/JSON to Parquet.
  when_not_to_use: >-
    Troubleshooting Athena query failures (use a troubleshoot skill), auditing
    Athena workgroup security (use the audit-athena-workgroup skill), building
    a data lake from scratch (use a deploy skill), or Athena Glue crawler
    troubleshooting (use a Glue troubleshoot skill). This skill focuses on
    performance and cost optimization.
  activation_triggers:
    - "optimize Athena query"
    - "Athena query slow"
    - "Athena cost reduction"
    - "Athena partition projection"
    - "Athena file format Parquet"
    - "Athena CTAS optimization"
    - "Athena data scanned limit"
    - "Athena workgroup settings"
    - "Athena SELECT * optimization"
    - "Athena $5/TB scanned"
    - "Athena result reuse"
    - "Athena federated query"
    - "reduce Athena spend"
    - "Athena query timeout"
    - "Athena bucketing"
  invocation_schema: >-
    Input: either (a) an Athena query or workload description with table DDL
    and query patterns, OR (b) live-account context with workgroup, database,
    table, and query history. Output: a deterministic TARGET / VERDICT / REASON
    / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block where VERDICT
    is one of {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL} and
    RECOMMENDATION includes file format, partitioning strategy, query rewrite,
    workgroup config, and materialization (CTAS) guidance.
---

# Athena Query Optimizer

## Quick start

- **Data scanned is the cost driver.** Athena charges $5/TB scanned. The
  fastest path to savings is reducing data scanned: partition pruning (filter
  by partition column), columnar pruning (Parquet — only read needed columns),
  and CTAS materialization (pre-compute aggregations).
- **Decision framework (apply in order):**
  - File format: CSV/JSON → Parquet (10-100x faster, 50-90% less scanned).
  - Partitioning: unpartitioned → partition by date/time column. Partitioned
    → add partition projection if > 100K partitions.
  - Query rewriting: SELECT * → SELECT specific columns; missing WHERE on
    partition column → add filter; COUNT(DISTINCT) → APPROX_COUNT_DISTINCT.
  - Workgroup: no data scanned limit → set one. No timeout → set one.
  - CTAS: repeated full-table scans → materialize the aggregation.
  - Advanced: bucketing for JOIN-heavy workloads, result reuse for repeated
    queries.
- **Parquet + Snappy is the default recommendation.** Columnar storage +
  fast decompression = 10-100x faster scans and 50-90% less data read. Every
  CSV/JSON table in Athena is an optimization opportunity.
- **$5/TB makes small wins matter.** A query scanning 500 GB costs $2.50. If
  it runs 100 times/day, that is $250/day = $7,500/month. Partition pruning
  to scan 10 GB drops it to $150/month.

## STRICT output contract

Every optimization response MUST emit this block per target (table, query, or
workgroup). No prose before or after the block.

```text
TARGET: <database/table | query-id | workgroup>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <file format | partitioning | query pattern | workgroup config>
  Proposed: <file format | partitioning | query pattern | workgroup config>
  File format: <CSV | JSON | Parquet | ORC>
  Compression: <none | GZIP | Snappy | ZSTD>
  Partitioning: <none | date column | partition projection>
  Query rewrite: <avoid SELECT * | add partition filter | APPROXIMATE | none>
  Workgroup: <data scanned limit | query timeout | result reuse>
  CTAS: <materialization target | none>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Cost (monthly): $<amount>  (<current scan> → <proposed scan>)
  Performance: <current runtime> → <proposed runtime>
  Data scanned per query: <current> → <proposed>
  Annual total: $<amount>
  Assumptions: <$5/TB, query frequency, etc.>
MIGRATION_STEPS:
  1. <specific action with DDL or CLI command>
  2. <verification step>
CONFIRM: Before executing any CTAS or workgroup config change, emit and await
  operator approval.
```

Do NOT omit any field. If a field is not applicable, write `N/A` with a
one-line reason.

## Quick navigation

| Section | What it covers | When to read |
|---|---|---|
| **Quick start** | Decision framework order, Parquet rule of thumb | First read |
| **STRICT output contract** | Mandatory output block format | Before emitting |
| **Mindset** | Data-scanned-first philosophy, Parquet dominance | Understanding |
| **Quick reference** | Verdict thresholds | Classifying findings |
| **Pre-flight** | Data gate — query history, DDL, data lake layout | Before decisions |
| **Process** | Ordered optimization steps (1-10) | Choosing recommendations |
| **Output format** | Worked example (OPPORTUNITY_FOUND) | Formatting |
| **Expert heuristic** | Non-obvious Athena behaviours table | Complex decisions |
| **NEVER** | Top 5 anti-patterns | Before remediation |
| `references/` | CLI commands, worked examples, full heuristics | Deep reference |

## Mindset

Athena optimization is a layered decision. Four behaviours separate a senior
analytics engineer from a generalist:

- **Data scanned is the only cost lever.** Athena charges by bytes read from
  S3, not by compute time. Reducing data scanned is the ONLY way to reduce
  cost. Everything else (compression, caching, result reuse) reduces bytes
  read as a side effect.
- **File format is the highest-leverage single change.** Switching from CSV
  to Parquet reduces data scanned by 50-90% (columnar pruning + compression)
  and improves query speed by 10-100x. This is always Step 1.
- **Partitioning amplifies file format gains.** A Parquet table partitioned
  by date lets a query scanning one day of a year-long dataset read 1/365th
  of the data. Unpartitioned, it scans the full table even in Parquet.
- **Workgroup settings prevent runaway spend.** A data-scanned limit caps
  the worst-case cost of any single query. Without it, a single `SELECT *`
  on a petabyte table costs $5,000.

## Quick reference — verdict thresholds

| Observation | Verdict | Recommendation |
|---|---|---|
| Table in CSV or JSON format | OPPORTUNITY_FOUND (file format) | Step 2 — CTAS to Parquet + Snappy |
| Table unpartitioned, queries filter by date/time | OPPORTUNITY_FOUND (partitioning) | Step 3 — add partition column + ALTER TABLE |
| Partitioned table with > 100K partitions, slow metadata ops | OPPORTUNITY_FOUND (partition projection) | Step 4 — enable partition projection |
| Query uses `SELECT *` | OPPORTUNITY_FOUND (query rewrite) | Step 6 — select only needed columns |
| Query scans full table without partition filter | OPPORTUNITY_FOUND (query rewrite) | Step 6 — add WHERE on partition column |
| Repeated full-table aggregation scan | OPPORTUNITY_FOUND (CTAS) | Step 7 — materialize the aggregation |
| Workgroup has no data scanned limit | OPPORTUNITY_FOUND (workgroup) | Step 8 — set data scanned limit |
| Parquet + partitioned + partition projection + tight queries | ALREADY_OPTIMAL | None — continue monitoring |
| Post-remediation: changes applied and verified | OPTIMIZED | None — verification passed |

## Pre-flight: data gate (run before any optimization decision)

**Required data:** table DDL (file format, partition columns, compression),
query history (data scanned per query, frequency), and data lake S3 layout.
Key commands: `aws glue get-table`, `aws glue get-partitions`,
`aws athena batch-get-query-execution`, `aws s3 ls`.

Full CLI sequences in `references/athena-optimization-reference.md`.

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| No query history available | MEDIUM confidence; base estimates on DDL + S3 size |
| Table not in Glue catalog | NEED_MORE_INFO: register in Glue first |
| Federated query (non-S3 source) | Different cost model — connector-dependent; not $5/TB |
| Table has 0 bytes (empty) | Skip — no cost to optimize |

## Process — Optimization logic (apply in order)

### Step 1: Validate input and data sufficiency

Gather DDL and query history:

```bash
# Table DDL and properties:
aws glue get-table --database-name <db> --name <table> \
  --query 'Table.{Storage:StorageDescriptor,Partitions:Parameters,Compression:Parameters.compression}'

# Query history (last 50 queries on this workgroup):
aws athena list-query-executions --work-group <wg> --max-results 50 \
  --query 'QueryExecutionIds'

# Batch get execution details (data scanned, runtime, status):
aws athena batch-get-query-execution \
  --query-execution-ids <id1> <id2> <id3> \
  --query 'QueryExecutions[*].{Query:Query,Scanned:Statistics.DataScannedInBytes,Runtime:Statistics.EngineExecutionTimeInMillis,State:Status.State}'
```

### Step 2: File format optimization (highest-leverage single change)

| Current format | Target format | Speedup | Data scanned reduction |
|---|---|---|---|
| CSV (row-based, no compression) | Parquet + Snappy | 10-100x | 50-90% |
| JSON (row-based) | Parquet + Snappy | 10-50x | 50-80% |
| Parquet + uncompressed | Parquet + Snappy | 2-3x | 20-40% |
| Parquet + GZIP | Parquet + Snappy | 1.5-2x | 5-15% (Snappy faster, similar ratio) |
| ORC + ZSTD | Keep (already columnar) | — | — |

**Parquet vs CSV anatomy:** CSV is row-based and stores all columns for each
row. A query selecting 3 of 50 columns still reads all 50 columns. Parquet is
columnar: a query selecting 3 of 50 columns reads only those 3 columns from
disk. This is columnar pruning, and it is the #1 reason Parquet is 10-100x
faster.

**CTAS migration to Parquet:**

```sql
-- Create the Parquet table from the CSV table:
CREATE TABLE <db>.<table>_parquet
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  external_location = 's3://<bucket>/<prefix>/parquet/'
) AS
SELECT * FROM <db>.<table>_csv;
```

### Step 3: Partitioning optimization

Partitioning splits data into S3 subdirectories by column value. Queries with
a WHERE clause on the partition column read only the matching partitions.

| Partitioning state | Recommendation |
|---|---|
| Unpartitioned, queries filter by date/time | Add partition by date (e.g., `dt='2026-08-01'`) |
| Partitioned by high-cardinality column (e.g., user_id) | Switch to bucketing or secondary partition by date |
| Over-partitioned (> 100K partitions) | Enable partition projection (Step 4) |
| Partitioned by hour (too many small files) | Consolidate to daily partitions |

**Add partitioning via CTAS:**

```sql
CREATE TABLE <db>.<table>_partitioned
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  partitioned_by = ARRAY['dt'],
  external_location = 's3://<bucket>/<prefix>/partitioned/'
) AS
SELECT col1, col2, ..., date_format(event_time, '%Y-%m-%d') AS dt
FROM <db>.<table>_unpartitioned;
```

**Optimal partition size:** 100 MB - 1 GB per partition file. Too many small
files (< 100 MB) cause S3 request overhead. Too few large files (> 1 GB)
reduce parallelism.

### Step 4: Partition projection

Partition projection lets Athena calculate partition values mathematically
instead of querying Glue for each partition. Essential for tables with
10K-100K+ partitions.

**When to use:** Glue `get-partitions` is slow (> 5s), partition count >
100K, or partitions follow a predictable pattern (date ranges, integer
ranges).

```sql
-- Enable partition projection on an existing table:
ALTER TABLE <db>.<table> SET TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.dt.type' = 'date',
  'projection.dt.range' = '2024-01-01,2026-12-31',
  'projection.dt.format' = 'yyyy-MM-dd',
  'projection.dt.interval' = '1',
  'projection.dt.interval.unit' = 'DAYS',
  'storage.location.template' = 's3://<bucket>/<prefix>/${dt}'
);
```

Partition projection eliminates the need for `MSCK REPAIR TABLE` or
`ALTER TABLE ADD PARTITION` — Athena auto-discovers partitions within the
configured range.

### Step 5: Compression optimization

| Compression | Ratio | Speed | Recommendation |
|---|---|---|---|
| None (uncompressed) | 1:1 | Fastest read | Never use for Athena |
| Snappy | ~3:1 | Fastest decompression | **Default for Parquet** |
| GZIP | ~4:1 | 2-3x slower than Snappy | Use for cold storage; hurts query speed |
| ZSTD | ~4:1 | Between Snappy and GZIP | Good for large datasets; level 3-9 |
| LZ4 | ~2.5:1 | Faster than Snappy | Alternative for latency-sensitive |

**Rule of thumb:** Use Snappy for Parquet (best speed/ratio balance). Avoid
GZIP for Athena queries — the decompression overhead outweighs the better
compression ratio for query workloads. ZSTD is a good upgrade from Snappy for
very large datasets where the better ratio reduces S3 GET costs.

### Step 6: Query rewriting

| Pattern | Problem | Fix | Impact |
|---|---|---|---|
| `SELECT *` | Reads all columns, even unused | `SELECT col1, col2` (only needed) | 50-90% scan reduction |
| No WHERE on partition column | Full table scan | `WHERE dt >= '2026-07-01'` | Proportional to partition pruning |
| `COUNT(DISTINCT col)` | Exact count is expensive | `APPROX_COUNT_DISTINCT(col)` | 10-50x faster, < 3% error |
| `ORDER BY` without `LIMIT` | Sorts entire dataset | Add `LIMIT N` or use window functions | Reduces sort overhead |
| `LIKE '%pattern%'` | Full scan, no optimization | Use string functions or pre-process | Variable |
| Repeated subqueries | Recomputes same data | Use CTE (WITH) or materialize via CTAS | Eliminates redundant scans |
| `JOIN` on unbucketed large tables | Shuffle-heavy | Bucket both tables on join key (Step 9) | Eliminates shuffle |
| `UNION` (not `UNION ALL`) | Deduplication overhead | Use `UNION ALL` if no dupes expected | Eliminates sort |

```sql
-- Before (scans all columns + all partitions):
SELECT * FROM sales WHERE amount > 100;

-- After (only needed columns + partition filter):
SELECT order_id, customer_id, amount
FROM sales
WHERE dt >= '2026-07-01' AND amount > 100;
```

### Step 7: CTAS materialization

If a query (or query pattern) runs frequently and scans a large table to
produce a small result, materialize it with CTAS.

**When to use CTAS:**
- Daily/weekly aggregation queries scanning raw event data.
- Complex JOINs that produce a denormalized reporting table.
- Queries that scan > 100 GB to produce < 1 GB of results.

```sql
-- Materialize a daily aggregation from raw events:
CREATE TABLE <db>.daily_summary
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  partitioned_by = ARRAY['dt'],
  external_location = 's3://<bucket>/curated/daily_summary/'
) AS
SELECT
  date_trunc('day', event_time) AS day,
  product_id,
  COUNT(*) AS event_count,
  SUM(amount) AS total_amount
FROM <db>.raw_events
WHERE dt >= '2026-01-01'
GROUP BY 1, 2;
```

**Cost trade-off:** The CTAS itself scans data once (costs $X). Subsequent
queries on the materialized table scan far less (costs $X/N per query).
Break-even depends on query frequency. If the daily summary is queried 10+
times/day, CTAS pays for itself within a day.

### Step 8: Workgroup settings

| Setting | Purpose | Recommendation |
|---|---|---|
| Data scanned limit (bytes) | Caps worst-case cost per query | Set to p99 of healthy queries × 2 |
| Query timeout (minutes) | Prevents runaway queries | 30 min for interactive; 6 hours for batch |
| Requester pays | Shifts cost to query requester | Enable for shared workgroups |
| Result reuse | Caches identical query results | Enable for dashboard workloads |
| Enforced workgroup config | Prevents users from bypassing limits | Set `EnforceWorkGroupConfiguration: true` |

```bash
# Update workgroup with data scanned limit:
aws athena update-work-group \
  --work-group <wg> \
  --configuration '{
    "ResultConfiguration": {"OutputLocation": "s3://<bucket>/results/"},
    "EnforceWorkGroupConfiguration": true,
    "PublishCloudWatchMetricsEnabled": true,
    "BytesScannedCutoffPerQuery": 10737418240,
    "EngineVersion": {"SelectedEngineVersion": "Athena engine version 3"}
  }'
```

**Data scanned limit of 10 GB** caps any single query at $0.05. Adjust
based on your workload's normal query sizes.

### Step 9: Bucketing for JOIN optimization

Bucketing pre-splits data into N files by a hash of the bucket column.
When two tables are bucketed on the same join key with the same bucket
count, Athena can perform a bucket-map JOIN without shuffling.

```sql
-- Create bucketed tables for a large JOIN:
CREATE TABLE <db>.orders_bucketed
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  bucketed_by = ARRAY['customer_id'],
  bucket_count = 256,
  external_location = 's3://<bucket>/bucketed/orders/'
) AS SELECT * FROM <db>.orders;

CREATE TABLE <db>.customers_bucketed
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  bucketed_by = ARRAY['customer_id'],
  bucket_count = 256,
  external_location = 's3://<bucket>/bucketed/customers/'
) AS SELECT * FROM <db>.customers;
```

**When bucketing helps:** Large-table-to-large-table JOINs (both > 10 GB).
Not helpful for dimension tables < 1 GB (Athena broadcasts small tables
automatically).

### Step 10: Impact estimation and final verdict

```
File format savings = (csv_bytes_scanned - parquet_bytes_scanned) * $5/TB * query_freq
Partition pruning savings = (full_table_scan - partition_scan) * $5/TB * query_freq
CTAS savings = (raw_scan - materialized_scan) * $5/TB * query_freq - ctas_creation_cost
```

Verdict: any dimension with a concrete recommendation → **OPPORTUNITY_FOUND**.
All dimensions pass → **ALREADY_OPTIMAL**. Changes applied and verified →
**OPTIMIZED**.

## Output format

See STRICT output contract above. Worked example below. Additional examples
(CSV to Parquet migration, ALREADY_OPTIMAL, NEED_MORE_INFO) in
`references/athena-optimization-reference.md`.

### Worked example — CSV to Parquet + partitioning + workgroup limit

```text
TARGET: analytics_db.events_raw
VERDICT: OPPORTUNITY_FOUND
REASON: Table is unpartitioned CSV (1.2 TB). Top 10 queries scan the full
  table averaging 320s runtime. Migrating to Parquet + partitioning by date
  reduces average scan from 1.2 TB to 18 GB (daily queries). Adding a 10 GB
  data-scanned limit prevents runaway scans.
RECOMMENDATION:
  Current: CSV, unpartitioned, no compression, no workgroup limit
  Proposed: Parquet + Snappy, partitioned by dt, 10 GB workgroup limit
  File format: CSV → Parquet
  Compression: none → Snappy
  Partitioning: none → partitioned_by = ['dt']
  Query rewrite: SELECT * → SELECT 8 of 42 columns; add WHERE dt filter
  Workgroup: no limit → 10 GB data scanned per query
  CTAS: materialize daily_summary aggregation table
  Confidence: HIGH — DDL confirms CSV/unpartitioned, query history shows
    daily date-filtered queries scanning 1.2 TB each.
ESTIMATED_SAVINGS:
  Cost (monthly): $3,280.50 → $49.10
    (1.2 TB × $5 × 220 queries/month → 18 GB × $5 × 220 queries/month)
  Performance: 320s avg → 8s avg (40x faster)
  Data scanned per query: 1.2 TB → 18 GB (98.5% reduction)
  Annual total: $38,774.40
  Assumptions: $5/TB, 220 daily-filtered queries/month, 1/30th data per
    partition after date partitioning + columnar pruning.
MIGRATION_STEPS:
  1. Create the Parquet partitioned table via CTAS:
     CREATE TABLE analytics_db.events_parquet
     WITH (format='PARQUET', parquet_compression='SNAPPY',
           partitioned_by=ARRAY['dt'],
           external_location='s3://<bucket>/events/parquet/')
     AS SELECT event_id, user_id, event_type, amount, device, country,
       ip_address, session_id,
       date_format(event_time, '%Y-%m-%d') AS dt
     FROM analytics_db.events_raw;
  2. Verify row count parity:
     SELECT COUNT(*) FROM analytics_db.events_parquet;
     SELECT COUNT(*) FROM analytics_db.events_raw;
  3. Update downstream queries to use the new table + partition filter:
     SELECT event_type, COUNT(*) FROM analytics_db.events_parquet
     WHERE dt >= '2026-07-01' GROUP BY event_type;
  4. Set the workgroup data-scanned limit:
     aws athena update-work-group --work-group primary \
       --configuration '{"BytesScannedCutoffPerQuery":10737418240,...}'
  5. Monitor query performance for 7 days before decommissioning the CSV table.
CONFIRM: Before running the CTAS (scans 1.2 TB, cost ~$6.00), emit and await:
  "CONFIRM: About to run CTAS migration on analytics_db.events_raw (1.2 TB,
   estimated cost $6.00). Proceed? (yes/no)"
```

## Verdict semantics

| Verdict | When to emit |
|---|---|
| OPPORTUNITY_FOUND | At least one dimension has a concrete, savings-bearing recommendation. |
| OPTIMIZED | Changes applied and verified this session; queries confirm improvement. |
| ALREADY_OPTIMAL | Parquet + partitioned + tight queries + workgroup limits in place. |

## Expert heuristic — consolidated

| Heuristic | Impact on recommendation |
|---|---|
| Athena charges per byte read, not per compute second | Reducing data scanned is the ONLY cost lever. |
| Parquet columnar pruning reads only selected columns | SELECT * on 50-column Parquet reads 50 columns; SELECT 3 reads 3. |
| Partition pruning happens at the S3 listing level | Queries without a partition-column WHERE clause scan every partition. |
| Partition projection eliminates Glue metadata latency | Essential for 100K+ partition tables; removes MSCK REPAIR need. |
| Snappy beats GZIP for query speed | GZIP decompression is CPU-bound; Snappy is 2-3x faster to decompress. |
| APPROX_COUNT_DISTINCT is 10-50x faster than COUNT(DISTINCT) | Error is < 3% with default settings; acceptable for dashboards. |
| CTAS breaks even proportional to query frequency | Materialize if the same aggregation runs 10+ times/day. |
| Workgroup data-scanned limits prevent the $5,000 SELECT * | Set limits conservatively; users get a clear error message. |
| Athena engine v3 enables dynamic partition pruning | The engine prunes partitions at runtime based on JOIN conditions. |
| Result reuse caches identical query output | Enable for dashboard workloads; 0 cost for cache hits. |
| Federated queries are NOT $5/TB | They use connector-specific pricing (Lambda + source system cost). |
| Small files (< 8 MB) cause S3 request overhead | Consolidate to 100 MB - 1 GB files per partition. |

## NEVER (top 5)

- **NEVER** recommend changing query patterns without first checking the file
  format. A `SELECT *` on Parquet is still better than `SELECT *` on CSV, but
  `SELECT col1, col2` on CSV is still expensive. Fix file format first.

- **NEVER** recommend partitioning without estimating partition size. Too
  many small partitions (< 100 MB each) cause S3 503 errors and metadata
  bloat. Consolidate to daily or monthly partitions if hourly files are small.

- **NEVER** recommend GZIP compression for Athena Parquet tables. GZIP's
  decompression overhead negates the compression advantage for query
  workloads. Use Snappy (default) or ZSTD.

- **NEVER** set a workgroup data-scanned limit without first measuring normal
  query sizes. Setting it too low blocks legitimate queries. Measure p99
  first, then set limit at p99 × 2.

- **NEVER** recommend CTAS materialization without checking query frequency.
  A CTAS that costs $5 to create but is queried once/month does not break
  even. Materialize only if query frequency justifies the one-time cost.

## Pre-flight safety checks (run before any remediation)

- **MANDATORY CONFIRMATION GATE** before any CTAS (it scans data and costs $).
- **Verify row count parity** after CTAS migration before decommissioning
  the source table.
- **Verify partition count** after adding partition projection — if the
  projection range is wrong, Athena may miss partitions.
- **Batch limit:** max 5 table migrations per batch, single CONFIRM per batch.
- **Capture pre-state:** record current DDL and query history before changes.

## Recent AWS features (2024-2026)

- **Athena query result reuse (2023-2024 GA):** Caches identical query
  results for a configurable TTL. Cache hits cost $0 and return in
  milliseconds. Enable via workgroup configuration:
  `Configuration.ResultConfiguration.ResultReuseConfiguration`.
- **Athena federated queries (2023-2025):** Query non-S3 data sources
  (DynamoDB, RDS, Redshift) via Lambda connectors. Not priced at $5/TB —
  cost is Lambda invocation + source system charges. Use for cross-source
  JOINs without ETL.
- **Athena Spark notebook integration (2024-2025):** Run interactive Spark
  sessions within Athena for complex transformations. Priced per DPU-hour
  ($0.35/DPU-hour). Use when SQL is insufficient for the transformation.
- **Athena engine version 3 (2022+, continuously updated 2024-2026):**
  Dynamic partition pruning (runtime partition elimination based on JOIN
  conditions), improved JOIN performance, subquery materialization. Ensure
  workgroup uses engine v3.
- **Apache Iceberg table support (2023-2025):** Athena can read and write
  Iceberg tables with time travel, schema evolution, and hidden partitioning.
  Iceberg on Athena enables ACID transactions and partition evolution
  without re-creating tables.
- **Athena parameterized queries (2024-2025):** Pre-compiled query templates
  that accept parameters. Improves security (SQL injection prevention) and
  enables result reuse for parameterized queries.

## Domain

AWS CloudOps / Amazon Athena Analytics Query Performance & Cost Optimization.

## AWS documentation

- **Amazon Athena User Guide** — https://docs.aws.amazon.com/athena/latest/ug/what-is.html
- **Athena performance tuning** — https://docs.aws.amazon.com/athena/latest/ug/performance-tuning.html
- **Athena pricing** — https://aws.amazon.com/athena/pricing/
- **Athena CTAS** — https://docs.aws.amazon.com/athena/latest/ug/ctas.html
- **Partition projection** — https://docs.aws.amazon.com/athena/latest/ug/partition-projection.html
- **Athena query result reuse** — https://docs.aws.amazon.com/athena/latest/ug/query-result-reuse.html
- **Athena federated queries** — https://docs.aws.amazon.com/athena/latest/ug/connect-to-a-data-source.html
- **Athena Spark** — https://docs.aws.amazon.com/athena/latest/ug/notebooks-spark.html
- **Apache Iceberg on Athena** — https://docs.aws.amazon.com/athena/latest/ug/querying-iceberg.html
- **AWS Well-Architected Framework — Performance Efficiency** — https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html
