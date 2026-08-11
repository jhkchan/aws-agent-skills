# Baseline (no-skill) response: pii-audit-instead-of-block-missing

This file captures what a generic assistant produces WITHOUT the
bedrock-guardrail-deployer skill loaded — the contrast that proves
the skill catches the AUDIT-vs-BLOCK confusion that a baseline would
pass through without flagging.

---

To meet GDPR requirements, configure your PII filters with AUDIT:

```bash
aws bedrock create-guardrail \
  --name gdpr-compliance-guardrail \
  --sensitive-information-policy-config '{
    "piiEntitiesConfig": [
      {"type": "EMAIL", "action": "AUDIT"},
      {"type": "PHONE", "action": "AUDIT"},
      {"type": "SSN", "action": "AUDIT"},
      {"type": "NAME", "action": "AUDIT"},
      {"type": "ADDRESS", "action": "AUDIT"}
    ]
  }' \
  --region eu-west-1
```

This will log all PII detections for compliance auditing.
