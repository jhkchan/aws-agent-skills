# Baseline (no-skill) response: csv-to-parquet-migration

This file captures what a generic assistant produces WITHOUT the
athena-query-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, ordered framework, cost estimation).

---

Your Athena table is in CSV format and queries are scanning the full 1.2 TB
every time. You should consider converting to Parquet format which is much
more efficient for analytical queries.

To fix this, you can create a new table using CTAS (CREATE TABLE AS SELECT)
with Parquet format. Parquet is a columnar format so it will be much faster
for queries that only need a few columns. You should also consider adding
partitioning by date since your queries filter by event_time.

Also consider setting a data-scanned limit on your workgroup to prevent
expensive runaway queries.
