# Eval prompt: draft-guardrail-not-ready

Audit the following Bedrock Guardrail configuration for enforcement posture.
Emit the standard VERDICT block (GUARDRAIL, VERDICT, RISK, REASON, FINDINGS,
REMEDIATION).

Guardrail configuration:
  name: prod-content-guard
  guardrailId: grn-draft001
  guardrailArn: arn:aws:bedrock:us-east-1:111111111111:guardrail/grn-draft001
  status: DRAFT
  version: DRAFT

  contentPolicy:
    filtersConfig:
      - type: SEXUAL, inputStrength: HIGH, outputStrength: HIGH
      - type: VIOLENCE, inputStrength: HIGH, outputStrength: HIGH
      - type: HATE, inputStrength: HIGH, outputStrength: HIGH
      - type: INSULT, inputStrength: HIGH, outputStrength: HIGH

  contextualGroundingPolicy:
    filtersConfig:
      - type: GROUNDING, threshold: 0.55
      - type: RELEVANCE, threshold: 0.55

  blockedInputMessaging: "Your request was blocked."
  blockedOutputsMessaging: "The response was blocked."
