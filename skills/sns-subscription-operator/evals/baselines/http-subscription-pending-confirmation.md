# Baseline (no-skill) response: http-subscription-pending-confirmation

This file captures what a generic assistant produces WITHOUT the
sns-subscription-operator skill loaded.

---

Your subscription is pending confirmation. To confirm it, you need to
extract the token from the confirmation POST that SNS sent to your
endpoint and call confirm-subscription:

```bash
aws sns confirm-subscription \
  --topic-arn arn:aws:sns:us-east-1:111111111111:alert-notifications \
  --token 51b2ff37-extended-token-xyz
```

After that, the subscription should be active.
