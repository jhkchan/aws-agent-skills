---
description: Audit AWS Cost Explorer anomaly-detection subscriptions, RI/SP coverage gaps, idle-resource detection readiness, and report-subscription cadence.
nl_triggers:
  - "audit Cost Anomaly Detection"
  - "check anomaly subscription"
  - "is CAD wired correctly"
  - "RI coverage gap"
  - "Savings Plan coverage"
  - "anomaly threshold too high"
  - "idle resource detection"
  - "IMMEDIATE vs DAILY monitor"
  - "cost spike alerting"
  - "commitment gap"
  - "on-demand leak"
  - "Cost Explorer audit"
  - "anomaly subscription frequency"
  - "cost anomaly threshold"
  - "FinOps spend visibility"
routes_to: ce-cost-anomaly-auditor
---

# /aws:audit-ce-cost-anomaly

Activate the `ce-cost-anomaly-auditor` skill and audit one or more AWS
Cost Explorer configurations for FinOps spend-visibility posture.

## What it does

Reads a CE/CAD inventory (anomaly monitors, anomaly subscriptions, RI/SP
coverage percentages, CUR config, account spend profile) and applies the
ordered classification logic:

1. CE enablement gate — short-circuit to ERROR if CE is not enabled.
2. CAD subscription gate — zero monitors or zero subscriptions is
   NO_ANOMALY_SUB (total cost-spike blind spot).
3. RI/SP coverage — eligible compute spend >$1k/mo with RI < 40% AND
   SP < 40% is LOW_RI_COVERAGE (on-demand leak).
4. Configuration quality — IMMEDIATE monitor + WEEKLY subscription,
   $100 default threshold on low-spend account, DAILY-only monitors,
   no CUR resource IDs, narrow monitor scope are all CONFIG_GAP.
5. Aggregation — worst finding wins (NO_ANOMALY_SUB > LOW_RI_COVERAGE >
   CONFIG_GAP > OK).

Emits a deterministic VERDICT per account:

```text
ACCOUNT: <account-id>
VERDICT: NO_ANOMALY_SUB | LOW_RI_COVERAGE | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and worst finding>
FINDINGS:
  - [HIGH] <finding description (Step N)>
  - [MEDIUM] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste a CE/CAD inventory and ask any of:

- "audit my Cost Anomaly Detection"
- "is CAD wired correctly?"
- "check RI coverage gap"
- "is the anomaly threshold calibrated?"
- "can we detect idle resources via Cost Explorer?"
- "why did the cost spike alert arrive late?"

A bare account-id or CE inventory + any audit verb ("audit CE", "check
anomaly detection") also routes here via the orchestrator.

## Inputs

- CE/CAD inventory: anomaly monitors (MonitorType, MonitorArn),
  anomaly subscriptions (Threshold, Frequency, subscribers), RI/SP
  coverage percentages (7-day average over eligible compute spend),
  CUR config (IncludeResourceIDs, Athena integration), account spend
  profile (monthly total, workload type).
- For Organizations: provide per-member coverage breakdown
  (LINKED_ACCOUNT group-by) to expose the long tail.

## Outputs

- One VERDICT block per account (multiple findings aggregate to the
  worst verdict).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: create monitors/subscriptions, update
  frequency/threshold, run commitment analysis, configure CUR v2.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for FinOps cost visibility).
- `/aws:audit-budgets` for budget threshold/notification auditing
  (complementary — budgets are reactive guardrails; CAD is predictive ML).
- `/aws:audit-billing-account` for the account-level CAD-enablement gate
  (runs first; this skill assumes CE is enabled).
- `/aws:audit-cur-cost-usage-report` for CUR v2 configuration (required
  for resource-level idle detection via CE).
