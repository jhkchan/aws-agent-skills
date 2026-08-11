# Eval prompt: ctas-materialization-repeated-scan

Optimize this Athena workload for cost. Walk the optimization framework
and emit the standard optimization block.

## Scenario

Database: `analytics_db`
Table: `events_parquet_ctas-materialization-repeated-scan`
Region: us-east-1

## Known facts

- **Table DDL**:
  - `InputFormat`: Parquet, `Compressed`: Snappy
  - `Partitioned by`: `dt` (daily)
  - `Size`: ~6 TB (1 year of daily data, ~16 GB/day)
  - `projection.enabled`: `true`

- **Query pattern**: a dashboard runs this query 50 times/day:
  ```sql
  SELECT date_trunc('day', event_time) AS day,
         product_id, event_type,
         COUNT(*) AS event_count,
         SUM(amount) AS total_amount,
         COUNT(DISTINCT user_id) AS unique_users
  FROM events_parquet_ctas-materialization-repeated-scan
  WHERE dt >= date_format(current_date - interval '1' day, '%Y-%m-%d')
  GROUP BY 1, 2, 3
  ```

- **Per query**: scans 200 GB, costs $1.00, runtime 45s.
- **Daily total**: 50 queries * $1.00 = $50/day = $1,500/month.

- Table is already Parquet + partitioned + partition projection.
  The query is correctly filtering by `dt`. The issue is repeated
  computation of the same aggregation.

- **Workgroup**: Athena engine v3, 10 GB limit, result reuse enabled.

## Symptom

Table is well-optimized (Parquet, partitioned, projection), but the same
aggregation is computed 50 times/day, scanning 200 GB each time. Monthly
cost: $1,500 for this single query pattern.
