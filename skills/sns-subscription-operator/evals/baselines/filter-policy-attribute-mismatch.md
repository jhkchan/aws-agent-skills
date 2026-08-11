# Baseline (no-skill) response: filter-policy-attribute-mismatch

This file captures what a generic assistant produces WITHOUT the
sns-subscription-operator skill loaded.

---

If your SQS subscription isn't receiving messages, there could be a
few reasons. Check that the queue policy allows the SNS topic to send
messages. Also check if there's a filter policy that might be blocking
messages.

Your filter policy uses `event_type` but it looks like your publisher
might be using a different attribute name. You could try removing the
filter policy to see if messages start flowing:

```bash
aws sns set-subscription-attributes \
  --subscription-arn arn:aws:sns:us-east-1:111111111111:order-events:1234-abcd \
  --attribute-name FilterPolicy \
  --attribute-value '{}'
```

If that works, the issue is the filter policy. You might need to align
the attribute names.
