# Eval prompt: stale-partitions-no-projection

Diagnose the Athena query failure for the following table. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Athena query returns zero rows for today's data even though
the S3 bucket has the files. The query SUCCEEDS with no error but
returns an empty result set.

```text
Database: analytics
Table: events_daily
Query: SELECT count(*) FROM analytics.events_daily
       WHERE dt = '2026-08-05'
QueryStatus: SUCCEEDED
QueryResult: 0 rows

DDL:
  CREATE EXTERNAL TABLE analytics.events_daily (
    event_id   STRING,
    event_type STRING,
    payload    STRING
  )
  PARTITIONED BY (dt DATE)
  STORED AS PARQUET
  LOCATION
    's3://prod-analytics/events/'

Glue get-partitions:
  Count: 0

S3 listing:
  aws s3 ls s3://prod-analytics/events/dt=2026-08-05/
  2026-08-05 14:00:00   1234567 part-00001.parquet
  2026-08-05 14:00:00    987654 part-00002.parquet

Table TBLPROPERTIES:
  (no projection.* properties set)

Workgroup: primary
```

Data exists on S3 but the partition metadata was never loaded. The
table has no partition projection configured, so new partitions
require MSCK REPAIR.
