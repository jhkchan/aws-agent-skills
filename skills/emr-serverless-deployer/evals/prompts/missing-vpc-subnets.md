# Eval: missing-vpc-subnets

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — VPC subnets required for private database access

## Prompt

Deploy an EMR Serverless Spark application named "db-spark-prod"
in us-east-1. Release label emr-7.2.0. Execution role
      EMRDbExecRole with S3 GetObject on etl-scripts, Secrets Manager
GetSecretValue on etl/db-creds. Pre-initialized capacity: 30
workers. Maximum capacity: 100 workers. The Spark job reads from
a private Aurora PostgreSQL cluster at
db.cluster-xxx.us-east-1.rds.amazonaws.com in private subnets
subnet-aaa, subnet-bbb. NO VPC SUBNETS OR SECURITY GROUPS
CONFIGURED. S3 log bucket s3://emr-logs-123456789012/db-spark/.
Job: entry point s3://etl-scripts/db_read.py, args --jdbc-url
jdbc:postgresql://db.cluster-xxx.us-east-1.rds.amazonaws.com:5432/analytics
--secret etl/db-creds. Account: 123456789012.
