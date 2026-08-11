# Baseline (no-skill) — governance-vault-with-continuous-backup

> This is the response a model produces **without** the skill
> definition. It creates the vault and plan but misses the governance
> vs compliance mode distinction (governance is a soft lock removable
> by privileged users), the continuous backup RecoveryPointType
> requirement, the lifecycle-within-lock-window cross-check, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

You can create the vault and plan like this:

```bash
aws backup create-backup-vault \
  --backup-vault-name dev-backup-vault \
  --encryption-key-arn alias/dev-backup-key

aws backup put-backup-vault-lock-configuration \
  --backup-vault-name dev-backup-vault \
  --min-retention-days 7 --max-retention-days 90
```

Create a backup plan with a daily schedule and add EC2 and EFS
resources to the selection.
