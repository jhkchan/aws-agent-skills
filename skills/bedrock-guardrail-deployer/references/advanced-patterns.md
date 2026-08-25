# Bedrock Guardrail Deployer — expert-heuristic deep dives and recent AWS features

Content moved verbatim from SKILL.md (progressive disclosure). Load on demand.

---

## Expert heuristic: the unapplied-guardrail trap (moved verbatim from SKILL.md)

The most dangerous Guardrail misconfiguration: a comprehensive
guardrail that is never applied.

```text
Operator thinks:              What actually happens:
"I created a guardrail   →    The guardrail exists as an independent
 with content filters,         resource. It is NOT automatically
 PII filters, and denied       associated with any model invocation
 topics — my app is safe"      or Agent. The model responds with no
                               filtering. The guardrail passes every
                               audit because it IS correctly
                               configured — it is just not wired.
```

The tell-tale signal: CloudWatch shows zero `Bedrock/Guardrail`
invocation metrics despite the guardrail being "active" in the
console. Remedy: explicitly associate the guardrail with every model
invocation via `guardrailIdentifier` and `guardrailVersion`, or
configure it on the Bedrock Agent. Verify with a test prompt that
SHOULD be blocked.

---

## Expert heuristic: AUDIT-vs-BLOCK confusion for PII filters (moved verbatim from SKILL.md)

The sensitive information filter has three actions:

```text
ALLOW  → no action (PII passes through, no log)
AUDIT  → log the detection but ALLOW the response through
BLOCK  → prevent the response; PII never reaches the user
```

Operators who set AUDIT thinking "block and log" are wrong: AUDIT
means LOG ONLY. The PII detection appears in CloudWatch, but the
response containing the PII is delivered to the user. For compliance,
use BLOCK. Use AUDIT only for monitoring with a documented plan to
switch to BLOCK.

---

## Expert heuristic: severity levels and filter sensitivity (moved verbatim from SKILL.md)

Each content filter category uses a severity threshold:

```text
NONE   → filter is OFF (no content blocked for this category)
LOW    → blocks only the most severe violations
MEDIUM → blocks moderate and severe violations
HIGH   → blocks all detected violations (most aggressive)
```

The severity is a threshold: setting violence to MEDIUM blocks content
classified as MEDIUM or HIGH. NONE disables the filter entirely. The
default for a new guardrail is NONE for all categories — operators who
accept defaults have no content filtering.

---

## Recent AWS features (moved verbatim from SKILL.md)

- **Contextual grounding checks**: the GROUNDING and RESPONSE_RELEVANCE
  filter types verify that the model's response is grounded in provided
  source content and relevant to the user's query. Configured via
  `contextual-grounding-policy-config` with a threshold (0.0-1.0).
  Requires the invocation to include source content (e.g., from a
  Knowledge Base or RAG pipeline).

- **Guardrails with Agents**: Bedrock Agents support guardrail
  association via `update-agent --guardrail-configuration`. The
  guardrail filters both the user's input and the Agent's responses,
  including tool-use and Knowledge Base retrieval augmented responses.

- **Guardrail evaluation**: the `apply-guardrail` API tests a guardrail
  in isolation without invoking a model. Send a test prompt that SHOULD
  be blocked and verify the BLOCK action. Use this to validate filter
  configuration before applying to production traffic.

- **Prompt attack filter**: the PROMPT_ATTACK type detects and blocks
  prompt injection attempts. `inputStrength` sets detection
  sensitivity; `outputStrength` is typically NONE since prompt attacks
  target the input.

- **Misconduct filter**: the MISCONDUCT type detects content involving
  misconduct or inappropriate behavior, extending the original four
  categories (hate, insults, sexual, violence).

- **Cross-region guardrails**: guardrails remain regional resources.
  With cross-region inference, a model invocation from one region may
  route to another — ensure the guardrail exists in every region where
  the model may be invoked, including inference target regions.

- **Guardrail versioning**: each update creates a new version. The
  `guardrailVersion` parameter pins the active version on model
  invocations and Agents. Updating the guardrail does NOT auto-update
  applied versions — operators must explicitly update each target.

