# Eval prompt: csv-to-parquet-migration

Optimize this Athena table for query performance and cost. Walk the
optimization framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

## Scenario

Database: `analytics_db`
Table: `events_csv-to-parquet-migration`
Region: us-east-1

## Known facts

- **Table DDL** (`aws glue get-table`):
  - `InputFormat`: `org.apache.hadoop.mapred.TextInputFormat` (CSV)
  - `Compressed`: `false`
  - `Location`: `s3://data-lake/events/`
  - `Columns`: 42 columns (event_id, user_id, event_type, amount, ...)
  - `PartitionKeys`: `[]` (unpartitioned)

- **Query history** (top 10 queries, last 7 days):
  - `SELECT * FROM ... WHERE amount > 100` — scans 1.2 TB, runtime 320s
  - `SELECT user_id, event_type FROM ... WHERE event_time >= '2026-07-01'`
    — scans 1.2 TB, runtime 305s
  - Average queries/day: 220 (all scanning full 1.2 TB)
  - All top queries filter by `event_time` date range

- **Workgroup** (`aws athena get-work-group`):
  - `BytesScannedCutoffPerQuery`: 0 (no limit set)
  - `EnforceWorkGroupConfiguration`: false
  - `EngineVersion`: Athena engine version 3

## Symptom

Table is 1.2 TB in CSV format. Every query scans the full table. Monthly
Athena cost for this table: ~$3,280.
