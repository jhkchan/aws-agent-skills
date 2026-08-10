# Eval: standard-queue-with-dlq

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — full checklist with DLQ, long polling, SSE-SQS, S3 access policy

## Prompt

Deploy a production SQS queue named "order-events" in us-east-1. It
receives messages from an S3 bucket "order-uploads" via S3 Event
Notification. A Lambda function "order-processor" consumes the queue.
The Lambda p99 processing time is about 8 seconds. Use a DLQ named
"order-events-dlq" with maxReceiveCount=5 and 14-day retention. Enable
SSE-SQS encryption. Long polling. Account: 111111111111.
