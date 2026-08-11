# Baseline (no-skill) response: fifo-type-mismatch-blocked

This file captures what a generic assistant produces WITHOUT the
sqs-dlq-operator skill loaded.

---

To create a DLQ for your FIFO queue:

```bash
aws sqs create-queue --queue-name prod-orders-dlq
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url <dlq-url> \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
aws sqs set-queue-attributes --queue-url <source-url> \
  --attributes RedrivePolicy='{"deadLetterTargetArn":"'$DLQ_ARN'","maxReceiveCount":"10"}'
```

Set the retention to 14 days. You may also want to enable content-based
deduplication on the DLQ if your source uses it.
