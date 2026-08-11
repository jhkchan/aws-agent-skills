# Eval: flink-production-streaming

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — full checklist with execution role, checkpointing, parallelism, source, destination

## Prompt

Deploy a production Kinesis Data Analytics Flink application named
"fraud-detection-flink" in us-east-1. Runtime environment
FLINK-1_19. Service execution role KDAExecutionRole with
Kinesis GetRecords/GetShardIterator on stream transactions,
Kinesis PutRecord/PutRecords on stream alerts, S3 GetObject on
s3://kda-apps/fraud-detection-1.0.0.jar, CloudWatch Logs on
/aws/kinesis-analytics/fraud-detection-flink. Source: Kinesis
Data Stream transactions (4 shards, ACTIVE), starting position
LATEST. Destination: Kinesis Data Stream alerts. Checkpointing:
interval 60000 ms, min pause 5000 ms. Parallelism: 4,
parallelismPerKPU 1. Application snapshots enabled. Auto-scaling
off. CloudWatch log group /aws/kinesis-analytics/fraud-detection-flink.
Account: 123456789012.
