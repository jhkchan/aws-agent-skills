# Eval: spark-production-etl

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — full checklist with execution role, capacity, VPC, job submission

## Prompt

Deploy a production EMR Serverless Spark application named
"etl-spark-prod" in us-east-1. Release label emr-7.2.0.
Execution role EMRServerlessExecRole with S3 GetObject on
etl-scripts and raw-data buckets, S3 PutObject on curated and
emr-logs-123456789012 buckets, Glue GetTable/GetDatabase,
CloudWatch Logs, Secrets Manager GetSecretValue on etl/db-creds.
Pre-initialized capacity: 50 workers, 4 vCPU / 16 GB each.
Maximum capacity: 200 workers burst ceiling. VPC access:
subnets subnet-aaa, subnet-bbb, security group sg-emr-prod.
S3 log bucket s3://emr-logs-123456789012/etl-spark-prod/.
CloudWatch log group /aws/emr-serverless/etl-spark-prod.
Job: entry point s3://etl-scripts/daily_transform.py, args
--source s3://raw-data/events/ --target s3://curated/events/
--date 2026-08-11. Spark config: AQE enabled, shuffle
partitions 200, KryoSerializer. Auto-start enabled, auto-stop
idle 15 min. Account: 123456789012.
