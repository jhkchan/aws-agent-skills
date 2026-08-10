# Baseline (no-skill) — missing-root-break-glass

> This is the response a model produces **without** the skill definition.
> It accepts the policy without flagging the missing root break-glass
> statement — a critical error that makes the key unrecoverable on any
> future policy misconfiguration.

---

```bash
aws kms create-key \
  --description "Audit CMK" \
  --policy file://policy.json

aws kms create-alias \
  --alias-name alias/audit-cmk \
  --target-key-id <key-id>
```

In the policy, grant the audit-team role kms:Encrypt,
kms:Decrypt, kms:GenerateDataKey*, and the admin actions.

A 7-day deletion window is fine — it's the minimum.
