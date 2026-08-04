---
description: Quick one-line phase + skill-routing summary for the current assessment.
nl_triggers:
  - "what phase am i in"
  - "assessment status"
  - "where are we in the audit"
  - "what's been checked so far"
  - "cloudops status"
  - "pipeline status"
routes_to: aws-orchestrator (status mode)
---

# /aws:status

One-line summary in the form:

```
[Phase: <Assess|Audit|Prioritize|Remediate> | Resources: <count by service> | Findings: <CRITICAL/HIGH/MEDIUM/LOW counts> | Last skill routed: <name> | Next recommended action: <...>]
```

Reads the assessment state directly from `cloudops_state.md`. No specialist
calls. Fast — used between substantive operations to reorient.
