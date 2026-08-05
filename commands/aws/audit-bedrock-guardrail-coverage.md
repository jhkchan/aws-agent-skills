---
description: Audit a Bedrock Guardrail configuration and model coverage for content-filter strength, contextual grounding thresholds, DRAFT-vs-READY enforcement status, denied topics, word filters, and per-application bypass risk.
nl_triggers:
  - "audit this Bedrock guardrail"
  - "check Bedrock guardrail coverage"
  - "are my models protected by guardrails"
  - "content filter too weak"
  - "grounding threshold too low"
  - "is this guardrail in DRAFT"
  - "which models have guardrails"
  - "Bedrock agent unguarded"
  - "knowledge base guardrail missing"
  - "LLM safety audit"
  - "generative AI guardrail check"
  - "Bedrock content policy"
  - "guardrail not enforced"
  - "model coverage gap"
  - "hardening Bedrock guardrails"
routes_to: bedrock-guardrail-coverage-auditor
---

# /aws:audit-bedrock-guardrail-coverage

Activate the `bedrock-guardrail-coverage-auditor` skill and audit one or
more Bedrock Guardrail configurations and model/resource coverage manifests
for generative AI safety posture.

## What it does

Reads a Bedrock Guardrail configuration (contentPolicy,
contextualGroundingPolicy, topicPolicy, wordPolicy, status, version)
optionally paired with a model/resource coverage manifest, and applies the
ordered classification logic:

1. Guardrail existence and status — DRAFT status provides zero enforcement
   (NO_GUARDRAIL).
2. Model/resource coverage — verify every agent, KB, and application caller
   references the guardrail ID (INCOMPLETE_COVERAGE).
3. Content filter strength — check all four core categories (HATE, INSULT,
   SEXUAL, VIOLENCE) for outputStrength NONE (WEAK_FILTER).
4. Contextual grounding — threshold below 0.2 is effectively disabled
   (WEAK_FILTER).
5. Configuration gaps — empty blocked messaging, DRAFT version in
   production, missing PII policy (CONFIG_GAP).
6. Aggregation — worst finding wins
   (NO_GUARDRAIL > INCOMPLETE_COVERAGE > WEAK_FILTER > CONFIG_GAP > OK).

Emits a deterministic VERDICT per guardrail or deployment:

```text
GUARDRAIL: <guardrail-id or name>
VERDICT: NO_GUARDRAIL | INCOMPLETE_COVERAGE | WEAK_FILTER | CONFIG_GAP | OK
RISK: CRITICAL | HIGH | MEDIUM | LOW
REASON: <1-2 sentences citing the worst finding and step>
FINDINGS:
  - [CRITICAL] <finding description (Step N)>
  - [HIGH] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Bedrock Guardrail configuration and resource coverage manifest and
ask any of:

- "audit this Bedrock guardrail"
- "are my Bedrock models protected?"
- "check guardrail coverage"
- "is this guardrail in DRAFT?"
- "content filter too weak"
- "grounding threshold too low"
- "which resources have guardrails?"

A bare guardrail ID/ARN or config JSON + any audit verb also routes here
via the orchestrator.

## Inputs

- A Bedrock Guardrail configuration (JSON/YAML): status, version,
  contentPolicy.filtersConfig (type, inputStrength, outputStrength),
  contextualGroundingPolicy.filtersConfig (type, threshold),
  topicPolicy, wordPolicy, blockedInputMessaging, blockedOutputsMessaging.
- A resource coverage manifest: list of agents, KBs, and application callers
  with their guardrailConfiguration (or NONE if unguarded).
- For multi-region deployments: provide configs for each region.

## Outputs

- One VERDICT block per guardrail (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: promote DRAFT to READY, add guardrail IDs to
  unguarded resources, increase filter strengths, raise grounding
  thresholds, pin numbered versions.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Bedrock generative AI safety).
- `/aws:audit-iam-least-privilege` for IAM policy analysis of roles that
  may have Bedrock invocation permissions in their identity-based policies.
