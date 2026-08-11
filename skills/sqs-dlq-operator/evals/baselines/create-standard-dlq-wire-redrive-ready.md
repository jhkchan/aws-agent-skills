# Baseline (no-skill) response: create-standard-dlq-wire-redrive-ready

This file captures what a generic assistant produces WITHOUT the
sqs-dlq-operator skill loaded.

---

To create a DLQ and wire it to your source queue:

```bash
aws sqs create-queue --queue-name prod-orders-dlq
DLQ_ARN=$(aws sqs get-queue-attributes --queue-url <dlq-url> \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)
aws sqs set-queue-attributes --queue-url <source-url> \
  --attributes RedrivePolicy='{"deadLetterTargetArn":"'$DLQ_ARN'","maxReceiveCount":"5"}'
```

Set the retention period to 14 days so you have time to analyze
messages. Also make sure your Lambda consumer handles errors properly.
