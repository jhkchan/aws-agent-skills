# Baseline (no-skill) response: cross-account-subscription-blocked

This file captures what a generic assistant produces WITHOUT the
sns-subscription-operator skill loaded.

---

To subscribe your SQS queue to a topic in another account, just run:

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:222222222222:shared-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:my-queue
```

You may need to make sure the topic policy allows your account to
subscribe. If you get an authorization error, ask the topic owner to
add your account to the topic policy.
