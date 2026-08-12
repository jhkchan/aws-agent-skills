# Baseline (no-skill) — encryption-audit-kms-coverage

> This is the response a model produces **without** the skill
> definition. It does not know how to check for KMS encryption on
> recovery points, misses the EncryptionKeyArn field, and does not
> emit the AUTOMATION_DEPLOYED checklist. Generated for
> with-skill-vs-baseline comparison.

---

List recovery points:

```bash
aws backup list-recovery-points-by-backup-vault --backup-vault-name default
```

Encryption should be there by default.
