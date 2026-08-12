# Baseline (no-skill) — vault-lock-compliance-mode-verification

> This is the response a model produces **without** the skill
> definition. It does not distinguish COMPLIANCE from GOVERNANCE Vault
> Lock modes, may treat them as equivalent, and does not emit the
> AUTOMATION_DEPLOYED checklist. Generated for with-skill-vs-baseline
> comparison.

---

Check the vault:

```bash
aws backup describe-backup-vault --backup-vault-name compliant-vault
```

If it has a lock, it should be compliant.
