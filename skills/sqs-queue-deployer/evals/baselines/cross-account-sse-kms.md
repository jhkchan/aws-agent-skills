# Baseline (no-skill) — cross-account-sse-kms

> This is the response a model produces **without** the skill definition.
> It sets up the queue and DLQ but does not flag that the KMS key policy
> needs to grant the foreign account kms:Decrypt — the #1 cross-account
> SSE-KMS deployment failure.

---

Here's how to set up cross-account SQS:

```bash
aws sqs create-queue \
  --queue-name shared-events \
  --attributes VisibilityTimeout=30,ReceiveMessageWaitTimeSeconds=20

aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/shared-events \
  --attributes KmsMasterKeyId=alias/shared-sqs-key

# Cross-account access policy
aws sqs set-queue-attributes \
  --queue-url https://sqs.us-east-1.amazonaws.com/111111111111/shared-events \
  --attributes Policy='{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::222222222222:root"},
      "Action": ["sqs:SendMessage", "sqs:ReceiveMessage"],
      "Resource": "arn:aws:sqs:us-east-1:111111111111:shared-events"
    }]
  }'
```

Make sure account 222222222222 has IAM permissions to access the queue.
