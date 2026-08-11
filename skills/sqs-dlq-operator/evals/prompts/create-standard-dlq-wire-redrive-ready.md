# Eval prompt: create-standard-dlq-wire-redrive-ready

Plan the following SQS DLQ creation and redrive wiring, then emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, STATE, NOTES).

Operation: create
Source queue: prod-orders (Standard, VisibilityTimeout=60)
DLQ name: prod-orders-dlq (Standard, 14-day retention)
maxReceiveCount: 5
Region: us-east-1. Account: 111111111111.

```json
{
  "PreFlightChecks": {
    "sqs.get-queue-url.prod-orders": "https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders",
    "sqs.get-queue-attributes.prod-orders": {
      "FifoQueue": "not set (Standard)",
      "VisibilityTimeout": "60",
      "RedrivePolicy": "not set"
    },
    "sqs.get-queue-url.prod-orders-dlq": "NonExistentQueue (name available)",
    "lambda.list-event-source-mappings": {
      "UUID": "a1b2c3d4",
      "BatchSize": 10,
      "VisibilityTimeout": 60,
      "FunctionResponseTypes": ["ReportBatchItemFailures"]
    },
    "lambda.Duration.p99": "8s (last 7 days)"
  }
}
```
