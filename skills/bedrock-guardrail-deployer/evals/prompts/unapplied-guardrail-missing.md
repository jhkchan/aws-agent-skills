# Eval prompt: unapplied-guardrail-missing

Design a deployment plan for an Amazon Bedrock Guardrail. Emit the
standard VERDICT block (GUARDRAIL_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- Guardrail name: prod-safety-guardrail
- Region: us-east-1
- Content filters: sexual=HIGH, violence=HIGH, hate=HIGH,
  insults=HIGH
- Denied topics: 3 topics defined
- Word filters: managed PROFANITY + custom words
- PII filters: BLOCK for SSN, EMAIL, PHONE
- NOT applied to any model or Agent yet
- Application: "we'll apply it later after testing"

Additional context: the team has created a comprehensive guardrail
with all filter categories configured. However, they have NOT applied
the guardrail to any model invocation or Bedrock Agent. They plan to
"apply it later after testing." The model invocations are running in
production without any guardrail protection.
