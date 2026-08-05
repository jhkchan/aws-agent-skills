# Eval prompt: no-guardrail-models-unprotected

Audit the following Bedrock deployment for guardrail coverage. Emit the
standard VERDICT block (GUARDRAIL, VERDICT, RISK, REASON, FINDINGS,
REMEDIATION).

Bedrock deployment summary for account 111111111111 (us-east-1):

Models available:
  - anthropic.claude-3-5-sonnet-20241022-v2:0
  - amazon.nova-pro-v1:0
  - amazon.titan-text-express-v1:0

Agents:
  - customer-support-agent (agentId: agent-aaa, status: PREPARED)
    guardrailConfiguration: NONE
  - content-writer-agent (agentId: agent-bbb, status: PREPARED)
    guardrailConfiguration: NONE

Knowledge Bases:
  - product-docs-kb (kbId: kb-ccc)
    guardrailConfiguration: NONE

Guardrails in account: 0

Application callers: 3 applications invoke models via converse without
guardrailIdentifier.
