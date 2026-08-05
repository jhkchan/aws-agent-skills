# Baseline (no-skill) response: grounding-threshold-zero

This file captures what a generic assistant produces WITHOUT the
bedrock-guardrail-coverage-auditor skill loaded.

---

Your guardrail has strong content filters (all HIGH) and all resources are
covered, which is great. The contextual grounding policy is configured but
the thresholds are set to 0.0 for both GROUNDING and RELEVANCE.

A threshold of 0.0 means the grounding check will essentially never trigger.
You should increase it to something like 0.5 or 0.6 to get meaningful
hallucination detection. The lower the threshold, the more responses pass
through without being checked for grounding.

Everything else looks good — just raise those grounding thresholds.
