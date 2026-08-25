# budgets-auditor — advanced patterns (moved from SKILL.md)

Progressive-disclosure reference. Content below was moved verbatim from SKILL.md; the agent loads it only when needed.

## Step 0: Expert knowledge — non-obvious AWS Budgets behaviours

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

## Recent AWS features (2024-2026)

- **Budget filters on cost allocation tags (2024):** AWS Budgets now supports filtering by cost allocation tags, dimensions, and expressions. Auditors should verify that budgets are scoped appropriately — an unfiltered budget may mask departmental cost overruns, while an over-filtered budget may miss account-level spend.
- **Zero-spend budgets (2024):** Budgets with a zero-spend threshold for sandbox/new accounts. Auditors should check whether new accounts have a zero-spend guardrail budget, as the skill already recommends.
- **Savings Plan utilization and coverage budgets (2024):** Budgets can now monitor Savings Plan utilization and coverage metrics directly. Auditors should verify that commitment-utilization budgets exist alongside cost budgets.
