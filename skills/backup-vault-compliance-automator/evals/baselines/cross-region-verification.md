# Baseline (no-skill) response: cross-region-verification

This file captures what a generic assistant produces WITHOUT the
backup-vault-compliance-automator skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, lock mode
selection, cool-off management, coverage audit, encryption
verification, cross-region replication, expert AWS Backup knowledge).

---

Your cross-region replication looks good since the last 10 copy
jobs are all completed. You can verify the recovery points in
us-west-2 by listing them from the destination vault.

```
aws backup list-recovery-points-by-backup-vault \
  --backup-vault-name prod-backup-vault-dr \
  --region us-west-2
```

Make sure the KMS key in us-west-2 is working and that the vault
policy allows cross-region copies.
