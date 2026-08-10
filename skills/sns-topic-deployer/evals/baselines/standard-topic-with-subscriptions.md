# Baseline (no-skill) — standard-topic-with-subscriptions

> This is the response a model produces **without** the skill definition.
> It creates the topic and subscriptions but misses the S3 access policy
> with aws:SourceArn condition, the delivery status logging, the filter
> policy, and the structured checklist.

---

Here's how to create your SNS topic:

```bash
aws sns create-topic --name order-events

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-queue \
  --return-subscription-arn

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:111111111111:function:order-handler \
  --return-subscription-arn
```

You should also set up an access policy for S3 to publish to the topic.
Make sure the SQS queue and Lambda function have permissions to receive
messages from SNS.
