# Eval: hive-batch-application

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Hive application, cold start, Glue catalog, Tez

## Prompt

Deploy a production EMR Serverless Hive application named
"hive-batch-prod" in us-east-1. Release label emr-7.2.0.
Execution role EMRHiveExecRole with S3 GetObject on
hive-scripts bucket, S3 PutObject on emr-logs-123456789012,
Glue GetTable/GetDatabase/GetPartitions. No pre-initialized
capacity (cold start acceptable for nightly batch). Maximum
capacity: 50 workers. No VPC access needed (Glue catalog only).
S3 log bucket s3://emr-logs-123456789012/hive-batch/. CloudWatch
log group /aws/emr-serverless/hive-batch-prod. Job: HiveQL
query SELECT COUNT(*) FROM sales WHERE dt = '2026-08-11', init
script s3://hive-scripts/hive-init.sql, Tez engine.
Auto-start enabled, auto-stop idle 5 min. Account: 123456789012.
