# Eval: missing-execution-role

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — execution role required for runtime AWS API calls

## Prompt

Deploy an EMR Serverless Spark application named "report-spark-prod"
in us-east-1. Release label emr-7.2.0. Execution role: NONE
PROVIDED (the operator forgot to create the IAM role). Pre-
initialized capacity: 20 workers. Maximum capacity: 100 workers.
VPC access: subnets subnet-aaa, subnet-bbb, security group
sg-emr-prod. S3 log bucket s3://emr-logs-123456789012/report/.
Job: entry point s3://etl-scripts/report.py, args --source
s3://raw-data/sales/ --target s3://curated/sales/. Account:
123456789012.
