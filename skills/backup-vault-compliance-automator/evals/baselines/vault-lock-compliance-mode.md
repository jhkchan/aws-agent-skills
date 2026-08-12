# Baseline (no-skill) response: vault-lock-compliance-mode

This file captures what a generic assistant produces WITHOUT the
backup-vault-compliance-automator skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, lock mode
selection, cool-off management, coverage audit, encryption
verification, cross-region replication, expert AWS Backup knowledge).

---

You can set up a Vault Lock on your backup vault to make the
backups immutable. Use compliance mode for SEC 17a-4 requirements.

```
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name compliance-vault \
  --min-retention-days 2557
```

Make sure the retention period is correct because once it's locked
you can't change it. You should also verify that all your recovery
points are encrypted before locking.
