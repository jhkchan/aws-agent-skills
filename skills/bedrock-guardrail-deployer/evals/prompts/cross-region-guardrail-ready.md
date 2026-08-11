# Eval prompt: cross-region-guardrail-ready

Design a deployment plan for a cross-region Amazon Bedrock Guardrail.
Emit the standard VERDICT block (GUARDRAIL_SPEC, VERDICT, CHECKLIST,
VERIFICATION_COMMANDS).

Requirements:

- Guardrail name: global-app-guardrail (one per region)
- Regions: us-east-1, eu-west-1, ap-southeast-2
- Content filters: sexual=HIGH, violence=HIGH, hate=HIGH,
  insults=MEDIUM
- Denied topics: 2 topics (Illegal_Activity, Self_Harm)
- PII filters: BLOCK for EMAIL, PHONE, SSN,
  CREDIT_DEBIT_CARD_NUMBER
- Applied to per-region Bedrock Agents: agt-us, agt-eu, agt-ap
- KMS: per-region customer-managed keys
- Account: 111111111111

Additional context: the application serves users globally with
per-region Bedrock Agents. Each region needs an identical guardrail
to ensure consistent safety filtering. The team has created
guardrails in all three regions with identical configurations and
applied each to its respective regional Agent.
