# Eval: batch-load-task

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — batch load task created with CSV data source S3 bucket and report configuration

## Prompt

Create a Timestream database named HistoricalData and table
SensorArchive in us-east-1 with memory store TTL 1 hour and
magnetic store TTL 3650 days. Create a batch load task to ingest
CSV data from S3 bucket historical-sensor-data (prefix 2024/)
into the table. Report bucket: batch-load-reports. Tags:
Environment=production, Purpose=historical-backfill.
