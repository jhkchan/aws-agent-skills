# Eval prompt: partition-projection-large-partition-count

Optimize this Athena table for query performance. Walk the optimization
framework and emit the standard optimization block.

## Scenario

Database: `logs_db`
Table: `app_logs_partition-projection-large-partition-count`
Region: us-east-1

## Known facts

- **Table DDL** (`aws glue get-table`):
  - `InputFormat`: `org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat` (Parquet)
  - `Compressed`: `true` (Snappy)
  - `Location`: `s3://logs/app/`
  - `PartitionKeys`: `[dt]` (date, hourly partitions)
  - `projection.enabled`: not set (not enabled)

- **Partition count**: 500,000+ (3 years of hourly data)

- **Query history**:
  - Top queries filter by `dt` range (e.g., `WHERE dt >= '2026-08-01 00:00:00'`)
  - Query planning latency: 5-10 seconds (Glue `get-partitions` overhead)
  - `MSCK REPAIR TABLE` runtime: 30 minutes
  - Data scanned per query: reasonable (partition pruning works once
    metadata loads)

- **Workgroup**: Athena engine version 3, 10 GB data-scanned limit set.

## Symptom

Table is well-formatted (Parquet + Snappy) but query planning is slow due
to 500K partitions in Glue. `MSCK REPAIR TABLE` takes 30 minutes. Every
query has a 5-10 second metadata latency penalty before execution begins.
