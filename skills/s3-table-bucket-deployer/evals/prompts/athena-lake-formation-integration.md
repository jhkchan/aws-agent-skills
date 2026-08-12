# Eval: athena-lake-formation-integration

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Athena via REST catalog (not S3 path), Lake Formation table-level SELECT grant, Iceberg v2 table with date partition

## Prompt

Create an S3 table bucket named bi-tables in us-east-1 account
123456789012. Create namespace reporting. Create an Iceberg v2
table named daily_revenue with columns: date (date), revenue
(double), region (string). Partition by day(date). Configure
Athena to query this table via the Iceberg REST catalog. Grant
Lake Formation SELECT permission on the table to the
AthenaUserRole. Tags: Environment=production.
