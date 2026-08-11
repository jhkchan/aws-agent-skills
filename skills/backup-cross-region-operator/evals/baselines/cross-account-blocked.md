# Baseline (no-skill) response: cross-account-blocked

This file captures what a generic assistant produces WITHOUT the
backup-cross-region-operator skill loaded.

---

To enable cross-account backup, set up an Organizations backup
policy:

```bash
aws organizations create-policy \
  --name "cross-account-backup" \
  --type BACKUP_POLICY \
  --content '...'
```

Attach the policy to the destination account. Then the source
account can copy to the destination vault.
