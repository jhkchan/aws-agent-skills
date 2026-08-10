# Baseline (no-skill) response: enable-rotation-asymmetric-key-blocked

This file captures what a generic assistant produces WITHOUT the
kms-key-rotation-operator skill loaded.

---

To enable rotation on your signing key, run:

```bash
aws kms enable-key-rotation \
  --key-id arn:aws:kms:us-east-1:111111111111:key/rsa12345-...
```

This will enable annual rotation of the key material. You can verify
with `get-key-rotation-status` after.
