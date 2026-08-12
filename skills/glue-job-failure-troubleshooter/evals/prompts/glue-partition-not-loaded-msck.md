# Eval prompt: glue-partition-not-loaded-msck

Diagnose the AWS Glue job issue for the following job. Walk the
symptom-driven diagnostic tree and emit the standard diagnostic block
(TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: Glue job `etl-aggregation` reads from Data Catalog table
`events_table`. The table exists and the S3 path has data, but the job
processes 0 records (`df.count() == 0`).

```text
JobName: glue-partition-not-loaded-msck
JobRunId: jr_jkl012
WorkerType: G.1X
NumberOfWorkers: 5
GlueVersion: glue-4.0

Data Catalog:
  Database: analytics
  Table: events_table
  StorageDescriptor.Location:
    s3://data-lake-prod/events/year=2026/month=08/day=05/
  TableType: EXTERNAL_TABLE

aws glue get-partitions --database analytics --table-name
  events_table: returns 0 partitions

aws s3 ls s3://data-lake-prod/events/year=2026/month=08/:
  - day=05/ (500 parquet files, 2 GB)
  - day=04/ (480 parquet files, 1.9 GB)
  - day=03/ (450 parquet files, 1.8 GB)

The data was written by Kinesis Firehose; no Glue crawler has
run since the data landed.
```

MSCK REPAIR TABLE is required after partition data lands in S3 (via
external processes like Firehose). Crawlers add partitions
automatically; Firehose does not. Verify the partition state and
recommend the fix.
