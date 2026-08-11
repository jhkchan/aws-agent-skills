# Eval prompt: full-guardrail-applied-ready

Design a deployment plan for an Amazon Bedrock Guardrail. Emit the
standard VERDICT block (GUARDRAIL_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- Guardrail name: customer-app-guardrail
- Region: us-east-1
- KMS key: arn:aws:kms:us-east-1:111111111111:key/abc-123
- Content filters: sexual=HIGH, violence=MEDIUM, hate=MEDIUM,
  insults=MEDIUM (input+output), misconduct=MEDIUM
- Denied topics: Financial_Advice, Medical_Diagnosis (with
  definitions and examples)
- Word filters: managed PROFANITY + 3 custom words
- PII filters: BLOCK for EMAIL, PHONE, SSN,
  CREDIT_DEBIT_CARD_NUMBER
- Contextual grounding: GROUNDING=0.75, RESPONSE_RELEVANCE=0.75
- Applied to Agent: agentId=agt-xyz, version=DRAFT
- Account: 111111111111

Additional context: the team is deploying a customer-facing LLM
application via a Bedrock Agent. The guardrail must filter harmful
content, block PII from responses, deny financial and medical advice
topics, and verify response grounding. All filter categories are
configured and the guardrail is explicitly applied to the Agent.
