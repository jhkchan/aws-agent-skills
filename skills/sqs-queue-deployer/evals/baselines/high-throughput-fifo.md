# Baseline (no-skill) — high-throughput-fifo

> This is the response a model produces **without** the skill definition.
> It creates a standard FIFO queue (300 TPS) without the high-throughput
> attributes, missing the 1500 TPS requirement entirely. It also does not
> configure partial batch responses for the Lambda consumer.

---

Here's how to create your FIFO queue:

```bash
aws sqs create-queue \
  --queue-name bulk-orders.fifo \
  --attributes FifoQueue=true,ContentBasedDeduplication=true,VisibilityTimeout=300

aws sqs create-queue \
  --queue-name bulk-orders-dlq.fifo \
  --attributes FifoQueue=true

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/bulk-orders-dlq.fifo \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/bulk-orders.fifo \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"10\"}"
```

Then create the Lambda event source mapping:

```bash
aws lambda create-event-source-mapping \
  --function-name bulk-processor \
  --event-source-arn arn:aws:sqs:us-east-1:111111111111:bulk-orders.fifo \
  --batch-size 10
```
