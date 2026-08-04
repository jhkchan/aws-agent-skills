---
description: Enter the full CloudOps audit pipeline (Assess -> Audit -> Prioritize -> Remediate).
nl_triggers:
  - "run the full cloudops pipeline"
  - "full security audit"
  - "audit my whole account"
  - "comprehensive aws review"
  - "assess audit prioritize remediate"
  - "end to end security check"
  - "full compliance audit"
routes_to: aws-orchestrator
---

# /aws:pipeline

Activate the `aws-orchestrator` skill and enter the 4-phase CloudOps pipeline.
The orchestrator will:

1. Read or create the assessment state (`cloudops_state.md`) — account context,
   resources under review, findings so far, skill routing history.
2. Diagnose where the assessment currently sits across the four phases.
3. Route to the right specialist skill(s) for that phase — never duplicating
   specialist content, always handing off.
4. Emit a phase indicator on every substantive response, e.g.
   `[Phase: Audit | Resources: 12 S3 buckets | Skills routed: s3-public-access-auditor]`.

Phases: **Assess -> Audit -> Prioritize -> Remediate** — each maps to one or
more specialist skills. The orchestrator is the router, not the content owner.

This is the same behavior as natural-language entry ("check my AWS security",
"audit my whole account"). Use the slash command when you want to be explicit,
or to start a fresh pipeline session.
