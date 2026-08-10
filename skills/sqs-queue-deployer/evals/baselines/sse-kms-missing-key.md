# Baseline (no-skill) — sse-kms-missing-key

> This is the response a model produces **without** the skill definition.
> It attempts to set SSE-KMS with a non-existent key alias without
> verifying the key exists first, and does not flag the missing
> prerequisite.

---

Here's how to create your encrypted queue:

```bash
aws sqs create-queue \
  --queue-name secure-events \
  --attributes VisibilityTimeout=60,ReceiveMessageWaitTimeSeconds=20

aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/secure-events \
  --attributes KmsMasterKeyId=alias/sqs-secure-key
```

Create the DLQ and link it:

```bash
aws sqs create-queue --queue-name secure-events-dlq

DLQ_ARN=$(aws sqs get-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/secure-events-dlq \
  --attribute-names QueueArn --query 'Attributes.QueueArn' --output text)

aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/secure-events \
  --attributes RedrivePolicy="{\"deadLetterTargetArn\":\"$DLQ_ARN\",\"maxReceiveCount\":\"5\"}"
```
