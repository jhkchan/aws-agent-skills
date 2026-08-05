# Baseline (no-skill) response: content-filters-all-none

This file captures what a generic assistant produces WITHOUT the
bedrock-guardrail-coverage-auditor skill loaded.

---

I see you have a guardrail that's READY and referenced by all your
resources, which is good. However, all the content filter categories
(SEXUAL, VIOLENCE, HATE, INSULT) are set to NONE for both input and output
strength.

This means the guardrail is technically active but isn't actually filtering
any content. You should increase the filter strengths to at least MEDIUM or
HIGH depending on your use case. The grounding policy looks fine at 0.55.

Basically your guardrail is doing nothing right now even though it's
deployed. You need to configure the actual filter levels.
