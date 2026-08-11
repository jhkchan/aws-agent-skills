# Eval: standard-fifo-with-dedup-and-dlq

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — standard FIFO, content-based dedup, FIFO DLQ with maxReceiveCount, SSE-KMS, per-entity message group IDs

## Prompt

Create an SQS FIFO queue named order-processing.fifo in
us-east-1. Content-based deduplication enabled. Per-entity
message group IDs (customer ID). Visibility timeout 120
seconds. FIFO DLQ: order-processing-dlq.fifo with
maxReceiveCount 5. SSE-KMS encryption with customer-managed
key arn:aws:kms:us-east-1:123456789012:key/abc123. Tags:
Environment=production, Application=order-service.
