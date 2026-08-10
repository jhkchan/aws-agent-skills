# Eval: fifo-topic-with-sqs-fifo

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — FIFO topic with correct SQS FIFO subscriber

## Prompt

Deploy a production FIFO SNS topic named "transaction-events.fifo" in
us-east-1. ContentBasedDeduplication=true. Subscriber: SQS FIFO queue
"transaction-queue.fifo" (same account). Enable SSE-KMS with AWS-managed
key. Enable SQS delivery status logging. maxReceiveCount on the SQS queue
is 10. Account: 111111111111.
