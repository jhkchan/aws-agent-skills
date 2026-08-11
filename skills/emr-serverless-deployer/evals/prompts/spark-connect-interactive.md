# Eval: spark-connect-interactive

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Spark Connect, pre-initialized capacity, interactive auto-stop

## Prompt

Deploy a production EMR Serverless Spark application named
"analytics-spark-prod" in us-east-1. Release label emr-7.2.0.
Execution role EMRAnalyticsExecRole with S3 GetObject on
curated bucket, Glue GetTable/GetDatabase, CloudWatch Logs.
Pre-initialized capacity: 10 workers, 4 vCPU / 16 GB each.
Maximum capacity: 100 workers. VPC access: subnets subnet-aaa,
subnet-bbb, subnet-ccc, security group sg-emr-analytics. S3 log
bucket s3://emr-logs-123456789012/analytics/. CloudWatch log
group /aws/emr-serverless/analytics-spark-prod. Interactive
endpoint: Spark Connect for Jupyter notebooks. Auto-start
enabled, auto-stop idle 60 min (interactive workload). Account:
123456789012.
