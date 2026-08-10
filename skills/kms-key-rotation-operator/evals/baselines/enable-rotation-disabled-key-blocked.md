# Baseline (no-skill) response: enable-rotation-disabled-key-blocked

This file captures what a generic assistant produces WITHOUT the
kms-key-rotation-operator skill loaded.

---

To enable rotation, run:

```bash
aws kms enable-key-rotation \
  --key-id arn:aws:kms:us-east-1:111111111111:key/disabled123-...
```

If the key is disabled, you may need to re-enable it first. Note that
disabling a key stops all cryptographic operations.
