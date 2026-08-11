# Baseline (no-skill) response: create-vault-ready

This file captures what a generic assistant produces WITHOUT the
backup-vault-operator skill loaded.

---

To create a backup vault, use:

```bash
aws backup create-backup-vault \
  --backup-vault-name prod-daily-vault \
  --encryption-key-arn arn:aws:kms:us-east-1:111111111111:key/abcd1234-5678-90ef-1234-567890abcdef
```

You can add tags with `--tags`.
