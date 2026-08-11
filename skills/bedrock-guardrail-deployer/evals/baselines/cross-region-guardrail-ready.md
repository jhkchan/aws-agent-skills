# Baseline (no-skill) response: cross-region-guardrail-ready

This file captures what a generic assistant produces WITHOUT the
bedrock-guardrail-deployer skill loaded — the contrast that proves
the skill correctly handles multi-region guardrail deployment and
verifies per-region application targets.

---

Create the guardrail in us-east-1:

```bash
aws bedrock create-guardrail \
  --name global-app-guardrail \
  --content-policy-config '{"filtersConfig":[...]}' \
  --region us-east-1
```

Then apply it to your Agents in each region. Bedrock Guardrails work
across regions automatically.
