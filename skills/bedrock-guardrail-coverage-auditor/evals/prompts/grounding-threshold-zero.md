# Eval prompt: grounding-threshold-zero

Audit the following Bedrock Guardrail configuration for contextual grounding
posture. Emit the standard VERDICT block (GUARDRAIL, VERDICT, RISK, REASON,
FINDINGS, REMEDIATION).

Guardrail configuration:
  name: weak-grounding-guard
  guardrailId: grn-grounding004
  status: READY
  version: 1

  contentPolicy:
    filtersConfig:
      - type: SEXUAL, inputStrength: HIGH, outputStrength: HIGH
      - type: VIOLENCE, inputStrength: HIGH, outputStrength: HIGH
      - type: HATE, inputStrength: HIGH, outputStrength: HIGH
      - type: INSULT, inputStrength: HIGH, outputStrength: HIGH

  contextualGroundingPolicy:
    filtersConfig:
      - type: GROUNDING, threshold: 0.0
      - type: RELEVANCE, threshold: 0.0

  blockedInputMessaging: "Your request was blocked."
  blockedOutputsMessaging: "The response was blocked."

Bedrock resource coverage: All 3 agents and 2 knowledge bases reference
this guardrail (version 1).
