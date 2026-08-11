# Baseline (no-skill) — lifecycle-outside-lock-window

> This is the response a model produces **without** the skill
> definition. It creates the vault and plan without flagging that
> DeleteAfterDays=7 violates the vault lock MinRetentionDays=90,
> which will cause backup jobs to fail. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Sure, here is the vault and plan:

```bash
aws backup create-backup-vault \
  --backup-vault-name locked-vault

aws backup put-backup-vault-lock-configuration \
  --backup-vault-name locked-vault \
  --min-retention-days 90 --max-retention-days 365

aws backup create-backup-plan --backup-plan file://plan.json
# plan has DeleteAfterDays=7
```

Then add a tag-based selection and you are done.
