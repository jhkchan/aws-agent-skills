# Baseline (no-skill) — allow-all-insecure

> This is the response a model produces **without** the skill
> definition. It creates the ledger with the insecure configuration
> without flagging that ALLOW_ALL defeats the purpose of an immutable
> ledger, does not warn about missing deletion protection for a
> production environment, and omits the prerequisite-check /
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Create the ledger:

```bash
aws qldb create-ledger \
  --name prod-ledger \
  --permissions-mode ALLOW_ALL \
  --no-deletion-protection \
  --region us-east-1
```

Then create tables and start inserting data.
