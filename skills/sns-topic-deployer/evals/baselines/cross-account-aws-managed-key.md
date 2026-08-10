# Baseline (no-skill) — cross-account-aws-managed-key

> This is the response a model produces **without** the skill definition.
> It sets up the topic with the AWS-managed key and the cross-account
> subscriber without flagging that the AWS-managed key blocks cross-account
> decryption — messages will silently fail to arrive in the subscriber
> queue.

---

Here's how to set up cross-account SNS:

```bash
aws sns create-topic --name shared-events

aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:shared-events \
  --attribute-name KmsMasterKeyId \
  --attribute-value alias/aws/sns

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:shared-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:222222222222:partner-queue \
  --return-subscription-arn
```

Make sure the topic policy allows account 222222222222 to subscribe.
