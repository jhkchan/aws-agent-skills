---
description: Audit AWS Trusted Advisor check results for security, fault-tolerance, cost-optimization, performance, and service-limits findings — including support-tier gating, staleness, excluded resources, and not_available statuses.
nl_triggers:
  - "audit Trusted Advisor"
  - "review TA checks"
  - "Trusted Advisor findings"
  - "TA check results"
  - "support tier coverage"
  - "stale Trusted Advisor"
  - "excluded TA resources"
  - "not_available TA check"
  - "service limit exceeded"
  - "cost optimization findings"
  - "fault tolerance findings"
  - "security check error"
  - "Basic support limited checks"
  - "Business support Trusted Advisor"
  - "compliance review TA"
  - "operational review Trusted Advisor"
routes_to: trustedadvisor-check-auditor
---

# /aws:audit-trustedadvisor-checks

Activate the `trustedadvisor-check-auditor` skill and audit one or more
Trusted Advisor check results for operational and security risk.

## What it does

Reads a Trusted Advisor check result (check name, category, status,
timestamp, flagged resources) plus optional account metadata (support
tier, total checks available, exclusions) and applies the ordered
classification logic:

1. Support tier gate — Basic/Developer (7 of ~115 checks) is CONFIG_GAP.
2. Check freshness — timestamp > 24 hours is a stale-result CONFIG_GAP.
3. Check status by category — Security/Fault Tolerance error is
   CRITICAL_CHECK; Cost/Performance error is WARNING_CHECK;
   not_available is CONFIG_GAP.
4. Service limits graduated severity — >= 100% is CRITICAL_CHECK,
   80-99% is WARNING_CHECK, < 80% is OK.
5. Excluded resources — suppressed findings on security checks escalate
   one level.
6. Aggregation — worst finding wins (CRITICAL > WARNING > CONFIG_GAP > OK).

Emits a deterministic VERDICT per check:

```text
CHECK: <check-name or check-id>
VERDICT: CRITICAL_CHECK | WARNING_CHECK | CONFIG_GAP | OK
REASON: <1-2 sentences citing the check category, status, and step>
FINDINGS:
  - [CRITICAL_CHECK] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Trusted Advisor check result and ask any of:

- "audit these Trusted Advisor results"
- "review TA findings before compliance review"
- "is my TA coverage complete?"
- "why do I only see 7 checks?"
- "is this check result stale?"
- "what does not_available mean for this check?"

A check name or ID + any audit verb ("audit this TA check", "review TA
findings") also routes here via the orchestrator.

## Inputs

- A Trusted Advisor check result: check name, category (Security, Fault
  Tolerance, Cost Optimization, Performance, Service Limits), status
  (ok, warning, error, not_available), timestamp, flagged resources.
- Account metadata: support tier (Basic, Developer, Business, Enterprise
  On-Ramp, Enterprise), total checks available, excluded resources.
- For multi-check audits: provide multiple check results; the skill
  emits a VERDICT block per check.

## Outputs

- One VERDICT block per check (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: restrict security groups, request quota
  increases, stop idle instances, refresh stale checks, enable
  prerequisites for not_available checks, supplement with free-tier
  alternatives for Basic support accounts.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Trusted Advisor governance).
- `/aws:audit-securityhub-control-compliance` for Security Hub control
  findings that overlap with TA security checks.
- `/aws:audit-cost-optimization-hub` for Cost Optimization Hub
  recommendations that complement TA cost checks.
