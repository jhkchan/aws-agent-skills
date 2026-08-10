# Baseline (no-skill) — fifo-topic-lambda-subscriber

> This is the response a model produces **without** the skill definition.
> It creates the FIFO topic and subscribes Lambda without knowing that
> FIFO topics only support SQS FIFO queue subscribers — the subscription
> call will fail at runtime.

---

Here's how to create your FIFO topic:

```bash
aws sns create-topic --name payment-events.fifo \
  --attributes FifoTopic=true,ContentBasedDeduplication=true

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:payment-events.fifo \
  --protocol lambda \
  --notification-endpoint arn:aws:lambda:us-east-1:111111111111:function:payment-handler \
  --return-subscription-arn
```

Make sure the Lambda function has a resource-based policy allowing SNS
to invoke it.
