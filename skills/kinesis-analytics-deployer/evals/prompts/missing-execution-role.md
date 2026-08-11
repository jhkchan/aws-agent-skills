# Eval: missing-execution-role

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — execution role required for runtime AWS API calls

## Prompt

Deploy a Kinesis Data Analytics Flink application named
"report-flink-prod" in us-east-1. Runtime environment
FLINK-1_19. Service execution role: NONE PROVIDED (the operator
forgot to create the IAM role). Source: Kinesis Data Stream
events (ACTIVE). Destination: Kinesis Data Stream report-out.
Checkpointing: interval 60000 ms. Parallelism: 2. Application
code s3://kda-apps/report-1.0.0.jar. CloudWatch log group
/aws/kinesis-analytics/report-flink-prod. Account: 123456789012.
