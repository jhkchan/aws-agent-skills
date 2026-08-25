# Redshift EXPLAIN and Scan Type Reference Guide

Supplementary reference for the Redshift Query Troubleshooter skill.
Loaded on-demand when a diagnostic needs EXPLAIN plan interpretation,
distribution/sort key decision guidance, or system table query patterns.

## EXPLAIN scan type reference

| EXPLAIN signal | Meaning | Performance impact |
|---|---|---|
| `Seq Scan` | Full table scan, no sort key elimination | Slow on large tables |
| `Sort` / sort-aware scan | Sort key leveraged; zone maps skip blocks | Fast -- blocks eliminated by zone maps |
| `DS_DIST_NONE` | Join is co-located; no redistribution needed | Optimal -- no network movement |
| `DS_DIST_ALL_INNER` | Inner table broadcast to all compute nodes | Costly on large inner tables |
| `DS_BCAST_INNER` | Inner table broadcast (alias for DS_DIST_ALL_INNER) | Costly on large inner tables |
| `DS_DIST_ALL_NONE` | Outer table broadcast; inner table stays local | OK for small outer tables |
| `DS_DIST_BOTH` | Both tables redistributed | Costly; both tables move data |
| `XN Hash Join` | Hash-based join (normal for equi-joins) | Good |
| `XN Merge Join` | Merge-based join (requires sorted inputs) | Good if inputs are sorted on join key |
| `XN Nested Loop` | Cartesian product -- every row vs every row | Almost always a bug |
| `XN Aggregate` | Aggregation step (GROUP BY) | Normal |
| `XN Limit` | LIMIT clause applied | Normal |
| `XN Window` | Window function | Normal, can be expensive |
| `XN Subquery Scan` | Subquery / CTE materialization | Check for unnecessary materialization |

### Reading the EXPLAIN prefix

Each step in the EXPLAIN tree has a prefix:
- `XN` = executed on compute nodes (parallel)
- `RS` = executed on leader node (serial)
- No prefix = storage-layer operation

Leader-node operations (`RS`) are single-threaded and should be avoided
for large data volumes.

## Distribution style decision guide

| Table profile | Recommended DISTSTYLE | Why |
|---|---|---|
| Large fact table (> 5M rows), dominant join on column X | KEY (X) | Co-locates matching rows for DS_DIST_NONE joins |
| Small dimension table (< 2-5M rows) | ALL | Replicates to all nodes; all joins are local (DS_DIST_NONE) |
| Staging table (loaded, queried independently) | EVEN | Even distribution for parallel scan; no join co-location needed |
| Table with no joins (used standalone) | EVEN | Balanced parallel scan; no join optimization needed |
| Table used in multiple joins on different columns | KEY on the most selective join column | Optimize the dominant join; accept redistribution on others |

### Distribution style SQL reference

```sql
-- Check current distribution style
SELECT schemaname, tablename, diststyle
FROM svv_table_info
WHERE schemaname NOT IN ('pg_catalog', 'pg_internal');

-- Check per-column distkey
SELECT tablename, "column", type, distkey, sortkey
FROM pg_table_def
WHERE schemaname = '<schema>' AND tablename = '<table>';

-- Change distribution style
ALTER TABLE <table> ALTER DISTSTYLE KEY DISTKEY (<column>);
ALTER TABLE <table> ALTER DISTSTYLE ALL;
ALTER TABLE <table> ALTER DISTSTYLE EVEN;
ALTER TABLE <table> ALTER DISTSTYLE AUTO;  -- let Redshift choose

-- After changing, update statistics
ANALYZE <table>;
```

## Sort key decision guide

| Query pattern | Recommended sort key | Why |
|---|---|---|
| Range filter on single date column | Compound (date_column) | Zone maps skip blocks outside date range |
| Range filter on date + equality on dimension | Compound (date_column, dim_column) | Date primary filter; dimension secondary |
| Equality filters on 2-3 independent columns | Interleaved (col1, col2, col3) | Equal-weight zone maps for any filter combination |
| Range filter on a non-date numeric column | Compound (numeric_column) | Zone maps work on any ordered type |
| No range filters, full scans only | (no sort key) | No zone map benefit; save sort maintenance |
| Mixed workload with varying filter patterns | Interleaved (max 3-4 cols) | Balanced for multiple access patterns |

### Compound vs interleaved sort keys

| Property | Compound | Interleaved |
|---|---|---|
| Zone map weight | First column dominates | All columns equal |
| Best for | Queries filtering on column 1 (or 1+2) | Queries filtering on any individual column |
| VACUUM cost | Lower | Higher |
| Write performance | Better | Worse (more re-sorting) |
| Max recommended columns | 4 | 3-4 |
| Zone map effectiveness for col 1 | Full | Reduced vs compound |

### Sort key SQL reference

```sql
-- Check current sort keys
SELECT tablename, "column", sortkey, sortkey_order
FROM pg_table_def
WHERE schemaname = '<schema>' AND tablename = '<table>'
  AND sortkey > 0
ORDER BY sortkey;

-- Change sort key
ALTER TABLE <table> ALTER SORTKEY (col1);
ALTER TABLE <table> ALTER SORTKEY (col1, col2);
ALTER TABLE <table> ALTER SORTKEY INTERLEAVED (col1, col2, col3);
ALTER TABLE <table> ALTER SORTKEY AUTO;  -- let Redshift choose

-- After changing, vacuum to sort the data
VACUUM SORT ONLY <table>;
ANALYZE <table>;
```

## Data skew detection

```sql
-- Check skew per slice (values should be roughly equal)
SELECT slice, COUNT(*) AS row_count
FROM <table_name>
GROUP BY slice
ORDER BY slice;

-- Check max_skew from SVV_TABLE_INFO
SELECT schemaname, tablename, diststyle, size,
       pct_used, max_skew, unsorted
FROM svv_table_info
WHERE max_skew > 1.5
ORDER BY max_skew DESC;
```

A `max_skew` > 1.5 indicates uneven distribution. A `max_skew` > 3.0
is severe and causes query performance to degrade because some slices
do more work than others.

## STL_WLM_QUERY timing interpretation

| Metric | Interpretation |
|---|---|
| `queue_time` >> `exec_time` | Queue contention; query waited for a slot |
| `exec_time` >> `queue_time` | Query slow during execution; optimize query plan |
| `total_queue_time` > `queue_time` | Query hopped queues (WLM Query Queue Hopping) |
| `state = 'cancelled'` | Query was cancelled (by WLM timeout, user, or error) |
| `state = 'completed'` | Query finished successfully |

## SVV_QUERY_SUMMARY step analysis

```sql
SELECT query, segment, step, maxtime, avgtime, rows, bytes
FROM svv_query_summary
WHERE query = <query_id>
ORDER BY segment, step;
```

Key fields:
- `maxtime`: Maximum time across slices for this step (microseconds).
  A step with `maxtime` >> others is the bottleneck.
- `rows` / `bytes`: Data volume at each step. A step with unexpectedly
  high rows (e.g., before a filter) may indicate a late filter.
- `is_diskbased`: If `true`, the step spilled to disk. Spilling is
  expensive; reduce by allocating more memory or filtering earlier.

## System table quick reference

| Table | Purpose | Retention |
|---|---|---|
| `STL_QUERY` | Query history (text, start/end, status) | 2-5 days |
| `STL_WLM_QUERY` | WLM queue assignment and timing | 2-5 days |
| `STL_LOAD_ERRORS` | COPY error details | 2-5 days |
| `STL_ERROR` | General error log | 2-5 days |
| `STV_LOCKS` | Active table locks (current state only) | Real-time |
| `STV_INFLIGHT` | Currently executing queries | Real-time |
| `SVV_TABLE_INFO` | Table metadata (diststyle, sortkey, skew) | Real-time |
| `SVV_QUERY_SUMMARY` | Per-step execution summary | 2-5 days |
| `PG_TABLE_DEF` | Column-level metadata | Real-time |
| `SVV_VACUUM_PROGRESS` | Active vacuum progress | Real-time |
| `STV_WLM_SERVICE_CLASS_CONFIG` | WLM queue configuration | Real-time |
| `STV_SESSIONS` | Active database connections | Real-time |
| `STL_CONNECTION_LOG` | Connection auth and teardown events | 2-5 days |

System tables with `STL_` prefix are log tables (historical). Tables
with `STV_` prefix are view tables (current state). `SVV_` tables are
system views.

## Symptom→layer matrix and distribution/sort decision guides (from SKILL.md)

### Symptom -> layer decision matrix (offline classification)

```
Error string / EXPLAIN signal                     -> Layer
"cancelled due to queue timeout"                  -> WLM_QUEUE_TIMEOUT
Query hangs; STV_LOCKS shows granted=false         -> TABLE_LOCK
stl_load_errors                                    -> COPY_IAM_ROLE / COPY_DATA_FORMAT
DS_DIST_ALL_INNER / DS_BCAST_INNER in EXPLAIN      -> DIST_KEY_SKEW
Seq Scan on large table in EXPLAIN                 -> SORT_KEY_MISALIGNMENT
Nested Loop in EXPLAIN                             -> NESTED_LOOP_JOIN
"too many connections"                             -> CONNECTION_LIMIT
"SSL certificate verification failed"              -> SSL_TLS_ERROR
"character ... has no equivalent in encoding"      -> ENCODING_CONVERSION
VACUUM running for hours                           -> VACUUM_BLOCKED
```

### Distribution style decision guide

| Table profile | Recommended DISTSTYLE | Why |
|---|---|---|
| Large fact table (> 5M rows), joins on a specific column | KEY on the join column | Co-locates matching rows for DS_DIST_NONE joins |
| Small dimension table (< 2-5M rows) | ALL | Replicates to all nodes; all joins are local |
| Staging table (loaded and queried independently) | EVEN | Even distribution for parallel scan; no join co-location needed |
| Table with no joins (used standalone) | EVEN | Balanced parallel scan |

### Sort key decision guide

| Query pattern | Recommended sort key | Why |
|---|---|---|
| Range filter on a single date column | Compound (date_column) | Zone maps skip blocks outside the date range |
| Range filter on date + equality on dimension | Compound (date_column, dim_column) | Date is primary filter; dim is secondary |
| Equality filters on 2-3 independent columns | Interleaved (col1, col2, col3) | Equal-weight zone maps for any filter combination |
| No range filters, full scans only | (no sort key) | No zone map benefit; save sort maintenance cost |

## EXPLAIN scan type reference (from SKILL.md)

### EXPLAIN scan type reference

| EXPLAIN signal | Meaning | Performance impact |
|---|---|---|
| `Seq Scan` | Full table scan, no sort key elimination | Slow on large tables |
| `Sort` | Sort key leveraged; zone maps skip blocks | Fast -- blocks eliminated |
| `DS_DIST_NONE` | Join is co-located; no redistribution | Optimal |
| `DS_DIST_ALL_INNER` | Inner table broadcast to all nodes | Costly on large tables |
| `DS_BCAST_INNER` | Inner table broadcast (same as ALL_INNER) | Costly |
| `DS_DIST_ALL_NONE` | Outer table broadcast; inner stays | OK for small outer tables |
| `XN Hash Join` | Hash-based join (normal) | Good |
| `XN Merge Join` | Merge-based join (requires sorted inputs) | Good if inputs are sorted |
| `XN Nested Loop` | Cartesian product | Almost always a bug |
