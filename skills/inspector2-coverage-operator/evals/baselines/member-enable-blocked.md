# Baseline (no-skill) response: member-enable-blocked

This file captures what a generic assistant produces WITHOUT the
inspector2-coverage-operator skill loaded.

---

To enable Inspector for the member account, run from the member:

```bash
aws inspector2 enable \
  --account-ids 333333333333 \
  --resource-types EC2 \
  --region us-east-1
```

Note that the account is in an Organization with delegated admin.
