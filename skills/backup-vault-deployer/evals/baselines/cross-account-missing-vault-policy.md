# Baseline (no-skill) — cross-account-missing-vault-policy

> This is the response a model produces **without** the skill
> definition. It creates the source vault and backup plan with a
> cross-account copy rule without verifying that the destination
> vault access policy grants backup:CopyIntoBackupVault to the source
> account. The source backup will succeed but the copy will fail
> silently with AccessDenied. Generated for with-skill-vs-baseline
> comparison.

---

Create the source vault and plan with cross-account copy:

```bash
aws backup create-backup-vault \
  --backup-vault-name source-vault

aws backup create-backup-plan --backup-plan file://plan.json
# plan has CopyActions to dest-vault in us-west-2
```

The cross-account copy should work since the KMS key policy is
configured. Add the selection and you are ready.
