# Eval: basic-table-bucket-iceberg

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — table bucket creation, namespace before table (hard dependency), Iceberg v2 format, schema with column types, day partition transform, default maintenance enabled

## Prompt

Create an S3 table bucket named analytics-tables in us-east-1
account 123456789012. Create namespace sales_analytics. Create
an Iceberg table named orders with columns: order_id (long,
required), customer_id (long, required), order_date (timestamp,
required), amount (double), status (string). Partition by
day(order_date). Use Iceberg v2. Tags: Environment=production,
Team=analytics.
