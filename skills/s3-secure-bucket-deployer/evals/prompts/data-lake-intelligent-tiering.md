# Eval: data-lake-intelligent-tiering

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — data-lake workload with Intelligent-Tiering

## Prompt

Create a data lake landing zone bucket named "datalake-raw-zone"
in us-east-1. Use SSE-KMS with alias/datalake-kms-key. Enable
Intelligent-Tiering for the lifecycle (unknown access patterns).
Enable access logging to "datalake-logs". Versioning on. No
replication needed. Tags: Environment=production,
Workload=data-lake, Zone=raw. Account: 123456789012.
