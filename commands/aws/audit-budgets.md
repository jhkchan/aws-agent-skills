---
description: Audit AWS Budgets for cost-overrun blind spots — zero budgets, decorative budgets (no notifications), SNS topic policies that silently block delivery (missing budgets.amazonaws.com publish), single-threshold/no-forecast alerts, breached or on-track-to-breach spend, and missing zero-spend guardrails for new accounts.
nl_triggers:
  - "audit my AWS budgets"
  - "check budget alerts"
  - "is my budget wired to SNS"
  - "budget notification threshold"
  - "zero-spend budget"
  - "cost overrun alert"
  - "budget forecast exceeded"
  - "spend posture audit"
  - "budget SNS policy"
  - "decorative budget"
  - "budget not alerting"
  - "budget alerts not working"
  - "AWS Budgets audit"
  - "budget threshold gap"
  - "FORECASTED budget notification"
routes_to: budgets-auditor
---

# /aws:audit-budgets

Activate the `budgets-auditor` skill and audit one or more AWS Budgets account
configurations for cost-overrun blind spots.

## What it does

Reads an account budget inventory (budgets, notifications, subscribers, SNS
topic policies, calculated spend) and applies the ordered classification
logic:

1. Budget existence — zero budgets of any type is NO_BUDGET (total blind
   spot; default for new accounts).
2. Notification gate — budget with zero notifications or empty subscriber
   lists is NO_ALERT (decorative budget).
3. SNS topic policy — subscriber present but topic policy lacks the
   budgets.amazonaws.com publish principal means alerts silently fail to
   deliver (CONFIG_GAP).
4. Threshold coverage — single threshold or no threshold below 80% means no
   reaction time (CONFIG_GAP).
5. FORECASTED coverage — COST budget with only ACTUAL notifications has no
   predictive signal given cost-data lag (CONFIG_GAP).
6. Actual-vs-forecast breach — uncovered breach with no matching notification
   type (CONFIG_GAP).
7. Zero-spend guardrail — new/sandbox account with no low-spend guardrail
   (CONFIG_GAP).
8. Aggregation — worst per-budget verdict wins
   (NO_BUDGET > NO_ALERT > CONFIG_GAP > OK).

Emits a deterministic VERDICT per account:

```text
ACCOUNT: <account-id>
VERDICT: NO_BUDGET | NO_ALERT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and worst finding>
FINDINGS:
  - [HIGH] <budget name>: <finding description (Step N)>
  - [OK] <budget name>: <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an account budget inventory and ask any of:

- "audit my AWS budgets"
- "are my budget alerts wired correctly?"
- "is my budget SNS topic policy correct?"
- "do I have a zero-spend guardrail?"
- "why don't my budget alerts fire?"
- "check my spend posture before the billing review"

A bare account id + any cost-control verb ("audit spend", "check budgets")
also routes here via the orchestrator.

## Inputs

- An account budget inventory (JSON or YAML): list of budgets, each with
  BudgetType, TimeUnit, BudgetLimit, CostTypes, CalculatedSpend, plus the
  notifications and subscribers for each, and the SNS topic policies for any
  SNS subscriber topics.
- Account context: production/sandbox/new, consolidated-billing (Org) scope.
- For live-account audits: an account-id, queried via `aws budgets
  describe-budgets --region us-east-1`.

## Outputs

- One VERDICT block per account (multiple findings aggregate to the worst
  verdict).
- Enumerated FINDINGS list with per-finding risk and step citation.
- Specific remediation: create budgets, add notifications, fix SNS topic
  policy, add FORECASTED notification, add zero-spend guardrail.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for FinOps cost control).
- `/aws:audit-ebs-volume` for EBS-specific cost waste (unattached volumes,
  legacy types, stale snapshots) that budgets may surface but not explain.
