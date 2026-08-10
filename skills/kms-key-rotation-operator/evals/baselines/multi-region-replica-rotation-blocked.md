# Baseline (no-skill) response: multi-region-replica-rotation-blocked

This file captures what a generic assistant produces WITHOUT the
kms-key-rotation-operator skill loaded.

---

To enable rotation on your Multi-Region key, run:

```bash
aws kms enable-key-rotation \
  --key-id arn:aws:kms:us-east-1:111111111111:key/multi-replica-...
```

If you get an error about replicas, you may need to enable rotation on
the primary key instead. Multi-Region keys have a primary that
controls rotation.
