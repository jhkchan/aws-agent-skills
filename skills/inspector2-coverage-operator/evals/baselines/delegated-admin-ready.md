# Baseline (no-skill) response: delegated-admin-ready

This file captures what a generic assistant produces WITHOUT the
inspector2-coverage-operator skill loaded.

---

To set up a delegated admin for Inspector:

```bash
aws inspector2 enable-delegated-admin-account \
  --delegated-admin-account-id 222222222222 \
  --region us-east-1
```

You can then configure auto-enable from the delegated admin.
