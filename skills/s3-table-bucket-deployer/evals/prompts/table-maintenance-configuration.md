# Eval: table-maintenance-configuration

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — compaction (target 512MB, min 10 files), snapshot management (max 14d, min 10), unreferenced file cleanup (max 30d), all ENABLED with tuned settings

## Prompt

Create an S3 table bucket named ops-tables in us-east-1 account
123456789012. Create namespace telemetry. Create an Iceberg v2
table named events with columns: event_id (long), event_time
(timestamp), event_type (string), payload (string). Partition by
day(event_time). Configure maintenance: compaction target file
size 512MB, min input files 10. Snapshot management max age 14
days, min snapshots 10. Unreferenced file cleanup max file age
30 days. Tags: Environment=production, Workload=telemetry.
