---
description: Audit AWS Cost Optimization Hub configuration for recommendation enablement, member-account coverage, effort-level distribution, and stale high-value unactioned recommendations.
nl_triggers:
  - "audit cost optimization hub"
  - "are cost optimization recommendations enabled"
  - "check member account enrollment cost optimization"
  - "effort level distribution recommendations"
  - "stale high-value recommendations"
  - "unactioned cost optimization recommendations"
  - "savings estimation mode check"
  - "FinOps audit cost optimization hub"
  - "cost optimization hub disabled"
  - "BEFORE_DISCOUNTS savings mode"
  - "AFTER_DISCOUNTS savings mode"
  - "cost optimization recommendations stale"
routes_to: cost-optimization-hub-recommendations-auditor
---

# /aws:audit-cost-optimization-hub

Activate the `cost-optimization-hub-recommendations-auditor` skill and audit a
Cost Optimization Hub configuration for optimization posture.

## What it does

Reads a Cost Optimization Hub configuration snapshot (preferences + organization
context + recommendation list) and applies the ordered classification logic:

1. Recommendations enablement — not enrolled or disabled is DISABLED
   (highest priority, short-circuit).
2. Member account coverage — enrolled but zero member accounts visible in
   an Organization management/delegated-admin context is NO_MEMBER_ACCOUNTS.
3. Effort level distribution — all remaining recommendations are High effort
   (no Low/Medium quick wins) is HIGH_EFFORT.
4. Configuration gaps — stale high-value recs (>= $500/mo, > 90 days) or
   BEFORE_DISCOUNTS savings estimation mode is CONFIG_GAP.
5. All dimensions pass — OK.

Emits a deterministic VERDICT per account:

```text
ACCOUNT: <account-id>
VERDICT: DISABLED | NO_MEMBER_ACCOUNTS | HIGH_EFFORT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step>
FINDINGS:
  - [CONFIG_GAP] <finding description (Step Na)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a Cost Optimization Hub configuration snapshot and ask any of:

- "audit cost optimization hub"
- "are cost optimization recommendations enabled?"
- "check member account enrollment"
- "are there stale high-value recommendations?"
- "is my savings estimation mode correct?"
- "FinOps audit"

## Inputs

- A COH configuration snapshot: enrolled status, preferences
  (savingsEstimationMode), organization context, member account counts,
  recommendation list (effortLevel, estimatedSavings, recommendationAgeInDays).
- For live-account audit: profile and region, and the skill will call
  `aws ce get-preferences` and
  `aws ce list-cost-optimization-recommendations`.

## Outputs

- One VERDICT block per account.
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: enroll COH, enable org-level visibility, action stale
  recs, switch savings estimation mode, with exact CLI commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for FinOps cost-optimization governance).
- `/aws:audit-compute-optimizer-findings` for Compute Optimizer right-sizing
  recommendations (a primary source of Cost Optimization Hub Low-effort items).
