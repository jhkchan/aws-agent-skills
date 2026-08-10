# Baseline (no-skill) — standard-queue-with-dlq

> This is the response a model produces **without** the skill definition.
> It provides a basic create-queue command but misses the visibility timeout
> tuning for the Lambda consumer, the structured checklist, the S3 access
> policy with aws:SourceArn condition, and the 14-day DLQ retention.

---

Here's how to create your SQS queue:

```bash
aws sqs create-queue \
  --queue-name order-events \
  --attributes VisibilityTimeout=30,ReceiveMessageWaitTimeSeconds=20
```

You should also create a DLQ:

```bash
aws sqs create-queue --queue-name order-events-dlq
```

Then link them with a redrive policy. For the S3 notification, you'll
need to add a queue policy allowing S3 to send messages. For the Lambda
consumer, create an event source mapping.

Make sure the Lambda function has permissions to read from the queue.
