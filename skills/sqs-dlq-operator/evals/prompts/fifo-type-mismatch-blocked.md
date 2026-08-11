# Eval prompt: fifo-type-mismatch-blocked

Plan the following SQS DLQ creation and emit the standard VERDICT block
(OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, STATE,
NOTES).

Operation: create
Source queue: prod-orders.fifo (FIFO, VisibilityTimeout=120)
Proposed DLQ name: prod-orders-dlq (Standard — WRONG, should be .fifo)
maxReceiveCount: 10
Region: us-east-1. Account: 111111111111.

```json
{
  "PreFlightChecks": {
    "sqs.get-queue-url.prod-orders.fifo": "https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders.fifo",
    "sqs.get-queue-attributes.prod-orders.fifo": {
      "FifoQueue": "true",
      "VisibilityTimeout": "120"
    },
    "sqs.get-queue-url.prod-orders-dlq": "NonExistentQueue (name available)"
  }
}
```
