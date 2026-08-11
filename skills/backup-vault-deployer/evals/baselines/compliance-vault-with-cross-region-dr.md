# Baseline (no-skill) — compliance-vault-with-cross-region-dr

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the compliance vs
> governance mode immutability distinction, the lifecycle-within-
> lock-window cross-check, the cross-region copy destination
> prerequisite verification (destination vault + KMS key), the
> continuous backup PITR requirement (RecoveryPointType=CONTINUOUS),
> and the READY_TO_DEPLOY checklist format. Generated for with-skill-
> vs-baseline comparison.

---

Here is how to create the backup vault and plan:

```bash
aws backup create-backup-vault \
  --backup-vault-name production-backup-vault \
  --encryption-key-arn alias/backup-encryption-key

aws backup put-backup-vault-lock-configuration \
  --backup-vault-name production-backup-vault \
  --min-retention-days 90 --max-retention-days 365

aws backup create-backup-plan --backup-plan file://plan.json
```

Then add cross-region copy to the plan and create the selection.
