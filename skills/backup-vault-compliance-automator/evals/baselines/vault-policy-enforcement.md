# Baseline (no-skill) response: vault-policy-enforcement

This file captures what a generic assistant produces WITHOUT the
backup-vault-compliance-automator skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, lock mode
selection, cool-off management, coverage audit, encryption
verification, cross-region replication, expert AWS Backup knowledge).

---

You can add a vault policy that denies unencrypted backups. Use
put-backup-vault-policy with a JSON policy that has a Deny statement
for backups without encryption.

```
aws backup put-backup-vault-policy \
  --backup-vault-name prod-backup-vault \
  --policy '{"Statement":[{"Effect":"Deny","Action":"backup:*"}]}'
```

For the cross-account access, add an Allow statement for the source
account. You'll also need the KMS key ARN in the policy somewhere.
