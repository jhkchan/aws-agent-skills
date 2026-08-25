---
name: budget-action-automator
description: Designs and deploys AWS Budgets automated actions — cost, usage, RI coverage, and RI utilization budgets with threshold-driven responses. Covers budget creation (actual vs forecasted alerts), SNS notification wiring, IAM action attachment (apply SCP deny on breach, apply IAM policy to constrain usage), EventBridge routing to Lambda for custom remediation (stop non-prod EC2, tag untagged resources, post to Slack), multi-account rollout via Organizations Payer, cost allocation tag enforcement as a budget prerequisite, Budgets API automation patterns, forecast-based proactive action before actual breach, and budget rollover/reset semantics. Emits AUTOMATION_DEPLOYED with a workflow template (CloudFormation / CLI) or REVIEW_REQUIRED with the specific gap. Use when building budget actions, wiring IAM or SCP responses to budget breaches, or complementing Cost Anomaly Detection with threshold-based controls.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline workflow design. Live deployment uses aws budgets create-budget, create-notification, subscribe, put-budget-action, describe-budget-action, aws ce get-cost-and-usage, get-cost-forecast, aws organizations attach-policy, create-policy, aws sns create-topic — AWS CLI v2, SSO or key-based credentials.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '4'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: FinOps
  task_type: automate
  skill_class: capability
  lifecycle_status: active
  verdict_shape: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
  when_to_use: Designing AWS Budgets automated actions, wiring IAM/SCP responses to budget breaches, building multi-account budget rollouts via Organizations Payer, enforcing cost allocation tags before budget creation, complementing Cost Anomaly Detection with threshold controls, configuring forecast-based proactive action, or automating RI coverage / RI utilization budgets.
  activation_triggers: automate budget action, put-budget-action, budget breach SCP, budget SNS notification, forecast budget action, RI coverage budget, RI utilization budget, budget multi-account payer, cost allocation tag budget, Budgets API automation, budget EventBridge Lambda, budget Slack notification
  invocation_schema: 'Input: either (a) a budget requirement ("alert at 80% of $10K monthly cost budget and deny new EC2 launches at 100%"), OR (b) a budget configuration under review. Output: deterministic BUDGET ACTION block per budget — BUDGET/THRESHOLD/NOTIFICATION/RESPONSE/ MULTI_ACCOUNT/VERDICT — where VERDICT is AUTOMATION_DEPLOYED (workflow template ready) or REVIEW_REQUIRED (specific gap cited).'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: AWS Budgets, budget action, put-budget-action, SCP deny, SNS notification, cost budget, usage budget, RI coverage, RI utilization, forecast threshold, Cost Anomaly Detection, cost allocation tags, Organizations Payer, budget rollover, EventBridge budget, FinOps automation
  tags: aws-budgets, finops, cost-optimization, scp, iam-action, eventbridge, automate
---

# Budget Action Automator

## Mindset

**One-line takeaway:** every budget action is a four-stage pipeline —
**define** (budget type, amount, period) → **threshold** (actual and/or
forecasted, with the right comparison) → **notify** (SNS, email, Slack
via Lambda) → **respond** (IAM/SCP action for hard enforcement, or
EventBridge → Lambda for custom remediation). A gap in ANY stage
produces a silent failure: the budget fires but no one hears it, or
the notification arrives after spend already blew past the limit.

- **Budget type** without the right **threshold type** is noise: a
  cost budget alerted only on `ACTUAL` misses the chance to act
  before the money is spent. Forecast thresholds catch trends 3-7
  days before actual breach.
- **Notification** without **response** is reporting, not control.
  SNS to an email queue is a post-mortem; SCP deny on the OU is
  prevention of further spend.
- **SCP deny is the only hard enforcement primitive in Budgets.** A
  budget action with `ActionType: APPLY_SCP` (formerly
  `APPLY_POLICY`) blocks new resource creation in the target account
  or OU. It does NOT shut down already-running resources — pair it
  with EventBridge → Lambda → `stop-instances` for full enforcement.

## Quick navigation

| You want to... | Go to |
|---|---|
| Pick a budget type (cost/usage/RI coverage/RI utilization) | Step 2 |
| Choose actual vs forecasted threshold | Step 3 |
| Wire SNS notification | Step 4 |
| Apply SCP deny for hard enforcement | Step 5 |
| Apply IAM policy via budget action | Step 6 |
| EventBridge → Lambda for custom action | Step 7 |
| Stop non-prod EC2 on breach | Step 8 |
| Tag untagged resources via budget | Step 9 |
| Slack notification via Lambda | Step 10 |
| Multi-account via Organizations Payer | Step 11 |
| Cost allocation tag prerequisite | Step 12 |
| Forecast-based proactive action | Step 13 |
| Budget vs Cost Anomaly Detection | Step 14 |
| Budget rollover / reset semantics | Step 15 |
| Common destructive-change pitfalls | Anti-Patterns |

## Critical rules at a glance (do NOT bury these)

1. **`put-budget-action` with `APPLY_SCP` only attaches the policy;
   it does NOT retroactively constrain resources.** It also requires
   the budget action to be in an account that is a member of an
   Organization, and the target must be the account itself or an OU
   it belongs to. A standalone account cannot use SCP actions.
2. **Forecast thresholds (`FORECASTED`) are probabilistic.** AWS
   forecast models are 80% confidence intervals by default. A
   forecast alert at 100% of budget may fire when actual spend is
   only at 70%. Always pair forecast with a higher actual threshold
   to avoid premature action.
3. **Cost allocation tags MUST be activated in the Billing console
   before any budget that uses `CostFilters` (e.g., by `env`,
   `team`, `project`) will work.** A budget with
   `CostFilters: {Tag: [env:prod]}` against a tag that is not
   activated produces zero matched spend — the budget never fires.
4. **Budget actions (`put-budget-action`) are distinct from
   notifications (`create-notification` + `subscribe`).** A
   notification sends an SNS/email message; an action runs IAM/SCP
   or both. Many operators wire notification and assume enforcement
   is in place.
5. **RI coverage and RI utilization budgets do NOT respond to
   on-demand spend directly.** They measure commitment performance.
   A 70% RI coverage budget at 65% actual coverage fires regardless
   of total dollar spend — useful for ensuring commitment
   compliance, not for cost control.

## Pre-flight: data requirements

Designing a budget action requires these inputs:

| Input | Source | Why |
|---|---|---|
| Budget type | Cost / Usage / RI Coverage / RI Utilization | Drives the `BudgetType` field |
| Budget amount + time unit | Customer-specified or derived from CE | `BudgetLimit.Amount` + `TimeUnit` |
| Cost filters (optional) | Tag, LinkedAccount, Service, etc. | `CostFilters` for scoped budgets |
| Notification thresholds | Customer-specified % of budget | Drives `Notification.Threshold` + `ThresholdType` |
| Response type | Notify only / IAM / SCP / Lambda | Drives `ActionType` |
| Account structure | `organizations list-roots`, `list-organizational-units` | SCP target for multi-account |
| SNS topic ARN | `sns create-topic` | Notification destination |
| Cost allocation tags status | `ce get-cost-and-usage` (TagKey filter) | Verify tags are activated before scoping |
| Existing budgets | `budgets describe-budgets` | Avoid overwriting |

**If the input is malformed** (missing budget amount, ambiguous
budget type), emit:

```text
BUDGET: <reference>
VERDICT: ERROR
REASON: Cannot design budget action — budget type, amount, and time unit are required.
GAP: Re-supply the budget requirement with explicit type (cost/usage/RI coverage/RI utilization), dollar or unit amount, and monthly/quarterly/annual period.
```

## Process — Workflow design (apply in order)

### Step 0: Expert knowledge — non-obvious Budgets behaviors

Step 0 expert-knowledge deep dive (action vs notification APIs, SCP no auto-detach, 8-12 hour evaluation, CE lag, threshold semantics, SSM definitions, per-account budgets, blended cost, RI vs SP budget types, execution-role silent failure) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when workflow design hinges on a non-obvious Budgets behavior.

### Step 1: Classify the budget goal

For each budget requirement, classify the goal:

| Goal | Budget type | Example | Notes |
|---|---|---|---|
| Cost containment | `COST` | "$10K/month total spend" | Most common; tracks unblended cost |
| Usage tracking | `USAGE` | "10,000 EC2 hours/month" | Useful for free-tier guardrails |
| Commitment performance | `RI_COVERAGE` | "75% RI coverage for EC2" | Drives commitment strategy |
| Commitment efficiency | `RI_UTILIZATION` | "95% RI utilization" | Detects unused RIs |
| Savings Plan coverage | `SAVINGS_PLANS_COVERAGE` | "80% SP coverage" | Modern alternative to RI |
| Savings Plan utilization | `SAVINGS_PLANS_UTILIZATION` | "95% SP utilization" | Detects unused SPs |

If the goal is "stop over-spend," use `COST`. If the goal is "ensure
we use what we committed," use `RI_UTILIZATION` or
`SAVINGS_PLANS_UTILIZATION`. If the goal is "ensure we commit enough
to cover our footprint," use `RI_COVERAGE` or
`SAVINGS_PLANS_COVERAGE`.

### Step 2: Pick the budget type and time period

| Time unit | Use case | Reset behavior |
|---|---|---|
| `MONTHLY` | Most operational budgets | Resets on the 1st (calendar month) |
| `QUARTERLY` | Capex / project budgets | Resets at the start of each quarter |
| `ANNUALLY` | Fiscal-year budgets | Resets on the configured start date |
| `DAILY` | High-resolution guardrails | Resets at 00:00 UTC |

**Budget rollover is NOT native.** AWS Budgets reset to zero at the
start of each period — they do NOT carry forward unused budget. For
"quarterly capex that rolls over," track it in a separate system
(e.g., a Lambda that stores the delta in DynamoDB) and use the
Lambda to gate the budget action rather than relying on
`BudgetLimit`.

### Step 3: Choose the threshold type (the threshold matrix)

| Threshold type | When it fires | Use case |
|---|---|---|
| `ACTUAL` | When actual spend crosses the threshold | Late-stage alerting; cannot prevent breach |
| `FORECASTED` | When forecasted end-of-period spend crosses threshold | Proactive; 3-7 day warning before breach |
| Combined (ACTUAL 100% + FORECASTED 90%) | Both | Recommended for production budgets |

**Decision rule:** default to **both** `FORECASTED` at 80% (warning)
and 90% (action), plus `ACTUAL` at 100% (hard enforcement). For
non-critical budgets, `ACTUAL` at 100% alone is acceptable.

Forecast thresholds in detail:

```text
FORECASTED @ 80% → SNS notify (Slack/email — human attention)
FORECASTED @ 90% → SNS + IAM policy (restrict IAM user)
ACTUAL     @ 100% → SCP deny (block new resource creation)
ACTUAL     @ 110% → EventBridge → Lambda → stop non-prod EC2
```

### Step 4: Wire SNS notification

Step 4 full CLI walkthrough (create-budget + SNS topic policy + silent-failure pitfall) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when wiring a notify-only budget.

### Step 5: Apply SCP deny for hard enforcement

Step 5 SCP walkthrough (put-budget-action APPLY_SCP_FAMILY, pre-created SCP, execution-role trust policy) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when wiring SCP enforcement.

### Step 6: Apply IAM policy via budget action

Step 6 IAM-action walkthrough (put-budget-action APPLY_IAM_ACTION + restrict policy JSON) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when wiring per-user enforcement.

### Step 7: EventBridge → Lambda for custom action

Step 7 EventBridge rule, Lambda handler pattern, and native-vs-Lambda trade-off table moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the required response exceeds native IAM/SCP actions.

### Step 8: Stop non-prod EC2 on budget breach

Step 8 SSM stop-instances action and its limitations moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when stopping instances on breach.

### Step 9: Tag untagged resources via budget action

Step 9 tag-compliance budget and Resource Groups Tagging API Lambda moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when enforcing tag compliance via budgets.

### Step 10: Slack notification via Lambda

Step 10 Slack-forwarder subscription and Lambda handler moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when routing budget alerts to Slack.

### Step 11: Multi-account via Organizations Payer

Step 11 payer CostFilters and StackSet walkthrough plus scoping-technique table moved verbatim to [references/multi-account-budget-patterns.md](references/multi-account-budget-patterns.md).
Load on demand for fleet-wide budget enforcement.

### Step 12: Cost allocation tag enforcement (BEFORE budget)

Step 12 tag-activation verification and activation commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before creating any tag-scoped budget.

### Step 13: Forecast-based proactive action

Step 13 forecast-notification create-budget CLI and rule of thumb moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when configuring FORECASTED thresholds.

### Step 14: Budget vs Cost Anomaly Detection — complementary use

Step 14 Budgets-vs-CAD comparison table and complementary pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when deciding between Budgets, CAD, or both.

### Step 15: Budget rollover / reset semantics

Step 15 DynamoDB rollover Lambda pattern moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a budget must carry forward unused spend.

## STRICT output contract

Every budget action design MUST emit a single block using these literal
labels, in this order. Do NOT substitute markdown headings or camelCase
variants — assertion-based evals and downstream provisioning pipelines
parse the literal labels `BUDGET:`, `VERDICT:`, `CHECKLIST:`, `GAP:`,
`TEMPLATE:`.

```text
BUDGET: <budget-name>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
CHECKLIST:
  [x] Budget type: COST | USAGE | RI_COVERAGE | RI_UTILIZATION | SAVINGS_PLANS_COVERAGE | SAVINGS_PLANS_UTILIZATION
  [x] Monthly amount: <$> <unit> (TimeUnit: MONTHLY | QUARTERLY | ANNUALLY | DAILY)
  [x] Threshold: ACTUAL <percent>% AND/OR FORECASTED <percent>% (PERCENTAGE | ABSOLUTE_VALUE)
  [x] Action: SNS_NOTIFY | SCP_DENY | IAM_RESTRICT | SSM_STOP_EC2 | LAMBDA_CUSTOM
  [x] Cost allocation tags: ACTIVATED | NOT_ACTIVATED | N/A
  [x] Multi-account scope: SINGLE | PAYER_LINKED_ACCOUNT | STACK_SET_PER_OU
  [x] Approval model: AUTOMATIC | MANUAL (start MANUAL; promote to AUTOMATIC after cycle 2)
  [x] Execution role: <arn> (trusts budgets.amazonaws.com, has organizations:AttachPolicy / iam:AttachUserPolicy)
  [x] SCP detach / IAM detach on recovery: WIRED (Lambda scheduled) | NOT WIRED
GAP: <if REVIEW_REQUIRED, the specific gap and remediation>
TEMPLATE: <CLI snippet or CloudFormation; "(held in draft)" if blocked>
```

### FORBIDDEN output patterns — NEVER

1. NEVER emit `VERDICT: AUTOMATION_DEPLOYED` while any CHECKLIST item is
   `[ ]`. Any unmet requirement forces `REVIEW_REQUIRED`.

2. NEVER recommend `Action: SCP_DENY` with `Approval model: AUTOMATIC` in
   a fresh deployment. SCP attach is irreversible until manually detached
   and a false positive locks an entire OU out of resource creation for
   5-15+ minutes. Always start `MANUAL`; promote to `AUTOMATIC` only
   after a false-positive-free cycle.

3. NEVER emit a tag-scoped budget (`CostFilters: Tag`) without verifying
   the tag is `ACTIVATED` in the Billing console. Non-activated tags
   silently match zero spend — the budget never fires and operators
   believe spend is under control.

4. NEVER combine `Access-Control-Allow-Origin: *` style wildcards in
   `CostFilters` with `ThresholdType: ABSOLUTE_VALUE` across multiple
   LinkedAccounts without recalculating per member. An absolute $10K
   threshold across 20 member accounts means $200K total exposure.

5. NEVER claim `Action: SNS_NOTIFY` is enforcement. SNS is reporting,
   not control. If the goal is prevention of further spend, the action
   MUST be `SCP_DENY`, `IAM_RESTRICT`, `SSM_STOP_EC2`, or `LAMBDA_CUSTOM`.

6. NEVER report a budget action as wired without confirming the SNS
   topic policy allows `budgets.amazonaws.com` to publish AND the
   execution role trust policy includes `budgets.amazonaws.com`. Both
   are silent-failure conditions — the budget fires, the action stays
   in `ERROR` state, and no alarm pages.

7. NEVER use `RI_COVERAGE` or `RI_UTILIZATION` budgets for cost control.
   They measure commitment performance, not spend. A 100% RI
   utilization target can be met while overall compute spend triples.

### Worked example — AUTOMATION_DEPLOYED ($10K/month cost budget at 80%, SCP deny at 100%)

```text
BUDGET: monthly-app-cost-budget
VERDICT: AUTOMATION_DEPLOYED
CHECKLIST:
  [x] Budget type: COST (unblended USD spend)
  [x] Monthly amount: 10000 USD (TimeUnit: MONTHLY, resets 1st of month)
  [x] Threshold: FORECASTED 80% (SNS notify — Slack #finops-alerts) AND ACTUAL 100% (SCP deny)
  [x] Action: SNS_NOTIFY at 80% forecast + SCP_DENY at 100% actual
  [x] Cost allocation tags: N/A (no CostFilters — budget covers whole account 111111111111)
  [x] Multi-account scope: SINGLE (account 111111111111, Org member of o-abc123def456)
  [x] Approval model: MANUAL (cycle 1 — notify-only verified; cycle 2 — IAM on CI bot verified; SCP promotes to AUTOMATIC after cycle 3)
  [x] Execution role: arn:aws:iam::111111111111:role/BudgetActionExecutionRole (trusts budgets.amazonaws.com; policy grants organizations:AttachPolicy + organizations:DetachPolicy on ou-abc-123def456)
  [x] SCP detach on recovery: WIRED (EventBridge schedule rule budget-period-reset → Lambda detach-scp-stale at 00:05 UTC on day 1)
GAP: None
TEMPLATE:
  # Budget + 80% forecast SNS notification
  aws budgets create-budget --account-id 111111111111 --budget '{"BudgetName":"monthly-app-cost-budget","BudgetLimit":{"Amount":"10000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}' \
    --notifications-with-subscribers '[{"Notification":{"NotificationType":"FORECASTED","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"},"Subscribers":[{"SubscriptionType":"SNS","Address":"arn:aws:sns:us-east-1:111111111111:budget-alerts"}]}]'

  # SCP deny at 100% ACTUAL (pre-create the SCP in Organizations first)
  aws organizations create-policy --type SERVICE_CONTROL_POLICY --name budget-breach-deny-new-resources --description "Attached when monthly-app-cost-budget breaches 100% ACTUAL" --content file://scp-deny-new-resources.json

  # Wire the budget action (ApprovalModel: MANUAL — flip to AUTOMATIC after cycle 3)
  aws budgets put-budget-action --account-id 111111111111 --budget-name monthly-app-cost-budget \
    --notification-type ACTUAL --action-type APPLY_SCP_FAMILY \
    --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
    --definition '{"ScpActionDefinition":{"PolicyId":"p-abc123def456","PolicyDocument":"{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Deny\",\"Action\":[\"ec2:RunInstances\",\"ecs:RegisterTaskDefinition\",\"lambda:CreateFunction\"],\"Resource\":\"*\"}]}"}}' \
    --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionExecutionRole --approval-model MANUAL
```


### Decision tree — budget action selection

```
Start: budget requirement
├─ Goal = notify only (no enforcement)?
│   └─ Yes → SNS_NOTIFY (create-notification + subscribe)
│            OR APPLY_SSM_ACTION for stop-instances notify-only flows
├─ Goal = enforce on a single account?
│   ├─ Is the account an Org member?
│   │   ├─ Yes → Block new resource creation?
│   │   │       ├─ Yes → APPLY_SCP_FAMILY (target = account itself or leaf OU)
│   │   │       └─ No  → APPLY_IAM_ACTION (target = CI bot user / group, not app roles)
│   │   └─ No (standalone) → APPLY_IAM_ACTION or EventBridge → Lambda
│   └─ Goal = stop running resources? → APPLY_SSM_ACTION (STOP_EC2_INSTANCES, static IDs)
├─ Goal = enforce across OU / fleet?
│   └─ StackSet to OU with APPLY_SCP_FAMILY at innermost leaf OU
└─ Budget type is RI_COVERAGE / RI_UTILIZATION / SAVINGS_PLANS_*?
    └─ Notify-only — NEVER enforcement. RI/SP budgets measure commitment,
       not spend. Wire to SNS for human review.
```

## Anti-Patterns — NEVER do these things

- NEVER wire a budget action with `ApprovalModel: AUTOMATIC` for
  SCP deny without first testing in a non-production OU. A false
  positive locks an entire OU out of resource creation; recovery
  requires manual SCP detach and propagation delay (5-15 minutes).
  Always start with `ApprovalModel: MANUAL` in production.

- NEVER assume `FORECASTED` thresholds are deterministic. AWS
  forecast models are probabilistic (80% confidence). A forecast at
  90% may fire when actual spend is only at 75%. Always pair forecast
  with a higher actual threshold to avoid premature enforcement.

- NEVER scope a budget by `CostFilters: Tag` without verifying the
  tag is activated. Tag-scoped budgets against non-activated tags
  silently match zero spend — the budget never fires and operators
  believe their spend is under control.

- NEVER use a budget as the only enforcement for unexpected spend
  spikes. Budgets evaluate every 8-12 hours and depend on CE data
  that lags 12-24 hours. For real-time spike detection, use Cost
  Anomaly Detection (Step 14) wired to a different SNS topic.

- NEVER forget the SCP detach step on budget recovery. The
  `put-budget-action` API attaches the SCP on breach but does NOT
  detach it when the budget resets next period. Wire a Lambda
  (EventBridge on `ResetPeriod` event) or a monthly scheduled
  Lambda to detach stale SCPs.

- NEVER omit the SNS topic access policy for `budgets.amazonaws.com`.
  A topic created via `sns create-topic` with the default policy
  does NOT allow Budgets to publish. Silent notification failure is
  the most common "budget didn't fire" root cause.

- NEVER attach an IAM policy via budget action to a role used by an
  application. The restricted policy applies immediately on breach
  and breaks the application. Target users (CI bots) or groups, not
  roles in active use.

- NEVER assume a payer-side budget cascades to member accounts.
  Budgets are per-account. For per-member enforcement, use
  `CostFilters: LinkedAccount` from the payer or deploy via
  CloudFormation StackSet to each member.

- NEVER use SSM Action (`APPLY_SSM_ACTION`) for production EC2 stop
  without testing idempotency. The action stops instances on every
  budget evaluation (8-12 hours) while the threshold is breached.
  Instances restarted by an autoscaler will be stopped again. Wire
  a state flag (SSM Parameter) to make the action idempotent.

- NEVER trust budget data for same-day decisions. CE data lags
  12-24 hours. A "real-time" dashboard built on Budgets data
  presents yesterday's spend as today's. Use the Cost and Usage
  Report (CUR) with hourly granularity for near-real-time.

- NEVER create a budget without `describe-budgets` first. Multiple
  teams creating budgets with the same name silently overwrite each
  other — Budgets does NOT enforce uniqueness across
  `Notification`/`Action` configs, only across `BudgetName`.

- NEVER rely on `ThresholdType: ABSOLUTE_VALUE` for multi-account
  budgets without recalculating per member. An absolute $10K
  threshold against 20 member accounts means each member can spend
  $10K (total $200K) — not what most operators expect.

- NEVER wire EventBridge → Lambda budget actions without a DLQ.
  Budget notification events that fail Lambda invocation are
  dropped silently. A missing DLQ produces silent enforcement
  failure.

- NEVER use RI Coverage or RI Utilization budgets for cost control.
  They measure commitment performance, not spend. A 100% RI
  utilization budget can be met while overall compute spend triples
  if the workload grows faster than the RI commitment.

- NEVER enable a budget action in production without verifying the
  execution role trust policy includes `budgets.amazonaws.com`. A
  role that trusts only `ec2.amazonaws.com` or `lambda.amazonaws.com`
  will silently fail to assume — the action stays in `ERROR` state.

- NEVER confuse `APPLY_SCP_FAMILY` (newer API) with the deprecated
  `APPLY_POLICY`. Both attach SCPs, but the API surface differs.
  Stick with `APPLY_SCP_FAMILY` for new code; `APPLY_POLICY` may
  not be supported on newer API versions.

- NEVER forget budget action status checks post-deploy.
  `describe-budget-action-histories` shows the action execution
  history; an action in `EXECUTED` state means it fired. Without
  this check, a misconfigured budget can breach for months with
  no enforcement.

## Pre-flight safety checks (run before applying any budget CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing
  operation (`put-budget-action`, `create-budget`, attaching SCPs,
  modifying the SNS topic policy), emit:
  `CONFIRM: About to <action> for budget <budget> in account
  <account>. This affects <consequence>. Proceed? (yes/no)`

- **Back up the current budget configuration** before modifying:
  `aws budgets describe-budget --account-id <id> --budget-name <name> > /tmp/<name>-backup-$(date +%s).json`

- **Before enabling `ApprovalModel: AUTOMATIC` for SCP**, dry-run
  the SCP in a non-production OU for at least one full budget cycle
  (monthly). Verify the SCP attaches, blocks the expected actions,
  and detaches correctly on budget reset.

- **Before deploying a multi-account budget StackSet**, validate
  the CloudFormation template:
  `aws cloudformation validate-template --template-body file://budget-template.yaml`

- **For cost-allocation-tag-scoped budgets**, verify tag activation
  with `ce get-cost-and-usage --group-by Type=TAG,Key=<key>` BEFORE
  creating the budget. Activated tags return data rows; non-activated
  return only `$NULL`.

## Appendix A — Common budget action types (summary)

Appendix A summary table moved verbatim to [references/budget-action-types.md](references/budget-action-types.md).
Load on demand when picking an action type — the full parameter contract is in the same file.

## Appendix B — Decision tree (which action type)

Appendix B action-type decision tree moved verbatim to [references/budget-action-types.md](references/budget-action-types.md).
Load on demand when choosing between SNS, IAM, SCP, SSM, and Lambda actions.

## Recent AWS features (2024-2026)

Recent AWS features 2024-2026 (SSM action, APPLY_SCP_FAMILY rename, CostFilters enhancements, CAD weekly subscriptions, EventBridge detail enrichment) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when checking feature availability windows.

## Expert heuristic: budget enforcement blast radius

Blast-radius heuristic, scoping techniques, 3-cycle validation protocol, CloudFormation pattern, and post-deploy detection alarms moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before recommending SCP enforcement or promoting an action to AUTOMATIC.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples and full CLI payloads: the Step 4, 5, 6 and 13 walkthroughs and the REVIEW_REQUIRED example moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 expert knowledge, EventBridge/Lambda, SSM stop, tagging, Slack and rollover patterns (Steps 7-10, 15), Budgets-vs-CAD (Step 14), blast-radius heuristic, and Recent AWS features moved from SKILL.md.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — cost-allocation tag activation check and activation commands (Step 12) moved from SKILL.md.
- [references/budget-action-types.md](references/budget-action-types.md) — action-type matrix and parameter contracts; now also holds the Appendix A summary table and Appendix B decision tree moved from SKILL.md.
- [references/multi-account-budget-patterns.md](references/multi-account-budget-patterns.md) — multi-account architectures; now also holds the Step 11 payer/StackSet walkthrough moved from SKILL.md.

## Domain

AWS CloudOps / FinOps Automation — Budget-driven enforcement.

## AWS documentation

- **AWS Budgets** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- **Budget Actions** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html
- **Cost Anomaly Detection** — https://docs.aws.amazon.com/cost-management/latest/userguide/manage-anomalies.html
- **Organizations SCPs** — https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps.html
- **Cost Allocation Tags** — https://docs.aws.amazon.com/cost-management/latest/userguide/alloc-tags.html
