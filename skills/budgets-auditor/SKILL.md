---
name: budgets-auditor
description: >-
  Audits AWS Budgets for cost-overrun blind spots: accounts with zero budgets,
  budgets configured without notifications (decorative budgets), single-
  threshold alerts that leave no time to react, ACTUAL-only alerts with no
  FORECASTED warning, SNS topic policies that silently block delivery
  (missing budgets.amazonaws.com publish principal), breached or on-track-to-
  breach actual-vs-forecast spend, and missing zero-spend guardrails for new
  or sandbox accounts. Emits a deterministic verdict
  (NO_BUDGET | NO_ALERT | CONFIG_GAP | OK) per account with enumerated
  findings and specific CLI remediation. Use when reviewing cost budgets,
  checking budget alert thresholds, validating SNS notification wiring,
  auditing spend posture, or hardening cost controls before a billing review.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). No AWS CLI required for offline budget-document classification.
  Live-account audits use aws budgets describe-budget, aws budgets
  describe-budgets, aws budgets describe-notifications-for-budget, aws budgets
  describe-subscribers-for-notification, and aws sns get-topic-attributes
  (AWS CLI v2, SSO or key-based credentials).
keywords:
  - AWS Budgets
  - cost budget
  - budget alert
  - notification threshold
  - FORECASTED
  - ACTUAL
  - SNS topic policy
  - budgets.amazonaws.com
  - zero-spend budget
  - cost overrun
  - FinOps
  - billing alarm
  - cost control
  - spend posture
  - budget action
  - RI coverage
  - Consolidated Billing
  - budget audit
  - threshold gap
tags: [budgets, finops, cost-control, alerting, sns, spend, audit]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: FinOps
  verdict_shape: "NO_BUDGET | NO_ALERT | CONFIG_GAP | OK"
  when_to_use: >-
    Reviewing cost budgets before a billing review or production cutover,
    checking that budget alerts are wired to a real SNS topic, validating
    threshold coverage (early-warning vs over-budget), auditing actual-vs-
    forecast breach posture, or hardening spend controls for a new or sandbox
    account.
  activation_triggers:
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
  invocation_schema: >-
    Input: either (a) an account budget inventory (list of budgets, each with
    notifications, subscribers, SNS topic policies, and calculated spend), OR
    (b) an account-id for live-account audit. Output: deterministic
    BUDGET/VERDICT/REASON/FINDINGS/REMEDIATION block per budget plus an
    account-level aggregate verdict, where VERDICT is one of NO_BUDGET,
    NO_ALERT, CONFIG_GAP, OK.
---

# Budgets Auditor

## Mindset

**One-line takeaway:** a budget without a working notification is decorative —
it tracks spend nobody watches. The verdict escalates through four blind-spot
tiers, and three AWS Budgets behaviours are easy to misjudge: **cost-data lag**
(actuals trail real spend by hours), **silent SNS delivery failure** (a missing
topic-policy statement produces zero console error), and **ACTUAL-vs-FORECASTED
semantics** (an ACTUAL alert at 100% fires after the money is spent).

AWS Budgets is the first line of cost control, but the configuration is where
alerting silently fails. Three failure modes dominate:

- **No budgets at all** — the account has zero budgets. Spend runs completely
  unbounded with no visibility. This is the default state for new accounts and
  the most dangerous posture for a compromised credential or a runaway
  resource.
- **Decorative budget** — a budget exists but has zero notifications (or
  notifications with no subscribers). It tracks spend in the console but never
  alerts anyone. The operator believes they have cost control; they have a
  dashboard.
- **Wired-wrong alert** — notifications exist but the SNS topic policy omits
  the `budgets.amazonaws.com` publish principal, OR there is a single 100%
  ACTUAL threshold with no early warning and no forecast. The alert either
  silently never delivers, or arrives too late to act on.

## Quick reference — verdict thresholds

| Condition | Verdict | Step |
|---|---|---|
| Account has zero budgets | **NO_BUDGET** | 1 |
| Budget has zero notifications, or all notifications have zero subscribers | **NO_ALERT** | 2 |
| SNS subscriber present but topic policy lacks `budgets.amazonaws.com` publish | **CONFIG_GAP** | 3 |
| Only one threshold, or no threshold below 80% | **CONFIG_GAP** | 4 |
| COST budget with ACTUAL notifications but zero FORECASTED notifications | **CONFIG_GAP** | 5 |
| `ForecastedSpend > BudgetLimit` with no FORECASTED notification at the breached ratio | **CONFIG_GAP** | 6 |
| `ActualSpend > BudgetLimit` (breached) with no ACTUAL notification fired | **CONFIG_GAP** | 6 |
| New/sandbox account (flagged) with no zero-spend or low-spend budget | **CONFIG_GAP** | 7 |
| All budgets: multi-threshold, ACTUAL+FORECASTED, SNS wired, not breached | **OK** | 8 |

Steps apply in order — the first step that triggers sets the per-budget
verdict. The account-level verdict is the **worst** per-budget verdict, where
NO_BUDGET > NO_ALERT > CONFIG_GAP > OK. See the ordered classification below
for edge cases and additive findings.

## Pre-flight: input and account-metadata gate

Before classification, validate the input structure and identify metadata that
short-circuits the audit.

**Live-account sweep note (pagination):** `aws budgets describe-budgets` is
paginated via `--next-token` and returns at most 100 budgets per page on a
payer. For each budget, page `aws budgets describe-notifications-for-budget`
(up to 100/page) and, for each notification, `aws budgets
describe-subscribers-for-notification`. Always drain `NextToken` to completion
— the long tail of stale, decorative, or breached budgets hides beyond page
one. Budgets are **account-scoped, not regional**; the Budgets API endpoint is
`us-east-1` regardless of where workloads run, so always query
`--region us-east-1`.

**Live-account pre-flight checks (skip if doing offline budget-doc audit):**
1. Confirm the caller identity has `budgets:DescribeBudget*` and
   `sns:GetTopicAttributes`. A read-only auditor role without SNS read
   permission will silently skip Step 3 (the SNS policy check) — the most
   common misclassification source. Surface this BEFORE the operator trusts an
   OK verdict.
2. For consolidated-billing (Organizations) accounts, run
   `aws organizations list-accounts` and audit the **payer** budget inventory.
   A payer budget with no `LinkedAccount` filter covers ALL member accounts; a
   member account with no own budget and no payer visibility is a blind spot.
3. Snapshot `aws budgets describe-budget-performance-history --account-id <id>`
   when available — it shows whether a budget has historically breached,
   calibrating whether a CONFIG_GAP is theoretical or recurring.

**If the budget inventory is malformed** (invalid JSON/YAML, missing required
`BudgetName` or `BudgetLimit` on a COST budget), output:

```text
BUDGET: <name or unknown>
VERDICT: ERROR
REASON: Budget configuration is not valid — cannot classify (missing BudgetName or BudgetLimit).
REMEDIATION: Re-fetch with `aws budgets describe-budget --account-id <id> --budget-name <name> --region us-east-1` and re-audit.
```

Do not attempt classification on malformed input.

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious AWS Budgets behaviours

These behaviours are easy to misjudge without operational Budgets experience.
Each changes a verdict if ignored:

- **Cost-data lag is real and material.** Budget actuals are fed by the
  Cost Explorer / Billing pipeline, which trails real-time spend by 8-14 hours
  (up to 24 hours historically and during month-end close). A budget showing
  90% actual may already be over budget. This is why a FORECASTED notification
  matters: it projects month-end spend from the current trajectory, giving
  hours-to-days of lead time that an ACTUAL-only alert cannot. Do NOT treat
  "actual is under the limit" as a safe state when the forecast breaches.

- **SNS topic policy omission fails SILENTLY.** When a budget notification
  targets an SNS topic whose policy does not grant `sns:Publish` to
  `budgets.amazonaws.com`, the notification is dispatched by Budgets but
  rejected by SNS at delivery. There is NO error surfaced in the Budgets
  console — the notification simply never arrives. The only signal is a
  missing CloudTrail `Publish` event or a dead-letter queue. This is the #1
  reason budget alerts "don't work" in production. The required statement is
  explicit and cannot be inferred from the budget configuration alone — you
  must read the SNS topic policy (`aws sns get-topic-attributes`).

- **FORECASTED vs ACTUAL are different triggers, not aliases.** `ACTUAL`
  means "current calculated spend has crossed the threshold." `FORECASTED`
  means "the projected month-end spend is predicted to cross the threshold."
  A budget with only ACTUAL notifications is reactive; a budget with
  FORECASTED notifications is predictive. For a MONTHLY cost budget, the
  absence of any FORECASTED notification is a CONFIG_GAP because it removes
  the only lead-time signal that cost-data lag otherwise eats.

- **A single 100% threshold leaves zero reaction time.** If the only
  notification is at 100% ACTUAL, the operator learns they are over budget
  after the spend has already occurred (plus the data lag). Best practice is
  at least two thresholds below breach: a 50% (awareness) and an 80-90%
  (action) tier, plus the 100% (breach) tier. A single-threshold budget is a
  CONFIG_GAP even if the threshold fires.

- **Budget notifications are capped at 11 per budget.** Each notification is
  one (threshold, type) pair. This is a hard quota. When proposing additional
  FORECASTED or early-warning notifications, confirm the budget is not already
  at 11 — the `CreateNotification` call will fail with
  `LimitExceededException`.

- **RI/SP Coverage and Utilization budgets are NOT cost budgets.** A budget
  with `BudgetType: RI_COVERAGE`, `RI_UTILIZATION`, `SP_COVERAGE`, or
  `SP_UTILIZATION` measures reservation effectiveness (a percentage), not
  spend. They have no `BudgetLimit` in dollars. Do NOT apply Steps 4-6
  (threshold/forecast/actual-spend) to them — their thresholds are utilization
  percentages, not cost ratios. Still audit their notification wiring (Steps
  2-3). Misclassifying an RI_UTILIZATION budget as breached on cost is a false
  positive.

- **Auto-adjusting budgets move the limit.** A budget with
  `AutoAdjustType: HISTORICAL` recalculates its `BudgetLimit` from trailing
  spend each period. Threshold percentages apply to a MOVING baseline, so a
  100% alert on an auto-adjusting budget means "100% of last period's pattern,"
  not a fixed dollar ceiling. Note this when assessing breach posture — the
  budget is harder to breach but also weaker as a hard cap.

- **Budget Actions are the enforcement tier, separate from alerting.** A
  budget can apply an IAM policy or SCP (`ActionType: APPLY_IAM_POLICY`,
  `APPLY_SCP_POLICY`) or run a SSM document when breached, via an assumed role.
  This is enforcement, not alerting. The ABSENCE of a Budget Action is NOT a
  CONFIG_GAP unless the account's policy explicitly mandates enforcement —
  most accounts use alert-only budgets by design. Do not flag a missing
  Budget Action as a gap; flag a misconfigured Action (missing approval model,
  over-broad applied IAM policy) if present.

- **CloudWatch billing alarms are legacy, not redundant.** The
  `AWS/Billing EstimatedCharges` metric updates roughly every 6 hours and is
  account-total only (no service/tag/linked-account filtering). Budgets
  supersede billing alarms with richer filtering and FORECASTED projections.
  Having both is fine (defense-in-depth) but a billing alarm is NOT a
  substitute for a budget, and a budget is not redundant because a billing
  alarm exists.

- **`CostTypes` filtering changes what "spend" means.** A COST budget with
  `IncludeTax: false` under-reports by the tax line; `UseAmortized: true`
  spreads upfront RI/SP charges across the term. Two budgets with the same
  limit but different `CostTypes` are not comparable. When assessing breach,
  confirm the `CostTypes` match the operator's intent before flagging.

- **Linked-account filtering on a payer budget.** A payer (management)
  account budget with no `LinkedAccount` filter covers ALL member-account
  spend. A budget with a `LinkedAccount` filter covers only that one account.
  For chargeback, each member account should have its own budget or the payer
  budget should be filtered. A payer-wide budget masking a runaway member
  account is a blind spot.

### Step 1: Budget existence gate (NO_BUDGET — highest priority)

If the account has **zero budgets** of any type (COST, RI_*, SP_*, USAGE),
the verdict is **NO_BUDGET**. This is the worst posture: no spend visibility,
no alerting, no forecast. This is the default state for newly created
accounts and the highest-risk configuration for credential compromise or
runaway resources.

NO_BUDGET short-circuits all other steps — there is nothing to evaluate
notifications against. The remediation is to create at minimum a total-account
cost budget and (for new/sandbox accounts) a zero-spend guardrail.

### Step 2: Notification and subscriber gate (NO_ALERT)

For each budget, evaluate notification coverage:

- **Zero notifications** on the budget → the budget is **decorative**. It
  tracks spend in the console but never alerts anyone. Per-budget verdict:
  **NO_ALERT**.
- **Notifications exist but every notification has an empty subscriber list**
  (`Subscribers: []`) → the notification has nowhere to deliver. Per-budget
  verdict: **NO_ALERT**.

A budget that triggers NO_ALERT is functionally equivalent to no budget for
the purpose of alerting — the spend may as well be unmonitored. The difference
between NO_BUDGET and NO_ALERT is that NO_ALERT means "the tracking exists but
the human-in-the-loop is severed," while NO_BUDGET means "there is no tracking
at all." Both are HIGH risk.

### Step 3: SNS topic policy delivery check (CONFIG_GAP)

For each notification with an SNS subscriber (`SubscriptionType: SNS`), the
notification can only deliver if the SNS topic policy grants `sns:Publish` to
the `budgets.amazonaws.com` service principal. Retrieve the topic policy
(`aws sns get-topic-attributes --topic-arn <arn>`) and check for a statement
matching:

```json
{
  "Effect": "Allow",
  "Principal": { "Service": "budgets.amazonaws.com" },
  "Action": "SNS:Publish",
  "Resource": "<topic-arn>"
}
```

- **Statement absent** → the notification will silently fail to deliver.
  Per-budget verdict: **CONFIG_GAP** (Finding: SNS_POLICY_GAP). This is the
  most common reason budget alerts "don't work" and produces zero console
  error.
- **Statement present but scoped to a different region or account** →
  CONFIG_GAP (the ARN mismatch causes rejection).
- **EMAIL/EMAIL-JSON subscribers do NOT require an SNS topic policy** —
  Budgets delivers directly to the email address. Skip Step 3 for email-only
  subscribers. (Note: email subscribers still require a confirmation click on
  the AWS-sent subscription email; an unconfirmed email is a delivery gap but
  is surfaced in the console, unlike the silent SNS policy failure.)

### Step 4: Threshold coverage check (CONFIG_GAP)

For each COST budget with notifications, evaluate the threshold set:

- **Single threshold** (only one notification on the budget) → **CONFIG_GAP**
  (Finding: SINGLE_THRESHOLD). A single alert leaves no time to react —
  regardless of where it sits, there is no early-warning tier.
- **No threshold below 80%** → **CONFIG_GAP** (Finding: NO_EARLY_WARNING). If
  the lowest threshold is at 80% or higher, the operator gets no awareness
  signal before the budget is nearly exhausted. Best practice: at least one
  threshold at 50% (awareness) and one at 80-90% (action).
- **No threshold at or above 100%** → **CONFIG_GAP** (Finding: NO_BREACH_ALERT).
  If no notification covers the actual breach point, the operator may never
  learn they are over budget.

A budget with thresholds at {50%, 80%, 100%} or {70%, 90%, 100%} passes this
step. A budget with only {100%} or only {90%} fails.

### Step 5: FORECASTED coverage check (COST budgets only — CONFIG_GAP)

For each COST budget (BudgetType `COST` or `USAGE`), evaluate notification
types:

- **All notifications are `ACTUAL`, zero `FORECASTED`** → **CONFIG_GAP**
  (Finding: NO_FORECAST). Without a FORECASTED notification, the operator has
  no predictive signal. Combined with cost-data lag, an ACTUAL-only alert at
  100% arrives after the budget is already breached by hours. A FORECASTED
  notification at 80-100% projects month-end spend and gives lead time.

This check does NOT apply to RI/SP budgets (their "forecast" is utilization
trajectory, handled differently) or to DAILY budgets where month-end
projection is meaningless.

### Step 6: Actual-vs-forecast breach check (CONFIG_GAP)

For each COST budget, compare `CalculatedSpend` against `BudgetLimit`:

- **`ForecastedSpend >= BudgetLimit`** and NO FORECASTED notification covers
  the breached ratio → **CONFIG_GAP** (Finding: FORECAST_BREACH_UNALERTED).
  The budget is on track to exceed by month-end but no forecast alert will
  fire.
- **`ActualSpend >= BudgetLimit`** (already breached) and NO ACTUAL
  notification covers 100% → **CONFIG_GAP** (Finding: ACTUAL_BREACH_UNALERTED).
  The budget has been exceeded but no actual alert will fire.

Note: a breach with a matching alert that WILL fire is informational, not a
CONFIG_GAP — the system is working as designed. Only flag when the breach is
uncovered by the notification set.

### Step 7: Zero-spend guardrail for new/sandbox accounts (CONFIG_GAP)

If the account is flagged as new, sandbox, or non-production (operator-provided
context, or account name/tag convention), check for a zero-spend or low-spend
guardrail:

- **No COST budget with `BudgetLimit <= $1.00` (or `<= $0.01`) and a 100%
  ACTUAL notification** → **CONFIG_GAP** (Finding: NO_ZERO_SPEND_GUARDRAIL).
  A zero-spend budget catches ANY unauthorized spend immediately — the leading
  signal for a compromised credential, a misconfigured free-tier resource, or
  a stray workload. Without it, a new account can accumulate charges for days
  before a normal budget trips.

This check is advisory-in-practice but Config_GAP-in-verdict because the
absence of a zero-spend guardrail on a new account is the single highest-leverage
FinOps control. For established production accounts, skip this step.

### Step 8: Aggregation — worst per-budget verdict wins

The account-level verdict is the **maximum severity** across all per-budget
verdicts, where NO_BUDGET > NO_ALERT > CONFIG_GAP > OK:

```text
account_verdict = max(all_budget_verdicts)
```

If the account has budgets and all pass Steps 2-7 with no findings, the
account verdict is **OK**. NO_BUDGET is only reachable when the account has
zero budgets (Step 1).

**Severity/risk mapping (emitted per finding):**
- NO_BUDGET → **HIGH** (total spend blind spot; default for new accounts)
- NO_ALERT → **HIGH** (budget is decorative; spend tracked but never alerted)
- CONFIG_GAP (SNS_POLICY_GAP) → **HIGH** (alerts silently fail to deliver)
- CONFIG_GAP (SINGLE_THRESHOLD / NO_EARLY_WARNING / NO_FORECAST) → **MEDIUM**
- CONFIG_GAP (NO_ZERO_SPEND_GUARDRAIL) → **MEDIUM** for new accounts
- CONFIG_GAP (breach uncovered) → **MEDIUM** (the breach is real but alertable
  with a fix)
- OK → **LOW**

## Output format (per account)

```text
ACCOUNT: <account-id>
VERDICT: NO_BUDGET | NO_ALERT | CONFIG_GAP | OK
REASON: <1-2 sentences citing the triggering step and worst finding>
FINDINGS:
  - [HIGH] <budget name>: <finding description (Step N)>
  - [MEDIUM] <budget name>: <finding description (Step N)>
  - [OK] <budget name>: <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — decorative budget with SNS policy gap

```text
ACCOUNT: 111111111111
VERDICT: CONFIG_GAP
REASON: Budget "monthly-total" has a single 100% ACTUAL notification wired to
an SNS topic whose policy omits the budgets.amazonaws.com publish principal —
alerts silently fail to deliver (Step 3), and there is no FORECASTED
notification for lead time (Step 5).
FINDINGS:
  - [HIGH] monthly-total: SNS topic arn:aws:sns:us-east-1:111111111111:budget-alerts
    policy lacks budgets.amazonaws.com sns:Publish — alerts dispatched but
    rejected at delivery (Step 3)
  - [MEDIUM] monthly-total: single threshold at 100% ACTUAL — no early warning
    and no FORECASTED notification (Steps 4, 5)
  - [OK] monthly-total: budget exists with BudgetLimit $10000, not breached
REMEDIATION:
  1. Add the budgets service principal to the SNS topic policy (see Step 3
     remediation CLI).
  2. Add a FORECASTED notification at 80% and an early-warning ACTUAL at 50%.
```

## Edge-case handling

- **Partially malformed budget.** If one budget in a multi-budget inventory is
  malformed, classify the valid budgets normally and emit an ERROR note for
  the malformed one: "Budget <name> is malformed (missing BudgetLimit) —
  skipped." Do NOT fail the entire account audit on one bad budget.

- **RI/SP budget mistaken for a cost breach.** A budget with
  `BudgetType: RI_UTILIZATION` and `BudgetLimit: {Amount: 100, Unit: PERCENTAGE}`
  is NOT a cost budget. Do not flag it as breached if `ActualSpend` exceeds a
  dollar amount — there is no dollar amount. Evaluate only its notification
  wiring (Steps 2-3).

- **Budget with email subscriber only (no SNS).** An EMAIL subscriber does not
  require an SNS topic policy. Skip Step 3. However, if the email is
  unconfirmed (the AWS subscription-confirmation email was never clicked),
  delivery silently fails — note this as an operational risk but it is not an
  SNS policy gap.

- **Zero-budget account with an org-level payer budget.** A member account
  with no own budgets but whose payer has a covering budget is NOT a
  NO_BUDGET finding IF the payer budget visibility is confirmed. Flag as a
  CONFIG_GAP (Finding: RELIES_ON_PAYER_BUDGET) because the member account has
  no independent alerting and the payer budget may be filtered to exclude it.

- **Auto-adjusting budget at 100%.** An auto-adjusting budget
  (`AutoAdjustType: HISTORICAL`) at 100% means it matched last period's
  pattern — not necessarily a cost problem. Note the auto-adjustment when
  assessing breach; do not flag a 100% actual as a breach unless the absolute
  spend is itself anomalous.

- **DAILY budget.** A DAILY TimeUnit budget resets each day. FORECASTED
  notifications are not meaningful for DAILY budgets (there is no month-end
  projection). Skip Step 5 for DAILY budgets. QUARTERLY/ANNUALLY budgets
  should have FORECASTED notifications like MONTHLY ones.

- **Budget Action present.** If a Budget Action (`APPLY_IAM_POLICY` /
  `APPLY_SCP_POLICY`) is configured, note it as an enforcement finding (OK or
  informational). Do NOT treat its presence as remediation for a missing
  notification — enforcement and alerting are independent tiers. A budget
  with an Action but no SNS/email notification still has NO_ALERT.

## Anti-Patterns — NEVER

- NEVER classify an account with zero budgets as anything other than
  NO_BUDGET. "No budgets" is a total spend blind spot — the highest-risk
  FinOps posture. Do not soften it to CONFIG_GAP.

- NEVER treat a budget with zero notifications as OK. A budget without
  notifications is decorative — it tracks spend nobody watches. This is
  NO_ALERT, not OK. The console showing a spend number is not alerting.

- NEVER assume an SNS subscriber means alerts will deliver. The SNS topic
  policy MUST explicitly grant `sns:Publish` to `budgets.amazonaws.com`. A
  missing policy statement fails silently with zero console error — this is
  the #1 reason budget alerts "don't work." Always read the topic policy.

- NEVER flag an RI_COVERAGE / RI_UTILIZATION / SP_COVERAGE / SP_UTILIZATION
  budget as cost-breached. These budget types measure reservation
  effectiveness (a percentage), not spend. They have no dollar BudgetLimit.
  Applying cost-breach logic to them is a false positive.

- NEVER treat the absence of a Budget Action as a CONFIG_GAP. Budget Actions
  (enforcement) are an opt-in tier separate from alerting. Most accounts use
  alert-only budgets by design. Only flag a misconfigured Action if one is
  present.

- NEVER assume "actual under limit" means the budget is safe. Cost-data lag
  trails real spend by 8-14 hours. A budget at 90% actual may already be over.
  Always check the FORECASTED spend against the limit, not just actual.

- NEVER recommend a single-threshold budget as adequate. A lone 100% ACTUAL
  alert fires after the spend is incurred plus the data lag. A budget needs at
  least an early-warning tier (50%) and an action tier (80-90%) below the
  breach alert (100%).

- NEVER treat a CloudWatch billing alarm as a substitute for a budget.
  Billing alarms (`AWS/Billing EstimatedCharges`) are account-total only,
  update every ~6 hours, and have no FORECASTED projection or filtering. They
  are legacy defense-in-depth, not a replacement for AWS Budgets.

- NEVER skip pagination on `describe-budgets` or
  `describe-notifications-for-budget`. The long tail of budgets (beyond page
  one) is where stale, decorative, and breached budgets hide. Always drain
  `NextToken` to completion.

- NEVER conflate FORECASTED and ACTUAL notification types. FORECASTED projects
  month-end spend; ACTUAL reports current calculated spend. They are not
  interchangeable. A budget with only ACTUAL notifications is reactive; a
  budget with FORECASTED notifications is predictive. Both belong in a mature
  budget config.

- NEVER assume a payer-wide budget covers a member account's alerting needs.
  A payer budget with no `LinkedAccount` filter aggregates all member spend
  but a runaway member account can hide inside an aggregate that is under
  limit. For chargeback and isolation, member accounts need their own budgets
  or the payer budget must be filtered per account.

- NEVER propose more than 11 notifications on a single budget. The quota is
  11 notifications per budget (hard limit). A remediation proposing a 12th
  notification will fail with `LimitExceededException`. Count existing
  notifications before adding.

- NEVER ignore the `CostTypes` filter when assessing breach. A budget with
  `IncludeTax: false` under-reports by the tax line. Two budgets with the same
  limit and different `CostTypes` are not comparable. Confirm the filter
  matches intent before flagging a breach.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (CreateBudget, CreateNotification, CreateSubscriber, DeleteNotification,
  SetTopicAttributes on an SNS policy, PutBudgetAction), the auditor MUST
  emit: `CONFIRM: About to <action> on budget <name> in account <account>.
  This affects <consequence>. Proceed? (yes/no)` Do NOT execute the CLI
  command until the operator confirms. Budgets changes can suppress or
  duplicate live alerting.
- Confirm the caller identity has `budgets:Create*` and `sns:SetTopicAttributes`
  if remediation is intended — most read-only auditor roles CANNOT, and
  remediation commands will fail with `AccessDenied`. Surface this BEFORE the
  operator approves.
- Before modifying an SNS topic policy, capture the current policy for
  rollback: `aws sns get-topic-attributes --topic-arn <arn> --region us-east-1
  > /tmp/<topic>-policy-backup-$(date +%s).json`. SNS topic policies are not
  versioned — a bad policy statement can break ALL topic publishers, not just
  Budgets.
- Prefer additive changes (add a notification, add a topic-policy statement)
  over destructive changes (delete a notification, replace a policy). Additive
  changes are reversible and cannot break existing delivery.
- Before creating a zero-spend budget on a new account, confirm the account
  has no expected spend (a zero-spend budget with legitimate ongoing spend
  generates constant false-positive alerts). For sandbox accounts with small
  expected spend, use a $1 or $5 guardrail, not $0.01.

## Remediation guidance

**Ordering principle:** always prefer additive changes. Add a notification
before deleting one; add a topic-policy statement before rewriting the policy.
This prevents a window where no alerting is in effect.

### For NO_BUDGET — account has zero budgets

1. Create a total-account MONTHLY cost budget at the operator's expected
   monthly spend:
   `aws budgets create-budget --account-id <id> --budget file://total.json
   --notifications-with-subscribers file://subs.json --region us-east-1`
2. Add at minimum: ACTUAL 50%, FORECASTED 80%, ACTUAL 100% notifications wired
   to an SNS topic (with the budgets principal in its policy) or an email.
3. For new/sandbox accounts, additionally create a zero-spend guardrail
   (Step 7).
4. For Organizations/consolidated-billing, create a payer-level budget AND per-
   member budgets (or filtered payer budgets) for chargeback visibility.

### For NO_ALERT — budget has zero functional notifications

1. Create notifications: `aws budgets create-notification --account-id <id>
   --budget-name <name> --notification <json> --subscribers <json>
   --region us-east-1`.
2. Minimum set for a MONTHLY COST budget: ACTUAL 50% (awareness), FORECASTED
   80% (action), ACTUAL 100% (breach). Wire each to an SNS topic or email.
3. Confirm the SNS topic policy grants `budgets.amazonaws.com` publish (see
   CONFIG_GAP / SNS policy remediation).

### For CONFIG_GAP — SNS topic policy missing budgets principal (Step 3)

1. Retrieve the current policy: `aws sns get-topic-attributes --topic-arn <arn>
   --region us-east-1 --query 'Attributes.Policy' --output text`.
2. Add (do not replace) a statement granting the budgets principal publish:
   ```bash
   aws sns set-topic-attributes --topic-arn <arn> --region us-east-1 \
     --attribute-name Policy --attribute-value '<updated-policy-json-with-budgets-statement>'
   ```
3. Verify delivery by triggering a test budget notification or waiting for the
   next threshold crossing and checking CloudTrail for a `Publish` event from
   `budgets.amazonaws.com`.

### For CONFIG_GAP — single threshold / no early warning (Step 4)

1. Add a 50% ACTUAL notification (awareness) and an 80-90% ACTUAL or
   FORECASTED notification (action tier) via `create-notification`.
2. Keep the existing 100% notification as the breach tier. Do NOT delete it.
3. Confirm total notifications do not exceed 11 per budget.

### For CONFIG_GAP — no FORECASTED notification (Step 5)

1. Add a FORECASTED notification at 80% and/or 100% via
   `create-notification --notification ... --notification-type FORECASTED`.
2. This provides lead time that ACTUAL-only alerts cannot, given cost-data
   lag.

### For CONFIG_GAP — zero-spend guardrail missing (Step 7)

1. Create a COST budget with `BudgetLimit.Amount: 0.01` (or `1.00` for sandbox
   with tiny expected spend), `TimeUnit: MONTHLY`, and an ACTUAL 100%
   notification wired to an SNS topic or email.
2. Name it distinctly (e.g., `zero-spend-guardrail`) so it is recognizable in
   audits.

### For OK

1. No remediation required for current posture.
2. Recommend verifying the SNS topic policy quarterly — policy drift from
   other tooling can silently remove the budgets principal.
3. Recommend confirming email subscribers are still valid (personnel churn).
4. For Organizations, verify member accounts have independent alerting, not
   just payer-level coverage.

## Deep reference: AWS Budgets internals

### Notification delivery pipeline

When a budget threshold crosses, Budgets dispatches the notification to each
subscriber in parallel. For SNS, Budgets calls `sns:Publish` as the
`budgets.amazonaws.com` service principal — the topic policy is the only gate.
For EMAIL, Budgets sends via AWS SES directly (no SNS topic policy needed).
For CHATBOT, the subscriber targets a chat client configured in us-east-1.
If the topic policy rejects the publish, the notification is dropped — there
is no retry, no dead-letter by default, and no console error. The only
forensic signal is the absence of a CloudTrail `Publish` event.

### Cost data pipeline and lag

Budget actuals flow from the Billing service → Cost Explorer → Budgets
calculation engine. The pipeline batches every few hours and finalizes
previous-period data during the month-end close (which can take 1-3 days).
This means: (1) same-day spend is never reflected in budget actuals; (2) the
last few days of a month may show artificially low actuals until close
completes; (3) a FORECASTED notification, which uses Cost Explorer's
projection engine, is the only mechanism that accounts for in-flight but
un-billed spend.

### Quotas and limits

- Budgets per account: 20,000 (service quota, raisable).
- Notifications per budget: 11 (hard limit per budget, not raisable per
  notification — plan threshold sets carefully).
- Budget Actions per account: limited; each Action requires an approval model
  and an IAM role for Budgets to assume.
- Subscriber types: SNS, EMAIL, EMAIL_JSON, SQS, CHATBOT (us-east-1 for
  budget notifications).

## Domain

AWS CloudOps / FinOps Cost Control & Spend Visibility.
