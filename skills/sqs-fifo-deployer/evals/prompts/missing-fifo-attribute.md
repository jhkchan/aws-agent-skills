# Eval: missing-fifo-attribute

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — queue name 'my-queue' lacks .fifo suffix; FIFO queues require the suffix

## Prompt

Create an SQS FIFO queue named my-queue in us-east-1. Enable
FIFO ordering, content-based deduplication, visibility
timeout 60 seconds. DLQ: my-queue-dlq.fifo. Tags:
Environment=production.
