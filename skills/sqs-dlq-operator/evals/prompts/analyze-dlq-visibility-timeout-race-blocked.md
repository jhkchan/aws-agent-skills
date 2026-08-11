# Eval prompt: analyze-dlq-visibility-timeout-race-blocked

Diagnose why messages are accumulating in the DLQ and emit the standard
VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, STATE, NOTES).

Operation: analyze
DLQ: prod-orders-dlq
Region: us-east-1. Account: 111111111111.

```json
{
  "PreFlightChecks": {
    "sqs.get-queue-attributes.prod-orders-dlq": {
      "ApproximateNumberOfMessagesVisible": 1247,
      "MessageRetentionPeriod": 1209600
    },
    "sqs.receive-message.prod-orders-dlq": {
      "messagesReceived": 10,
      "allPayloadsValid": true,
      "ApproximateReceiveCount": 10
    },
    "sqs.get-queue-attributes.prod-orders": {
      "VisibilityTimeout": 30,
      "RedrivePolicy.maxReceiveCount": 10
    },
    "lambda.list-event-source-mappings": {
      "UUID": "a1b2c3d4",
      "BatchSize": 10,
      "VisibilityTimeout": 30,
      "FunctionResponseTypes": []
    },
    "lambda.Duration.p99": "52s (last 7 days)",
    "lambda.cloudwatch-logs.ERROR": "0 errors in last 1 hour"
  }
}
```
