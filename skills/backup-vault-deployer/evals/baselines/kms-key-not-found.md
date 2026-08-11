# Baseline (no-skill) — kms-key-not-found

> This is the response a model produces **without** the skill
> definition. It creates the vault command with the nonexistent key
> alias without verifying the key exists, which will fail at runtime.
> Does not emit a PREREQUISITES_MISSING verdict. Generated for with-
> skill-vs-baseline comparison.

---

Here is the vault creation:

```bash
aws backup create-backup-vault \
  --backup-vault-name production-vault \
  --encryption-key-arn alias/nonexistent-key

aws backup put-backup-vault-lock-configuration \
  --backup-vault-name production-vault \
  --min-retention-days 30
```

Then create the backup plan with a daily schedule.
