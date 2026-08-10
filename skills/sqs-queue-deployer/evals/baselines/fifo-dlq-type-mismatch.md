# Baseline (no-skill) — fifo-dlq-type-mismatch

> This is the response a model produces **without** the skill definition.
> It creates the FIFO queue and links the Standard DLQ without flagging
> the type mismatch — a silent runtime failure where redriven messages
> are dropped.

---

Here's how to deploy your FIFO queue with the DLQ:

```bash
aws sqs create-queue \
  --queue-name payment-events.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true,VisibilityTimeout=120

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/payment-events-dlq \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/payment-events.fifo \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"10\"}"
```

The queue is ready. Make sure your consumers send a MessageGroupId with
each message.
