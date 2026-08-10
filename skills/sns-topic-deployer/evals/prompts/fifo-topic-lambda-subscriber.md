# Eval: fifo-topic-lambda-subscriber

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — FIFO topics only support SQS FIFO subscribers

## Prompt

Deploy a FIFO SNS topic named "payment-events.fifo" in us-east-1.
ContentBasedDeduplication=true. Subscriber: Lambda function
"payment-handler". SSE-KMS with AWS-managed key. Account: 111111111111.
