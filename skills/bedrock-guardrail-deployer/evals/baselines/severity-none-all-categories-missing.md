# Baseline (no-skill) response: severity-none-all-categories-missing

This file captures what a generic assistant produces WITHOUT the
bedrock-guardrail-deployer skill loaded — the contrast that proves
the skill catches severity=NONE (explicitly disabled) that a baseline
would accept as "configured."

---

Your guardrail is set up. Since you applied it to the model, it will
start filtering:

```bash
aws bedrock create-guardrail \
  --name minimal-guardrail \
  --region us-east-1
```

You can always adjust the severity levels later. The guardrail is
active and will protect your application.
