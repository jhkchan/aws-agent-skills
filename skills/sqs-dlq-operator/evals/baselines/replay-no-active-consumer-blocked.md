# Baseline (no-skill) response: replay-no-active-consumer-blocked

This file captures what a generic assistant produces WITHOUT the
sqs-dlq-operator skill loaded.

---

To replay messages from the DLQ back to the source queue:

```bash
aws sqs start-message-move-task \
  --source-arn arn:aws:sqs:us-east-1:111111111111:prod-orders-dlq \
  --destination-arn arn:aws:sqs:us-east-1:111111111111:prod-orders
```

You can check the status with list-message-move-tasks. Make sure your
consumer is ready to process the messages.
