# Eval prompt: already-optimal-parquet-partitioned-projection

Optimize this Athena table for query performance and cost. Walk the
optimization framework and emit the standard optimization block.

## Scenario

Database: `analytics_db`
Table: `daily_summary_already-optimal-parquet-partitioned-projection`
Region: us-east-1

## Known facts

- **Table DDL**:
  - `InputFormat`: Parquet, `Compressed`: Snappy
  - `Partitioned by`: `dt` (daily)
  - `projection.enabled`: `true` (daily range 2024-01-01 to 2026-12-31)
  - `Size`: ~50 GB total, ~170 MB/day

- **Query history** (top queries):
  1. `SELECT product_id, APPROX_COUNT_DISTINCT(user_id) AS unique_users,
            SUM(amount) AS total
     FROM daily_summary_already-optimal-parquet-partitioned-projection
     WHERE dt >= '2026-07-01' AND dt <= '2026-08-01'
     GROUP BY product_id`
     — scans 800 MB, runtime 2s
  2. `SELECT event_type, COUNT(*) FROM ... WHERE dt = '2026-08-05'`
     — scans 170 MB, runtime 1s

- **Workgroup**:
  - `BytesScannedCutoffPerQuery`: 10737418240 (10 GB)
  - `EnforceWorkGroupConfiguration`: true
  - `EngineVersion`: Athena engine version 3
  - Result reuse enabled (1 hour TTL)

- **Query patterns**: No `SELECT *` usage. All queries use `dt` partition
  filter. `APPROX_COUNT_DISTINCT` used for cardinality. Result reuse caches
  repeated dashboard queries.

## Symptom

Table appears to be in an already-optimized state across all dimensions:
file format, partitioning, partition projection, query patterns, and
workgroup configuration.
