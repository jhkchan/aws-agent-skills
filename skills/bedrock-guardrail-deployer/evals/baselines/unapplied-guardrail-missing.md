# Baseline (no-skill) response: unapplied-guardrail-missing

This file captures what a generic assistant produces WITHOUT the
bedrock-guardrail-deployer skill loaded — the contrast that proves
the skill catches the unapplied-guardrail trap that a baseline would
miss entirely.

---

Your guardrail plan looks good. Create the guardrail with your filters:

```bash
aws bedrock create-guardrail \
  --name prod-safety-guardrail \
  --content-policy-config '{"filtersConfig":[...]}' \
  --region us-east-1
```

You can apply it to your models later when you're ready. The guardrail
will be ready in the console for whenever you need it.
