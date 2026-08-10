# Eval: fifo-dlq-type-mismatch

**Difficulty:** hard
**Branch:** PREREQUISITES_MISSING — DLQ type must match source queue type

## Prompt

Deploy a FIFO SQS queue named "payment-events.fifo" in us-east-1. It
needs a DLQ. The existing DLQ "payment-events-dlq" is a Standard queue
(not FIFO). maxReceiveCount=10. ContentBasedDeduplication=true.
Visibility timeout 120s. SSE-SQS encryption. Account: 111111111111.
