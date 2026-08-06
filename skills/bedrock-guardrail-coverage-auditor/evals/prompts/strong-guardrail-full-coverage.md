# Eval prompt: strong-guardrail-full-coverage

Audit the following Bedrock Guardrail configuration for production readiness.
Emit the standard VERDICT block (GUARDRAIL, VERDICT, RISK, REASON, FINDINGS,
REMEDIATION).

Guardrail configuration:
  name: prod-content-guard
  guardrailId: grn-strong005
  status: READY
  version: 3

  contentPolicy:
    filtersConfig:
      - type: SEXUAL, inputStrength: HIGH, outputStrength: HIGH
      - type: VIOLENCE, inputStrength: HIGH, outputStrength: HIGH
      - type: HATE, inputStrength: MEDIUM, outputStrength: HIGH
      - type: INSULT, inputStrength: MEDIUM, outputStrength: MEDIUM

  contextualGroundingPolicy:
    filtersConfig:
      - type: GROUNDING, threshold: 0.55
      - type: RELEVANCE, threshold: 0.55

  wordPolicy:
    managedWordListsEnabled: true

  blockedInputMessaging: "Your request was blocked by the content policy. Please rephrase."
  blockedOutputsMessaging: "The response was blocked by the content policy."

Bedrock resource coverage: All 3 agents, 2 knowledge bases, and all
application callers reference this guardrail (version 3).
