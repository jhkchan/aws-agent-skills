# Eval prompt: replay-no-active-consumer-blocked

Plan the DLQ replay and emit the standard VERDICT block (OPERATION,
VERDICT, TARGET, PRE_CHECKS, STEPS, POST_VERIFY, STATE, NOTES).

Operation: replay
DLQ: prod-orders-dlq -> Source: prod-orders
Region: us-east-1. Account: 111111111111.

```json
{
  "PreFlightChecks": {
    "sqs.get-queue-attributes.prod-orders-dlq": {
      "ApproximateNumberOfMessagesVisible": 842
    },
    "sqs.list-dead-letter-source-queues": ["https://sqs.us-east-1.amazonaws.com/111111111111/prod-orders"],
    "lambda.list-event-source-mappings": {
      "UUID": "a1b2c3d4",
      "State": "Disabling (mapping disabled during incident, not yet re-enabled)"
    },
    "rootCauseStatus": "consumer patched (deploy v1.4.2), but mapping NOT yet re-enabled"
  }
}
```
