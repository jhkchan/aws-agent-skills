# Baseline (no-skill) response: full-guardrail-applied-ready

This file captures what a generic assistant produces WITHOUT the
bedrock-guardrail-deployer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, filter verification,
PII BLOCK-vs-AUDIT distinction, application target verification,
ApplyGuardrail test commands).

---

Here's how to create a Bedrock Guardrail:

```bash
aws bedrock create-guardrail \
  --name customer-app-guardrail \
  --description "Guardrail for customer app" \
  --region us-east-1
```

Then configure your filters in the console and apply it to your Agent.
Make sure to set the content filter levels and PII filters.
