# Athena Query Optimization Reference — Decision Tree

Supplementary reference for the Athena Query Optimizer skill. Walks the
full optimization analysis with worked examples per recommendation category.

## Athena cost anatomy and where each optimization strikes

```
   USER RUNS QUERY
        |
        v
   [S3 LIST] ---- list partitions ----> Partition Projection
        |                                  (eliminates Glue metadata latency)
        v
   [S3 GET] ---- read column data -------> File Format (Parquet columnar pruning)
        |                                  (read only selected columns)
        |                                  + Compression (Snappy/ZSTD)
        v
   [Partition Pruning] ---- skip S3 dirs -> Partitioning (date/time columns)
        |                                  (read only matching partitions)
        v
   [Dynamic Pruning] ---- runtime skip ---> Athena Engine v3
        |                                  (prune partitions from JOIN conditions)
        v
   [Processing] ---- compute results -----> Query Rewriting
        |                                  (APPROXIMATE, LIMIT, CTE)
        v
   [Result] ---- cache for reuse ---------> Result Reuse
                                           (0 cost for cache hits)
```

Optimization categories map to the steps in SKILL.md:

- File format = Step 2
- Partitioning = Step 3
- Partition projection = Step 4
- Compression = Step 5
- Query rewriting = Step 6
- CTAS materialization = Step 7
- Workgroup settings = Step 8
- Bucketing = Step 9

**Rule:** File format first (biggest single win), then partitioning, then
query rewriting, then workgroup limits. Each layer amplifies the previous.

## Worked example — CSV to Parquet migration (Step 2)

**Scenario:** `analytics_db.events` is CSV, 1.2 TB. Top queries select 5-8
of 42 columns. Average query scans 1.2 TB, takes 320s.

**Analysis:**

1. File format: CSV (row-based). Every query reads all 42 columns even if
   it selects 5. No compression.
2. Partitioning: none. No `WHERE dt` filter possible — full table scan
   every time.
3. Query history shows all 10 top queries filter by `event_time` date range.

**Recommendation:** CTAS to Parquet + Snappy, partitioned by date.

**Estimated impact:**
- Parquet columnar pruning: 5/42 columns read = 88% reduction.
- Snappy compression: additional ~60% reduction.
- Date partitioning: 1/30th of data for daily queries.
- Combined: 1.2 TB → ~8 GB per daily query (99.3% reduction).

```sql
CREATE TABLE analytics_db.events_parquet
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  partitioned_by = ARRAY['dt'],
  external_location = 's3://<bucket>/events/parquet/'
) AS
SELECT event_id, user_id, event_type, amount, device, country,
       ip_address, session_id, event_time,
       date_format(event_time, '%Y-%m-%d') AS dt
FROM analytics_db.events;
```

## Worked example — Partition projection for 500K partitions (Step 4)

**Scenario:** `logs_db.app_logs` has 500K partitions across 3 years of
hourly data. `MSCK REPAIR TABLE` takes 30 minutes. Query planning (Glue
`get-partitions`) adds 5-10 seconds to every query.

**Analysis:**

1. 500K partitions is well beyond Glue's efficient metadata limit (~50K).
2. Partitions follow a predictable hourly date pattern.
3. The table is already Parquet + partitioned by `dt` (hourly).

**Recommendation:** Enable partition projection with an hourly date range.

```sql
ALTER TABLE logs_db.app_logs SET TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.dt.type' = 'date',
  'projection.dt.range' = '2023-01-01,2026-12-31',
  'projection.dt.format' = 'yyyy-MM-dd HH',
  'projection.dt.interval' = '1',
  'projection.dt.interval.unit' = 'HOURS',
  'storage.location.template' = 's3://<bucket>/logs/${dt}'
);
```

**Impact:** Query planning drops from 5-10s to < 1s. `MSCK REPAIR TABLE`
no longer needed. No cost change (same data scanned), but significantly
better user experience.

**Caution:** If hourly partitions are small (< 100 MB each), consider
consolidating to daily partitions. 500K small files cause S3 request
overhead. The projection eliminates metadata latency but does not fix
the small-file problem.

## Worked example — Query rewriting (Step 6)

### Before — expensive full scan with SELECT *

```sql
SELECT * FROM sales
WHERE amount > 100
ORDER BY created_at DESC;
```

**Problems:**
- `SELECT *` reads all 47 columns (needs only 3).
- No partition filter on `dt` — scans all partitions.
- `ORDER BY` without `LIMIT` sorts the entire result set.

### After — optimized

```sql
SELECT order_id, customer_id, amount
FROM sales
WHERE dt >= '2026-07-01'
  AND dt <= '2026-08-01'
  AND amount > 100
ORDER BY created_at DESC
LIMIT 1000;
```

**Impact:** Columnar pruning (3/47 columns), partition pruning (1 month of
data), and bounded sort (1000 rows). Estimated 95% data scan reduction.

### APPROXIMATE functions

```sql
-- Before (exact, expensive):
SELECT product_id, COUNT(DISTINCT user_id) AS unique_users
FROM events
WHERE dt >= '2026-07-01'
GROUP BY product_id;

-- After (approximate, 10-50x faster, < 3% error):
SELECT product_id, APPROX_COUNT_DISTINCT(user_id) AS unique_users
FROM events
WHERE dt >= '2026-07-01'
GROUP BY product_id;
```

## Worked example — CTAS for daily aggregation (Step 7)

**Scenario:** A dashboard runs the same daily aggregation query 50 times/day,
scanning 200 GB of raw events each time. Total: 10 TB/day = $50/day =
$1,500/month.

**Recommendation:** Materialize the aggregation via CTAS.

```sql
CREATE TABLE analytics_db.daily_metrics
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  partitioned_by = ARRAY['dt']
) AS
SELECT
  date_trunc('day', event_time) AS day,
  product_id,
  event_type,
  COUNT(*) AS event_count,
  SUM(amount) AS total_amount,
  APPROX_COUNT_DISTINCT(user_id) AS unique_users
FROM analytics_db.events_parquet
WHERE dt >= '2026-07-01'
GROUP BY 1, 2, 3;
```

**Cost trade-off:**
- CTAS creation: scans 200 GB once = $1.00.
- Daily refresh: $1.00/day (incremental partition).
- Dashboard queries on `daily_metrics`: scan ~500 MB each = $0.0025 each.
- Monthly: 50 queries/day × 30 days × $0.0025 = $3.75 vs original $1,500.
- Savings: $1,496.25/month ($17,955/year).

## Worked example — Bucketing for large JOIN (Step 9)

**Scenario:** Two 50 GB tables `orders` and `customers` JOINed on
`customer_id`. The shuffle phase dominates runtime (180s).

**Recommendation:** Bucket both tables on `customer_id` with 256 buckets.

```sql
CREATE TABLE analytics_db.orders_bucketed
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  bucketed_by = ARRAY['customer_id'],
  bucket_count = 256
) AS SELECT * FROM analytics_db.orders;

CREATE TABLE analytics_db.customers_bucketed
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  bucketed_by = ARRAY['customer_id'],
  bucket_count = 256
) AS SELECT * FROM analytics_db.customers;
```

**Impact:** Bucket-map JOIN eliminates the shuffle. Runtime: 180s → ~30s.
Data scanned unchanged (same 100 GB total), but 6x faster.

## Worked example — ALREADY_OPTIMAL

**Scenario:** `analytics_db.daily_summary` is Parquet + Snappy, partitioned
by `dt` with partition projection enabled. Workgroup has a 10 GB data-scanned
limit. Queries select 3 columns with a `WHERE dt` filter. APPROX_COUNT_DISTINCT
used for cardinality. Result reuse enabled.

```text
TARGET: analytics_db.daily_summary
VERDICT: ALREADY_OPTIMAL
REASON: Table is Parquet + Snappy, partitioned by dt with partition projection,
  workgroup has 10 GB limit, queries use columnar pruning + partition filters +
  APPROXIMATE functions. Result reuse enabled. No optimization opportunity
  remaining.
```

## Worked example — NEED_MORE_INFO

**Scenario:** Table not found in Glue catalog. Cannot retrieve DDL or
partition metadata.

```text
TARGET: analytics_db.missing_table
VERDICT: NEED_MORE_INFO
REASON: Table not found in Glue catalog. Cannot assess file format or
  partitioning without DDL.
RECOMMENDATION:
  1. Verify the table exists:
     aws glue get-table --database-name analytics_db --name missing_table
  2. If the table is in a different database, specify the correct database.
  3. If the table is not registered, run a Glue crawler to discover the schema.
```

## Cross-category decision flowchart

```
START
  |
  v
Table in CSV or JSON format?
  |-- YES --> Step 2: CTAS to Parquet + Snappy
  |            (highest-leverage single change)
  v NO (Parquet or ORC)
Table unpartitioned with date/time queries?
  |-- YES --> Step 3: Add partitioning via CTAS
  v NO
Partitioned table with > 100K partitions?
  |-- YES --> Step 4: Enable partition projection
  v NO
Queries use SELECT *?
  |-- YES --> Step 6: Rewrite to select specific columns
  v NO
Queries missing partition column filter?
  |-- YES --> Step 6: Add WHERE on partition column
  v NO
Repeated full-table aggregation scan?
  |-- YES --> Step 7: CTAS materialization
  v NO
Workgroup has no data-scanned limit?
  |-- YES --> Step 8: Set limit at p99 * 2
  v NO
Large-table JOIN with shuffle overhead?
  |-- YES --> Step 9: Bucket both tables on join key
  v NO
All dimensions pass + Parquet + partitioned + tight queries
  |
  v
ALREADY_OPTIMAL
```
