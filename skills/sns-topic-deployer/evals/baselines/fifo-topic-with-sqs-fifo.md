# Baseline (no-skill) — fifo-topic-with-sqs-fifo

> This is the response a model produces **without** the skill definition.
> It creates the FIFO topic and SQS subscription but does not configure
> delivery status logging, the filter policy, or the structured checklist.

---

Here's how to create your FIFO topic:

```bash
aws sns create-topic --name transaction-events.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:transaction-events.fifo \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:transaction-queue.fifo \
  --return-subscription-arn
```

Make sure the SQS FIFO queue has its own redrive policy with
maxReceiveCount=10. The queue policy must grant SNS permission to send
messages.
