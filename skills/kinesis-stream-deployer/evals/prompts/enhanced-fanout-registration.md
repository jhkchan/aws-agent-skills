# Eval: enhanced-fanout-registration

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — provisioned 10-shard stream, 4 enhanced fan-out consumers with SubscribeToShard, SSE-KMS AWS-managed key

## Prompt

Create a Kinesis Data Stream named clickstream in us-east-1.
Provisioned mode, 10 shards. I have 4 consumer applications that
each need dedicated read throughput with low latency. Register
enhanced fan-out consumers: realtime-analytics, ml-feature-pipeline,
audit-logger, data-archive. Retention 72 hours. SSE-KMS with
AWS-managed key alias/aws/kinesis. Account: 123456789012.
