# Eval: missing-source-stream

**Difficulty:** medium
**Branch:** PREREQUISITES_MISSING — source stream required for the application to read records

## Prompt

Deploy a Kinesis Data Analytics Flink application named
"etl-flink-prod" in us-east-1. Runtime environment FLINK-1_19.
Service execution role KDAExecutionRole with Kinesis
GetRecords on stream ingestion-events, S3 GetObject on
s3://kda-apps/etl-1.0.0.jar, CloudWatch Logs. Source: Kinesis
Data Stream ingestion-events — DOES NOT EXIST (the operator
referenced a stream name that was never created; describe-stream
returns ResourceNotFoundException). Destination: Kinesis Data
Stream etl-out. Checkpointing: interval 60000 ms. Parallelism:
4. Application code s3://kda-apps/etl-1.0.0.jar. Account:
123456789012.
