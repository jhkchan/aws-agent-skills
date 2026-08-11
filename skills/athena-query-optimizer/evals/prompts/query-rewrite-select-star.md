# Eval prompt: query-rewrite-select-star

Optimize these Athena queries for performance and cost. Walk the
optimization framework and emit the standard optimization block.

## Scenario

Database: `sales_db`
Table: `orders_query-rewrite-select-star`
Region: us-east-1

## Known facts

- **Table DDL**:
  - `InputFormat`: Parquet
  - `Compressed`: `true` (Snappy)
  - `Location`: `s3://data-lake/orders/`
  - `Columns`: 47 columns
  - `PartitionKeys`: `[dt]` (date, daily partitions)
  - `projection.enabled`: `true` (partition projection already set)

- **Query history** (top 5 queries):
  1. `SELECT * FROM orders_query-rewrite-select-star
      WHERE amount > 100 ORDER BY created_at DESC`
     — scans 850 GB, runtime 95s
  2. `SELECT * FROM orders_query-rewrite-select-star
      WHERE status = 'shipped'`
     — scans 850 GB, runtime 88s
  3. `SELECT customer_id, COUNT(DISTINCT product_id)
      FROM orders_query-rewrite-select-star GROUP BY customer_id`
     — scans 850 GB, runtime 120s

- **Problems identified**:
  - All queries use `SELECT *` (read all 47 columns)
  - No `WHERE` filter on `dt` (partition column) — full table scan every time
  - `COUNT(DISTINCT)` instead of `APPROX_COUNT_DISTINCT`
  - `ORDER BY` without `LIMIT`

- **Workgroup**: 50 GB data-scanned limit (queries exceed it, get blocked).

## Symptom

Table format and partitioning are good (Parquet + Snappy + partitioned +
projection), but queries are poorly written: SELECT *, no partition filters,
expensive DISTINCT sorts. Queries exceed the workgroup limit and get blocked.
