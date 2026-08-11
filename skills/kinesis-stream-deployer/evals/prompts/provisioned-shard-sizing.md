# Eval: provisioned-shard-sizing

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — provisioned mode, shard count from write throughput (5 MiB/sec + 3000 records/sec → 5 shards), standard GetRecords consumer

## Prompt

Create a Kinesis Data Stream named events-stream in us-east-1.
Use provisioned capacity mode. Expected write throughput is
5 MiB/sec and 3000 records/sec. Use standard GetRecords consumer
(no enhanced fan-out). Retention 48 hours. Producer is ECS task
role events-producer-role. Consumer is EC2 role events-consumer-role.
CloudWatch alarms for IteratorAge and WriteProvisionedThroughputExceeded
to SNS arn:aws:sns:us-east-1:123456789012:alerts. Tags:
Environment=staging, Service=events. Account: 123456789012.
