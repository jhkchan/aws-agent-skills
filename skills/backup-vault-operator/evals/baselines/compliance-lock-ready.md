# Baseline (no-skill) response: compliance-lock-ready

This file captures what a generic assistant produces WITHOUT the
backup-vault-operator skill loaded.

---

To lock the vault in compliance mode, use:

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name prod-compliance-vault \
  --min-retention-days 30 \
  --max-retention-days 3650
```

The vault will be locked.
