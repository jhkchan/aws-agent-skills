# Baseline (no-skill) response: delivery-policy-dlq-setup

This file captures what a generic assistant produces WITHOUT the
sns-subscription-operator skill loaded.

---

To set up a delivery retry policy and DLQ on your subscription, you
can use set-subscription-attributes:

```bash
# Delivery policy
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:us-east-1:111111111111:alert-notifications:5678-efgh \
  --attribute-name DeliveryPolicy \
  --attribute-value '{"healthyRetryPolicy": {"numRetries": 5}}'

# DLQ
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:us-east-1:111111111111:alert-notifications:5678-efgh \
  --attribute-name RedrivePolicy \
  --attribute-value '{"deadLetterTargetArn": "arn:aws:sqs:us-east-1:111111111111:sns-dlq"}'
```

Make sure the DLQ queue exists and has the right permissions.
