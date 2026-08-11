# Eval: studio-notebook-zeppelin

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Zeppelin runtime, Glue Data Catalog, deploy-as-application

## Prompt

Deploy a Kinesis Data Analytics Studio notebook named
"fraud-explore-notebook" in us-east-1. Runtime environment
ZEPPELIN-FLINK-1_0. Service execution role KDAExecutionRole
with Kinesis GetRecords on stream transactions, S3 GetObject
on s3://kda-apps/custom-udf-1.0.0.jar, CloudWatch Logs on
/aws/kinesis-analytics/fraud-explore-notebook. Source: Kinesis
Data Stream transactions (ACTIVE). Glue Data Catalog
integration with database default. Deploy-as-application
enabled (notebook can be promoted to a STREAMING application).
Log level INFO. Account: 123456789012.
