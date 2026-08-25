# Bedrock Guardrail Deployer — secondary worked examples

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

### Perfect example output — PREREQUISITES_MISSING (moved verbatim from SKILL.md)

```text
GUARDRAIL_SPEC: customer-app-guardrail
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Model access: confirmed in region us-east-1
  [✓] Guardrail created: id=abc123def, version=1, KMS=arn:aws:kms:us-east-1:111111111111:key/xyz-789
  [✓] Content filters: sexual=HIGH, violence=MEDIUM, hate=MEDIUM, insults=MEDIUM
  [✓] Denied topics: 2 topics defined
  [✓] Word filters: managed=PROFANITY, custom=3 words
  [✗] PII filters: all entities set to AUDIT — compliance requires BLOCK for EMAIL, PHONE, SSN; switch action from AUDIT to BLOCK
  [N/A] Contextual grounding: not applicable
  [✗] Guardrail applied: NOT applied to any model invocation or Agent — guardrail is inert; associate via guardrailIdentifier parameter
  [✗] Cross-region: guardrail only in us-east-1; application also invokes models in eu-west-1 — create identical guardrail in eu-west-1
VERIFICATION_COMMANDS:
  aws bedrock get-guardrail --guardrail-identifier abc123def --guardrail-version 1 --region us-east-1
  aws bedrock list-guards --region eu-west-1 --output table
```

