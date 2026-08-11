# Baseline (no-skill) response: lock-dr-vault-ready

This file captures what a generic assistant produces WITHOUT the
backup-cross-region-operator skill loaded.

---

To apply a vault lock on the DR vault:

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name dr-vault \
  --changeable-for-days 3 \
  --min-retention-days 30 \
  --max-retention-days 3650 \
  --region us-west-2
```

The lock will be active immediately.
