# Eval prompt: pii-audit-instead-of-block-missing

Design a deployment plan for an Amazon Bedrock Guardrail. Emit the
standard VERDICT block (GUARDRAIL_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- Guardrail name: gdpr-compliance-guardrail
- Region: eu-west-1
- Content filters: all HIGH
- PII filters: ALL entities (EMAIL, PHONE, SSN, NAME, ADDRESS,
  CREDIT_DEBIT_CARD_NUMBER) set to AUDIT
- Compliance requirement: GDPR — PII must NOT appear in model
  responses
- Applied to model: anthropic.claude-3-5-sonnet-20241022-v2:0

Additional context: the compliance team requires that PII never
appears in model responses under GDPR. The operator configured all
PII entities with the AUDIT action, believing this blocks and logs
the PII. In reality, AUDIT only logs — the response containing the
PII is still delivered to the user.
