# Eval: on-demand-enhanced-fanout-sse

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — on-demand mode, enhanced fan-out consumer, SSE-KMS with CMK, CloudWatch IteratorAge alarm

## Prompt

Create a Kinesis Data Stream named telemetry-ingest in us-east-1.
Use on-demand capacity mode. Register an enhanced fan-out consumer
named realtime-processor. Enable SSE-KMS with customer-managed key
alias/kinesis/telemetry-ingest. Set retention to 168 hours. Producer
is EC2 role EC2-producer-role. Consumer is Lambda role
Lambda-consumer-role. CloudWatch alarm for IteratorAge > 300000ms to
SNS topic arn:aws:sns:us-east-1:123456789012:alerts. Tags:
Environment=production, Service=telemetry. Account: 123456789012.
