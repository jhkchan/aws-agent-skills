# Athena Optimization CLI Reference

Load this reference when analyzing or planning Athena query optimization.
Contains CLI commands for data gathering, DDL inspection, query history
analysis, workgroup configuration, and post-remediation verification.

## Pre-flight data-gathering CLI commands

```bash
# 1. Get table DDL and storage descriptor:
aws glue get-table --database-name <db> --name <table> \
  --query 'Table.{Format:StorageDescriptor.InputFormat,
    Compressed:StorageDescriptor.Compressed,
    Location:StorageDescriptor.Location,
    Columns:StorageDescriptor.Columns[*].Name,
    Partitions:PartitionKeys[*].Name,
    Parameters:Parameters}' --output json

# 2. Check partition count and distribution:
aws glue get-partitions --database-name <db> --table-name <table> \
  --query 'Partitions[*].Values' --output json | jq 'length'

# 3. Get partition projection properties:
aws glue get-table --database-name <db> --name <table> \
  --query 'Table.Parameters."projection.enabled"'

# 4. Check S3 data layout and file sizes:
aws s3 ls s3://<bucket>/<prefix>/ --recursive --human-readable --summarize

# 5. List recent Athena queries (with data scanned):
aws athena list-query-executions --work-group <wg> --max-results 50 \
  --query 'QueryExecutionIds'

# 6. Batch get execution details:
aws athena batch-get-query-execution \
  --query-execution-ids <id1> <id2> <id3> <id4> <id5> \
  --query 'QueryExecutions[*].{
    Query:Query,
    ScannedMB:Statistics.DataScannedInBytes,
    RuntimeSec:Statistics.EngineExecutionTimeInMillis,
    State:Status.State,
    Workgroup:WorkGroup}' --output table

# 7. Get workgroup configuration:
aws athena get-work-group --work-group <wg> \
  --query 'WorkGroup.Configuration.{EngineVersion:EngineVersion.SelectedEngineVersion,
    BytesScannedCutoff:BytesScannedCutoffPerQuery,
    EnforceConfig:EnforceWorkGroupConfiguration,
    ResultReuse:ResultConfiguration.ResultReuseConfiguration,
    OutputLocation:ResultConfiguration.OutputLocation}'

# 8. Athena cost from Cost Explorer:
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --metrics "UsageQuantity" "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Athena"]}}' \
  --query 'ResultsByTime[*].{Period:TimePeriod.Start,
    Cost:Total.UnblendedCost.Amount,
    Usage:Total.UsageQuantity.Amount}'

# 9. Get query execution plan (EXPLAIN):
aws athena start-query-execution \
  --query-string "EXPLAIN SELECT * FROM <db>.<table> WHERE dt >= '2026-07-01'" \
  --work-group <wg> \
  --result-configuration OutputLocation=s3://<bucket>/results/ \
  --query 'QueryExecutionId'

# 10. Verify table properties for compression:
aws glue get-table --database-name <db> --name <table> \
  --query 'Table.Parameters."parquet.compression"'
```

## CTAS template library

### CSV to Parquet + Snappy

```sql
CREATE TABLE <db>.<table>_parquet
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  external_location = 's3://<bucket>/<prefix>/parquet/'
) AS
SELECT * FROM <db>.<table>_csv;
```

### Add partitioning

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

### Add bucketing for JOIN optimization

```sql
CREATE TABLE <db>.<table>_bucketed
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  bucketed_by = ARRAY['join_key'],
  bucket_count = 256,
  external_location = 's3://<bucket>/<prefix>/bucketed/'
) AS
SELECT * FROM <db>.<table>;
```

### Materialize aggregation

```sql
CREATE TABLE <db>.<daily_agg>
WITH (
  format = 'PARQUET',
  parquet_compression = 'SNAPPY',
  partitioned_by = ARRAY['dt'],
  external_location = 's3://<bucket>/curated/<agg>/'
) AS
SELECT
  date_trunc('day', event_time) AS day,
  dim1, dim2,
  COUNT(*) AS cnt,
  SUM(metric) AS total
FROM <db>.raw_events
WHERE dt >= '2026-07-01'
GROUP BY 1, 2, 3;
```

## Partition projection configuration

### Daily date partitions

```sql
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

### Hourly date partitions

```sql
ALTER TABLE <db>.<table> SET TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.dt.type' = 'date',
  'projection.dt.range' = '2024-01-01,2026-12-31',
  'projection.dt.format' = 'yyyy-MM-dd HH',
  'projection.dt.interval' = '1',
  'projection.dt.interval.unit' = 'HOURS',
  'storage.location.template' = 's3://<bucket>/<prefix>/${dt}'
);
```

### Integer partitions (e.g., customer_id ranges)

```sql
ALTER TABLE <db>.<table> SET TBLPROPERTIES (
  'projection.enabled' = 'true',
  'projection.cust_id.type' = 'integer',
  'projection.cust_id.range' = '0,999999',
  'projection.cust_id.interval' = '1',
  'storage.location.template' = 's3://<bucket>/<prefix>/cust_id=${cust_id}'
);
```

## Workgroup configuration commands

```bash
# Get current workgroup config:
aws athena get-work-group --work-group <wg>

# Set data-scanned limit (10 GB):
aws athena update-work-group \
  --work-group <wg> \
  --configuration '{
    "ResultConfiguration": {
      "OutputLocation": "s3://<bucket>/results/"
    },
    "EnforceWorkGroupConfiguration": true,
    "PublishCloudWatchMetricsEnabled": true,
    "BytesScannedCutoffPerQuery": 10737418240,
    "EngineVersion": {
      "SelectedEngineVersion": "Athena engine version 3"
    }
  }'

# Enable query result reuse (1 hour TTL):
aws athena update-work-group \
  --work-group <wg> \
  --configuration '{
    "ResultConfiguration": {
      "OutputLocation": "s3://<bucket>/results/",
      "ResultReuseConfiguration": {
        "ResultReuseByAgeConfiguration": {
          "Enabled": true,
          "MaxAgeInMinutes": 60
        }
      }
    },
    "EnforceWorkGroupConfiguration": true,
    "BytesScannedCutoffPerQuery": 10737418240
  }'
```

## Cost estimation formulas

### Per-query cost
```
cost = (data_scanned_bytes / 1e12) * $5
```

### Monthly cost for a repeated query
```
monthly_cost = per_query_cost * queries_per_day * 30
```

### CTAS break-even
```
ctas_cost = (source_table_bytes / 1e12) * $5
break_even_queries = ctas_cost / (materialized_per_query_cost)
days_to_break_even = break_even_queries / queries_per_day
```

### File format migration savings
```
savings = (csv_bytes - parquet_bytes) / 1e12 * $5 * queries_per_month
# Rule of thumb: CSV to Parquet reduces data scanned by 50-90%
```

### Partition pruning savings
```
savings = (full_scan_bytes - partition_scan_bytes) / 1e12 * $5 * queries_per_month
# Rule of thumb: daily partition on a year of data = 1/365th scan
```

## Post-remediation verification

```bash
# 1. Verify CTAS row count parity:
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM <db>.<table>_parquet" \
  --work-group <wg> \
  --result-configuration OutputLocation=s3://<bucket>/verify/ \
  --query 'QueryExecutionId'

# 2. Compare query performance before/after:
# Before:
aws athena batch-get-query-execution --query-execution-ids <old-id> \
  --query 'QueryExecutions[0].{ScannedMB:Statistics.DataScannedInBytes,
    RuntimeMs:Statistics.EngineExecutionTimeInMillis}'

# After:
aws athena batch-get-query-execution --query-execution-ids <new-id> \
  --query 'QueryExecutions[0].{ScannedMB:Statistics.DataScannedInBytes,
    RuntimeMs:Statistics.EngineExecutionTimeInMillis}'

# 3. Verify partition projection works (no MSCK REPAIR needed):
aws athena start-query-execution \
  --query-string "SHOW PARTITIONS <db>.<table>" \
  --work-group <wg> \
  --result-configuration OutputLocation=s3://<bucket>/verify/ \
  --query 'QueryExecutionId'

# 4. Verify workgroup data-scanned limit is enforced:
aws athena get-work-group --work-group <wg> \
  --query 'WorkGroup.Configuration.BytesScannedCutoffPerQuery'

# 5. Monitor Athena spend trend:
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity DAILY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Athena"]}}'
```

## Additional worked examples

### Worked example — already optimal

```text
TARGET: analytics_db.daily_summary
VERDICT: ALREADY_OPTIMAL
REASON: Table is Parquet + Snappy, partitioned by dt with partition projection
  (hourly, 2024-2026 range). Workgroup has 10 GB data-scanned limit. Top
  queries select 3-4 columns with WHERE dt filter. Result reuse enabled (1h TTL).
  APPROX_COUNT_DISTINCT used for cardinality metrics.
RECOMMENDATION:
  Current: Parquet + Snappy, partitioned, partition projection, workgroup limit
  Proposed: no change
  Confidence: HIGH — all optimization dimensions addressed.
ESTIMATED_SAVINGS:
  Monthly: $0
  Annual total: $0
MIGRATION_STEPS:
  - None. Re-evaluate quarterly if query patterns change.
```

### Worked example — NEED_MORE_INFO (table not in Glue)

```text
TARGET: analytics_db.missing_table
VERDICT: NEED_MORE_INFO
REASON: Table not found in Glue catalog. Cannot assess file format or
  partitioning without DDL.
RECOMMENDATION:
  1. Verify table exists:
     aws glue get-table --database-name analytics_db --name missing_table
  2. If not found, run a Glue crawler to discover the schema.
  3. If in a different database, specify the correct database name.
ESTIMATED_SAVINGS: $0 (cannot quantify without DDL)
```

## Full NEVER list (anti-patterns)

- NEVER recommend changing query patterns without first checking the file
  format. File format is the highest-leverage single change.
- NEVER recommend partitioning without estimating partition size. Too many
  small partitions (< 100 MB) cause S3 request overhead and metadata bloat.
- NEVER recommend GZIP compression for Athena Parquet tables. GZIP
  decompression is CPU-bound; use Snappy or ZSTD.
- NEVER set a workgroup data-scanned limit without first measuring normal
  query sizes. Setting it too low blocks legitimate queries.
- NEVER recommend CTAS without checking query frequency. A CTAS that costs
  $5 to create but is queried once/month does not break even.
- NEVER use `SELECT *` in production Athena queries. Always specify the
  columns you need for columnar pruning.
- NEVER use `ORDER BY` without `LIMIT` on large result sets. Sort the
  minimum data necessary.
- NEVER use `COUNT(DISTINCT)` when `APPROX_COUNT_DISTINCT` suffices. The
  error is < 3% and the speedup is 10-50x.
- NEVER run `MSCK REPAIR TABLE` on tables with partition projection enabled.
  Projection auto-discovers partitions.
- NEVER mix GZIP and Snappy files in the same Parquet table. Athena may
  fail or degrade performance.
- NEVER assume federated queries cost $5/TB. They use connector-specific
  pricing (Lambda + source system charges).
- NEVER ignore small file sizes in S3. Files < 8 MB cause S3 request
  overhead and slow query planning.
