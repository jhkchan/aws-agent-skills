# Baseline (no-skill) response: enable-standalone-ready

This file captures what a generic assistant produces WITHOUT the
inspector2-coverage-operator skill loaded.

---

To enable Inspector v2, use:

```bash
aws inspector2 enable \
  --account-ids 111111111111 \
  --resource-types EC2 ECR LAMBDA \
  --region us-east-1
```

Inspector will start scanning the resources in the account.
