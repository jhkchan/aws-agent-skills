# Baseline (no-skill) response: create-sqs-subscription-ready

This file captures what a generic assistant produces WITHOUT the
sns-subscription-operator skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, pre-checks, confirmation
flow, filter-policy match, CONFIRM gate).

---

To create an SNS subscription from your topic to your SQS queue, run:

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:111111111111:order-events \
  --protocol sqs \
  --notification-endpoint arn:aws:sqs:us-east-1:111111111111:order-processing-queue
```

If you want a filter policy, you can set it after:

```bash
aws sns set-subscription-attributes \
  --subscription-arn <sub-arn> \
  --attribute-name FilterPolicy \
  --attribute-value '{"event_type": ["order_created", "order_updated"]}'
```

You can also enable raw message delivery if you want.
