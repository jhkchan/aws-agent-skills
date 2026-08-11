# Baseline (no-skill) response: governance-mode-misuse-blocked

This file captures what a generic assistant produces WITHOUT the
backup-vault-operator skill loaded.

---

Here is the vault lock in governance mode for your HIPAA vault:

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name hipaa-archive-vault \
  --mode GOVERNANCE \
  --min-retention-days 2189 \
  --max-retention-days 2555
```

Governance mode is recommended because it can be removed if you ever
need to delete recovery points early.
