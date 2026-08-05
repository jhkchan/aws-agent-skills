# Eval prompt: content-filters-all-none

Audit the following Bedrock Guardrail configuration for content-filter
strength. Emit the standard VERDICT block (GUARDRAIL, VERDICT, RISK, REASON,
FINDINGS, REMEDIATION).

Guardrail configuration:
  name: baseline-guard
  guardrailId: grn-weak003
  status: READY
  version: 1

  contentPolicy:
    filtersConfig:
      - type: SEXUAL, inputStrength: NONE, outputStrength: NONE
      - type: VIOLENCE, inputStrength: NONE, outputStrength: NONE
      - type: HATE, inputStrength: NONE, outputStrength: NONE
      - type: INSULT, inputStrength: NONE, outputStrength: NONE

  contextualGroundingPolicy:
    filtersConfig:
      - type: GROUNDING, threshold: 0.55
      - type: RELEVANCE, threshold: 0.55

  blockedInputMessaging: "Blocked."
  blockedOutputsMessaging: "Blocked."

Bedrock resource coverage: All 3 agents and 2 knowledge bases reference
this guardrail (version 1).
