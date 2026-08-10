# Baseline (no-skill) — http-subscription-no-logging

> This is the response a model produces **without** the skill definition.
> It creates the topic and HTTPS subscription without flagging that
> delivery status logging is missing — SNS will retry HTTP for 4 hours
> then silently drop failed messages with no visibility.

---

Here's how to create your SNS topic with an HTTPS subscriber:

```bash
aws sns create-topic --name webhook-delivery

aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:webhook-delivery \
  --protocol https \
  --notification-endpoint https://api.partner.com/webhook \
  --return-subscription-arn
```

The HTTPS endpoint will receive a confirmation message from SNS. Visit
the SubscribeURL to confirm the subscription. Make sure the endpoint
can handle SNS message format.
