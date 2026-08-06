# Eval prompt: partial-model-coverage

Audit the following Bedrock Guardrail configuration and resource coverage
manifest. Emit the standard VERDICT block (GUARDRAIL, VERDICT, RISK, REASON,
FINDINGS, REMEDIATION).

Guardrail configuration:
  name: prod-content-guard
  guardrailId: grn-coverage002
  status: READY
  version: 1

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

  blockedInputMessaging: "Your request was blocked by the content policy."
  blockedOutputsMessaging: "The response was blocked by the content policy."

Bedrock resource coverage manifest:
  1. Agent: customer-support-agent (agentId: agent-aaa)
     guardrailConfiguration: {guardrailIdentifier: "grn-coverage002", guardrailVersion: "1"}
  2. Agent: content-writer-agent (agentId: agent-bbb)
     guardrailConfiguration: NONE
  3. Knowledge Base: product-docs-kb (kbId: kb-ccc)
     guardrailConfiguration: {guardrailIdentifier: "grn-coverage002", guardrailVersion: "1"}
  4. Application: chat-app (calls converse with anthropic.claude-3-5-sonnet)
     guardrailIdentifier in converse: NONE
  5. Application: summarizer-app (calls converse with amazon.nova-pro)
     guardrailIdentifier in converse: NONE
