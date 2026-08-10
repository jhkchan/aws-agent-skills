# Baseline (no-skill) response: enable-rotation-symmetric-cmk-ready

This file captures what a generic assistant produces WITHOUT the
kms-key-rotation-operator skill loaded.

---

To enable automatic key rotation on your KMS key, run:

```bash
aws kms enable-key-rotation \
  --key-id arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-...
```

You can verify the rotation status with:

```bash
aws kms get-key-rotation-status \
  --key-id arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-...
```

This will enable annual rotation of the cryptographic material.
