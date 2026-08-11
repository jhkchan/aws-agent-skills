---
name: budget-deployer
description: >-
  Provisions AWS Budgets and Cost Anomaly Detection with production
  defaults: cost budgets (fixed/threshold, actual vs forecast alerts),
  usage budgets (RI/SP utilization, RI/SP coverage), cost anomaly
  detection (service monitors, subscriptions), budget actions
  (apply/remove IAM policy, stop EC2/RDS, SNS), threshold tiering
  (80/90/100%), cost filters (service, linked account, tag, region).
  Emits READY_TO_DEPLOY | PREREQUISITES_MISSING. Use when creating a
  budget, configuring budget actions, hardening spend guardrails on a
  new account, setting RI/SP utilization targets, or wiring cost
  anomaly subscriptions.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). For live deployment: AWS CLI v2 with budgets, ce, sns, iam,
  sts, and ec2 access. Works with Terraform aws_budgets_budget,
  aws_ce_anomaly_monitor, and aws_sns_topic resources and
  CloudFormation AWS::Budgets::Budget templates.
keywords:
  - aws
  - budgets
  - cloudops
  - deploy
  - provisioning
  - cost budget
  - usage budget
  - ri utilization
  - ri coverage
  - savings plan
  - savings plan utilization
  - savings plan coverage
  - cost anomaly detection
  - budget actions
  - iam policy apply
  - ec2 stop
  - sns notification
  - forecast
  - actual
  - threshold
  - cost filters
  - linked account
  - consolidated billing
tags:
  - aws
  - budgets
  - cloudops
  - deploy
  - finops
  - provisioning
  - cost-budget
  - usage-budget
  - ri-utilization
  - savings-plan
  - anomaly-detection
  - budget-actions
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: FinOps
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - budgets
    - cloudops
    - deploy
    - finops
    - provisioning
    - cost-budget
    - usage-budget
    - ri-utilization
    - savings-plan
    - anomaly-detection
    - budget-actions
  dependencies:
    - aws-orchestrator
  keywords:
    - create aws budget
    - provision budget
    - cost budget
    - usage budget
    - ri utilization budget
    - savings plan utilization
    - savings plan coverage
    - cost anomaly detection
    - budget actions
    - budget alert
    - sns notification
    - threshold
    - forecast
    - cost filters
    - linked account filter
  when_to_use: >-
    Invoke when the user wants to create an AWS Budget (cost, usage, RI
    utilization, RI coverage, Savings Plan utilization, Savings Plan
    coverage), configure Budget Actions (apply/remove IAM policy, stop EC2,
    SNS), enable Cost Anomaly Detection with subscriptions and monitors,
    wire SNS notifications for budget alerts, scope a budget to a linked
    account / service / tag / region, or generate provisioning CLI commands
    / IaC templates for spend guardrails. Do NOT invoke for auditing
    existing budgets posture (use budgets-auditor), or for Cost Explorer
    forecast analysis without a deployment intent.
---

# AWS Budget Deployer

An AWS CloudOps agent skill that provisions AWS Budgets and Cost Anomaly
Detection with correct defaults. The skill walks the operator through a
10-step provisioning procedure, captures the operator's spend-model
decisions (budget type, scope, thresholds, action tier), explains why
each default matters, and emits a READY_TO_DEPLOY checklist with
copy-pasteable verification commands.

## What this skill does

Provisions AWS Budgets and Cost Anomaly Detection with production-grade
defaults: cost budgets (fixed amount or zero-spend), usage budgets (RI /
Savings Plan utilization and coverage), cost anomaly detection monitors,
budget alerts on actual vs forecast spend at configurable thresholds, and
budget actions that apply/remove an IAM policy, stop EC2/RDS instances,
or publish to SNS when a threshold is breached.

## Activation

Trigger phrases: "create budget", "provision AWS Budget", "cost budget",
"usage budget", "RI utilization budget", "RI coverage budget", "Savings
Plan utilization", "Savings Plan coverage", "cost anomaly detection",
"budget actions", "apply IAM policy on budget breach", "stop EC2 on
budget", "SNS budget notification", "budget threshold alert", "zero
spend budget", "linked account budget".

## Invocation contract (hard requirement)

When this skill is invoked with a budget-provisioning request, the agent
MUST respond with the READY_TO_DEPLOY checklist defined in §"Output
format" using the literal all-caps labels `BUDGET:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

## Mindset

**One-line takeaway:** a budget without a notification or action is
silent. AWS Budgets does not push alerts unless an explicit notification
is attached; Cost Anomaly Detection does not alert unless an explicit
subscription exists. The provisioning procedure treats the
notification/action/subscription as the load-bearing part of the
deployment — the budget definition itself is the easy part.

Three misconceptions dominate budget misconfiguration at provisioning
time:

- **"A budget alerts me automatically when spend crosses the threshold."**
  It does not. `create-budget` defines the threshold; you MUST call
  `create-notification` separately to attach an SNS notification, email,
  or Slack destination. Operators frequently create budgets via the
  console wizard (which silently attaches a default notification) and
  then assume `create-budget` via CLI does the same. It does not — the
  CLI path requires an explicit `create-notification`.

- **"Budget actions fire automatically on any breach."** Budget actions
  (apply/remove IAM policy, stop EC2 instances, SNS) require a separate
  `create-budget-action` call AND an IAM role that trusts
  `budgets.amazonaws.com` with a permission policy granting the action.
  Without the role, `create-budget-action` returns
  `InvalidParameterException`. The role is the most commonly missed
  prerequisite.

- **"Cost Anomaly Detection is enabled by default."** It is not. The
  service-wide monitor must be created (`create-anomaly-monitor`) and a
  subscription (`create-anomaly-subscriptions`) must be attached with an
  SNS topic or email root. Without the subscription, anomalies are
  visible in the console but never alerted on.

## Quick navigation

- **Step 0** — Capture intent (budget type, scope, amount, action tier).
- **Step 1** — Choose budget type (cost vs usage vs anomaly).
- **Step 2** — Choose scope (payer, linked account, service, tag, region).
- **Step 3** — Cost budget: amount, time period, unit.
- **Step 4** — Usage budget: RI/SP utilization vs coverage.
- **Step 5** — Cost anomaly detection: monitor + subscription.
- **Step 6** — Alerts: actual vs forecast, threshold percentages.
- **Step 7** — Budget actions: IAM, EC2 stop, SNS — gated by IAM role.
- **Step 8** — SNS topic + subscription + Budgets IAM policy.
- **Step 9** — Cost filters: service, linked account, tag, region.
- **Step 10** — Verification commands.

## STRICT output contract

Every response MUST begin with this block — no preamble, no
conversational opening:

```text
BUDGET: <budget name> in <account / payer scope>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Budget type: COST | RI_UTILIZATION | RI_COVERAGE | SP_UTILIZATION | SP_COVERAGE | ANOMALY
  [✓|✗] Scope: <account | linked account | service | tag | region>
  [✓|✗] Amount / target: <$amount or % utilization>
  [✓|✗] Time period: MONTHLY | QUARTERLY | ANNUALLY | DAILY
  [✓|✗] Alerts: <list with threshold %, ACTUAL|FORECAST, SNS topic>
  [✓|✗] Budget actions: <list with threshold %, action type, target>
  [✓|✗] SNS topic + subscription + IAM policy: <verified | missing>
  [✓|✗] Cost anomaly subscription: <monitor + subscription + SNS>
  [✓|✗] Cost filters: <service | linked account | tag | region>
VERIFICATION_COMMANDS:
  aws budgets describe-budget --account-id <id> --budget-name <name>
  aws budgets describe-notifications-for-budget ...
  aws budgets describe-budget-actions ...
  aws ce get-anomaly-subscriptions ...
  aws sns get-topic-attributes --topic-arn <arn>
```

### FORBIDDEN output patterns

- NEVER start with "Let me set up…" or "I'll create…" — the BUDGET line
  is the FIRST line, always. No conversational preamble.
- NEVER use lowercase verdict values — emit `READY_TO_DEPLOY` or
  `PREREQUISITES_MISSING`.
- NEVER emit a budget without at least one notification, an action, or
  an explicit "no notification configured" note. A budget without
  notifications is silent spend.
- NEVER recommend an IAM policy/EC2 stop budget action without first
  verifying the action role exists and trusts the Budgets service
  principal.
- NEVER declare `READY_TO_DEPLOY` for a budget action that targets a
  resource outside the budget's scope (e.g., stopping an EC2 instance in
  a linked account while the budget is scoped to the payer).

## Cost Budgets vs Usage Budgets vs Anomaly Detection — decision tree

| Signal in the prompt | Provisioning path |
|---|---|
| "monthly spend limit", "fixed budget amount", "we don't want to exceed $X" | **COST budget** — Step 3 |
| "RI utilization target", "we should be using our reservations" | **USAGE budget** (`RI_UTILIZATION`) — Step 4 |
| "RI coverage target", "% of compute covered by RI" | **USAGE budget** (`RI_COVERAGE`) — Step 4 |
| "Savings Plan utilization", "are we using our SP commitment" | **USAGE budget** (`SP_UTILIZATION`) — Step 4 |
| "Savings Plan coverage", "% of spend covered by SP" | **USAGE budget** (`SP_COVERAGE`) — Step 4 |
| "unusual spend spike", "anomalous cost", "detect outliers" | **ANOMALY DETECTION** — Step 5 |
| "zero spend budget", "new account guardrail" | **COST budget**, amount=$0.01, ACTUAL 100% — Step 3 |
| "stop EC2 instances when budget breached" | **COST budget** + **budget action** (`APPLY_IAM_POLICY` or `RUN_SSM_DOCUMENTS`) — Step 7 |

**Precedence rule.** When both a budget and anomaly detection are
requested, provision the budget first (it has the harder prerequisites —
SNS, IAM role for actions) and the anomaly subscription second (it can
share the SNS topic).

## Budget configuration dependency graph

| Configuration | Hard dependencies | Silent failure | Enables downstream |
|---|---|---|---|
| Budget definition | none — `create-budget` argument | exists silently if no notification attached | notifications, actions |
| Notification | budget exists; SNS topic exists for SNS-type | email-not-verified SNS subscription silently drops messages | email/SNS/Slack alerting |
| Budget action (IAM/EC2/SNS) | budget exists; **IAM role trusting `budgets.amazonaws.com`** with required permissions | `create-budget-action` fails with `InvalidParameterException` if the role is missing or lacks trust policy | IAM policy apply/remove, EC2 stop, SNS |
| IAM action role | trust policy `Principal: Service: budgets.amazonaws.com` + permission policy for the target action | role with trust on `sts:AssumeRole` only (no `Service` principal) silently fails at action execution | budget actions |
| SNS topic for budget alerts | topic exists in same account + region; key policy allows `events.amazonaws.com` and/or `budgets.amazonaws.com` | SNS topic with server-side encryption (SSE-KMS) but no key policy for Budgets silently drops notifications | email, Lambda, HTTPS endpoints |
| Cost anomaly monitor | `create-anomaly-monitor` (`DIMENSIONAL` for service-level or `CUSTOM`) | monitor exists but produces no alerts without a subscription | anomaly subscription |
| Cost anomaly subscription | monitor exists; SNS topic or root email configured | SNS topic without key policy for `ce.amazonaws.com` silently drops anomaly alerts | anomaly SNS/email alerting |
| Cost filter (Dimensions) | `BudgetType=COST` or `USAGE` | filter on `LINKED_ACCOUNT` only works on payer accounts | scoped budget per service/account/tag/region |

**The action role and the SNS key policy are the two prerequisites a
baseline model misses.** The procedure below forces an explicit check on
both before any `create-budget-action` call.

**Cross-dependency gotchas:**

- A budget action targeting a linked account requires the action role
  in THAT linked account, not the payer. A common error is provisioning
  the role in the payer and expecting it to apply an IAM policy to an
  IAM principal in a linked account.
- SNS topics with SSE-KMS will silently drop notifications from Budgets
  unless the KMS key policy grants `kms:GenerateDataKey*` and
  `kms:Decrypt` to `budgets.amazonaws.com` and
  `ce.amazonaws.com`. AWS-managed KMS keys (`alias/aws/sns`) work
  out-of-the-box.
- Budget notifications on `FORECAST` alerts fire earlier than `ACTUAL`
  but forecast is a trailing model — it is less accurate in the first
  ~14 days of a budget period.
- Usage budgets (RI/SP utilization/coverage) do NOT support budget
  actions — only SNS/email/Slack notifications. Do not attempt to wire
  an IAM policy/EC2 stop action on a usage budget; the API rejects it.

## Expert heuristic: threshold tiering for cost budgets

A baseline model attaches a single 100% threshold and moves on. That
gives the operator zero lead time to react. Use the **80 / 90 / 100**
tiering rule for production cost budgets:

```text
threshold_tier = {
  "80% ACTUAL":   "early warning — operator still has 20% of budget to react",
  "90% ACTUAL":   "urgent — reaction window closing; pre-approve remediation",
  "100% ACTUAL":  "breach — invoice will exceed budget; investigate root cause",
  "100% FORECAST":"predictive — AWS forecast model predicts end-of-period breach",
}
```

**Why FORECAST matters:** a budget set to $10,000/month that is on pace
for $13,000 by day 20 will trigger a `100% FORECAST` notification around
day 14-18, while the `100% ACTUAL` notification only fires around day
24-26. The 6-10 day lead time is the difference between "rightsize now"
and "explain the overage next month".

**Zero-spend accounts** (sandbox, security-audit, break-glass) need a
different pattern: `$0.01` budget amount, `ACTUAL > 50%` threshold, SNS
to security/FinOps. A 50% threshold on a $0.01 budget fires on the first
dollar. Never set a $0 budget; the API rejects it.

**Action tier recommendation:**

| Action | Threshold | Use case |
|---|---|---|
| SNS only | 80% / 90% ACTUAL | All budgets — non-destructive, lets operator investigate |
| SNS + APPLY_IAM_POLICY | 100% ACTUAL | Sandbox/dev accounts — restrict further spend by denying `*:*` on non-essential services |
| SNS + RUN_SSM_DOCUMENTS (EC2 stop) | 100% ACTUAL | Test environments where stop is acceptable; **never** on production |
| REMOVE_IAM_POLICY | 100% ACTUAL | Reverse a previous `APPLY_IAM_POLICY` action when budget resets |

**Critical:** budget actions are scoped per budget. A single budget can
have multiple actions at different thresholds.

## Expert heuristic: anomaly detection sensitivity tuning

Cost Anomaly Detection uses a machine-learning model on your historical
Cost Explorer usage data. The model needs **at least ~30 days** of
history before its predictions are reliable. Three configuration choices
dominate false-positive rates:

- **`Feedback` API (`put-feedback`)**: the model does NOT auto-learn
  from SNS-dismissed alerts. You must explicitly call
  `aws ce put-feedback --anomaly-id <id> --is-anomaly NO` to suppress a
  false positive. Operators frequently mark alerts as "not an anomaly"
  in the console but do not realize the model only updates via
  `put-feedback`. Plan for this in the runbook.
- **Subscription `Threshold`**: the dollar amount above which an
  anomaly is published to SNS. Default is `$0`. **Always set a
  threshold** (typical: `$100` or `$1000` depending on total account
  spend). A `$0` threshold produces daily noise from minor variances.
- **Monitor `MonitorSpecification`**: a service-scoped monitor
  (`Dimension=SERVICE`) gives cleaner signals than the default
  account-wide monitor. For multi-service accounts, provision per-
  service dimensional monitors rather than relying on the
  account-wide one.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a specific
gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account ID (payer or standalone) | Budgets are scoped per account; payer covers linked | `aws sts get-caller-identity --query Account --output text` |
| Region (Budgets API is `us-east-1`) | SNS topics should be in `us-east-1` for lowest latency | `aws configure get region` |
| SNS topic ARN + policy allowing `budgets.amazonaws.com` Publish | Budgets calls `sns:Publish`; topic policy must allow it | `aws sns get-topic-attributes --topic-arn <arn> --query 'Attributes.Policy'` |
| KMS key policy for encrypted SNS topic (if SSE-KMS) | CMK must grant `kms:GenerateDataKey*` to `budgets.amazonaws.com` and `ce.amazonaws.com` | `aws kms get-key-policy --key-id <cmk-id> --policy-name default` |
| Budget action role with trust on `budgets.amazonaws.com` | Budget Actions require an assumable role | `aws iam get-role --role-name <name> --query 'Role.AssumeRolePolicyDocument'` |
| Email address confirmed (for email notifications) | Email subscriptions require confirmation | `aws sns list-subscriptions-by-topic --topic-arn <arn>` |
| Payer access for linked-account budgets | Linked-account filters require Cost Explorer | `aws ce get-dimension-values --dimension LINKED_ACCOUNT --time-period ...` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 10-step provisioning procedure

### Step 0 — Capture intent (scope and amount)

Before any CLI call, confirm: budget type (cost / RI util / RI coverage
/ SP util / SP coverage / anomaly); scope (whole account / linked
account / service / tag / region); amount (dollars for cost, percent for
usage); time period (MONTHLY default); action tier (notify-only SNS /
SNS+IAM policy / SNS+EC2 stop / SNS+IAM removal); thresholds (80/90/100
recommended for production; 50/100 for sandbox; 100+forecast for
budget-at-risk).

If the operator has not specified these, emit
`VERDICT: PREREQUISITES_MISSING` with the missing inputs list.

### Step 1 — Choose budget type

| Need | BudgetType | Spec field |
|---|---|---|
| Fixed dollar spend limit | `COST` | `Budget.BudgetLimit.Amount` + `.Unit` |
| Zero-spend guardrail | `COST` | `Budget.BudgetLimit.Amount=0.01, Unit=USD` |
| RI utilization target | `RI_UTILIZATION` | `Budget.BudgetLimit.Amount=80, Unit=PERCENTAGE` |
| RI coverage target | `RI_COVERAGE` | `Budget.BudgetLimit.Amount=80, Unit=PERCENTAGE` |
| SP utilization target | `SP_UTILIZATION` | `Budget.BudgetLimit.Amount=80, Unit=PERCENTAGE` |
| SP coverage target | `SP_COVERAGE` | `Budget.BudgetLimit.Amount=80, Unit=PERCENTAGE` |
| Outlier detection (no threshold) | (anomaly monitor, not a budget) | `create-anomaly-monitor` (Step 5) |

`BudgetType` and `BudgetLimit` are mutable via `update-budget`; `TimeUnit`
(MONTHLY / DAILY / QUARTERLY / ANNUALLY) is mutable.

### Step 2 — Choose scope (CostFilters)

Use `CostFilters` in the budget definition to scope the budget. Filters
are additive (AND semantics).

| Filter dimension | Key in CostFilters | Example | Notes |
|---|---|---|---|
| Linked account | `LinkedAccount` | `["123456789012"]` | Only works from the payer |
| Service | `Service` | `["Amazon Elastic Compute Cloud - Compute"]` | Use Cost Explorer service names, not CLI names |
| Tag | `TagKeyValue` | `["Environment$production"]` | Format `key$value`; tag must be activated in Cost Explorer |
| Region | `Region` | `["US East (N. Virginia)"]` | Use Region display names |
| AZ | `AZ` | `["us-east-1a"]` | Rarely used |
| PurchaseType | `PurchaseType` | `["Reserved Instances"]` | For RI-related budgets |

**Common mistake:** using AWS CLI service names (`ec2`) instead of Cost
Explorer service names (`Amazon Elastic Compute Cloud - Compute`). Verify
with `aws ce get-dimension-values --dimension SERVICE`.

**Tag activation prerequisite:** tag-based filters require the tag key
to be activated in Billing → Cost Allocation Tags. Allow ~24 hours for
propagation.

### Step 3 — Cost budget configuration (amount + time period + unit)

```bash
aws budgets create-budget \
  --account-id 111111111111 \
  --budget '{"BudgetName":"prod-monthly-cost","BudgetLimit":{"Amount":"10000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST","CostFilters":{"Service":["Amazon Elastic Compute Cloud - Compute"]},"CostTypes":{"IncludeTax":true,"IncludeSubscription":true,"UseBlended":false,"IncludeRefund":false,"IncludeCredit":true,"IncludeUpfront":true,"IncludeRecurring":true,"IncludeOtherSubscription":true,"IncludeSupport":true,"IncludeDiscount":true,"UseAmortized":false}}'
```

**CostTypes defaults:** `IncludeTax=true` (tax is on the invoice);
`IncludeSubscription=true` (Support, Marketplace); `UseBlended=false`
(Blended averages across linked accounts, masking overages);
`UseAmortized=false` for budget alerts, `true` for amortized RI/SP
analysis — pick one consistently.

**Zero-spend guardrail** (sandbox / new account): `BudgetLimit.Amount=0.01`,
`Unit=USD`. Then attach `ACTUAL > 50%` to SNS — a 50% threshold on a
$0.01 budget fires on the first dollar.

### Step 4 — Usage budget configuration (RI/SP utilization/coverage)

```bash
# RI Utilization budget — alert when RI utilization drops below 80%
aws budgets create-budget --account-id 111111111111 \
  --budget '{"BudgetName":"ri-utilization-target","BudgetLimit":{"Amount":"80","Unit":"PERCENTAGE"},"TimeUnit":"MONTHLY","BudgetType":"RI_UTILIZATION"}'
# Savings Plan Coverage budget (latest GA feature) — same pattern with BudgetType SP_COVERAGE
```

**Usage budget constraints:** Usage budgets (`RI_*`, `SP_*`) do NOT
support budget actions (IAM/EC2/SSM). Only SNS/email/Slack
notifications. Set `ComparisonOperator` to `LESS_THAN_THRESHOLD` for
utilization/coverage targets — alerts fire when actual drops below the
target.

### Step 5 — Cost Anomaly Detection (monitor + subscription)

Cost Anomaly Detection is **separate from AWS Budgets** — it is a Cost
Explorer (CE) API. Provisioning requires two API calls.

```bash
# Service-level monitor (recommended over default account-wide)
aws ce create-anomaly-monitor \
  --anomaly-monitor '{"Name":"service-anomaly-monitor","Type":"DIMENSIONAL","MonitorDimension":"SERVICE"}'

# Subscription to SNS — anomaly > $100 publishes to topic
aws ce create-anomaly-subscription \
  --anomaly-subscription '{"Name":"prod-anomaly-subscription","Frequency":"DAILY","Threshold":100.0,"MonitorArn":"arn:aws:ce::111111111111:anomaly-monitor/default","Subscribers":[{"Address":"arn:aws:sns:us-east-1:111111111111:cost-anomaly-alerts","Type":"SNS"}]}'
```

The default account-wide monitor ARN is
`arn:aws:ce::<account-id>:anomaly-monitor/default`. Dimensional monitors
must be explicitly created. The topic policy must allow
`Principal: Service: ce.amazonaws.com` to `sns:Publish` — this is a
**different principal** from Budgets. Operators frequently reuse a
Budgets SNS topic for anomalies and wonder why anomaly alerts never
fire — the topic policy lacks the `ce.amazonaws.com` principal.
Frequency: `IMMEDIATE` (noisy); `DAILY` (batched, recommended);
`WEEKLY` (slow).

### Step 6 — Budget alerts (actual vs forecast, threshold percentages)

```bash
# 80% ACTUAL — early warning (repeat for 90, 100; add 100% FORECAST)
aws budgets create-notification \
  --account-id 111111111111 --budget-name "prod-monthly-cost" \
  --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=arn:aws:sns:us-east-1:111111111111:budget-alerts,Type=SNS
```

**Threshold types:** `PERCENTAGE` (relative to `BudgetLimit`, default)
or `ABSOLUTE_VALUE` (explicit dollar amount). Use `ABSOLUTE_VALUE` when
the threshold should not change if the budget limit changes.

**Actual vs Forecast:** `ACTUAL` is definitive; `FORECAST` is predictive
(uses trailing ~30 days). Pair them — forecast alone is unreliable in
the first 14 days of a budget period. **Usage budgets (RI_*, SP_*)**
support `ACTUAL` only — `FORECAST` is rejected by the API for non-COST
budget types.

### Step 7 — Budget actions (IAM policy / EC2 stop / SNS)

Budget actions require an **IAM role** that trusts `budgets.amazonaws.com`
and has permission for the action. This is the most commonly missed
prerequisite.

**IAM role template (trust + permission policy for APPLY_IAM_POLICY):**

```bash
# Trust policy MUST have Principal: Service: budgets.amazonaws.com
cat > /tmp/budget-actions-trust.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow",
"Principal":{"Service":"budgets.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF
# Permission policy grants: iam:AttachUserPolicy, iam:AttachRolePolicy,
# iam:DetachUserPolicy, iam:DetachRolePolicy, iam:ListAttached*Policies
aws iam create-role --role-name BudgetActionsRole \
  --assume-role-policy-document file:///tmp/budget-actions-trust.json
```

**Create the action — APPLY_IAM_POLICY at 100% ACTUAL:**

```bash
aws budgets create-budget-action \
  --account-id 111111111111 --budget-name "prod-monthly-cost" \
  --notification-type ACTUAL --action-type APPLY_IAM_POLICY \
  --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
  --definition '{"IamActionDefinition":{"PolicyArn":"arn:aws:iam::111111111111:policy/BudgetDenyAll","Roles":["SandboxAppRole"]}}' \
  --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionsRole \
  --approval-model AUTOMATIC
```

For EC2 stop, use `--action-type RUN_SSM_DOCUMENTS` with
`SsmActionDefinition.ActionSubType=STOP_EC2_INSTANCES` (or
`STOP_RDS_INSTANCE` for non-prod databases, 2024 GA).

**Action types:** `APPLY_IAM_POLICY` (attach policy to principals),
`REMOVE_IAM_POLICY` (detach — reverse an APPLY when budget resets),
`RUN_SSM_DOCUMENTS` (run SSM doc: `STOP_EC2_INSTANCES` /
`STOP_RDS_INSTANCE`).

**`ApprovalModel`:** `AUTOMATIC` (sandbox/dev — action fires on breach)
or `MANUAL` (production — requires human approval in the console).

**Cross-account constraint:** the `ExecutionRoleArn` MUST be in the same
account as the target resource. For a budget on a linked account that
stops EC2 in that linked account, the role must exist in the linked
account, not the payer.

### Step 8 — SNS topic + subscription + IAM policy

The SNS topic is the alerting backbone for both Budgets and Cost
Anomaly Detection. Provision it in `us-east-1`.

```bash
TOPIC_ARN=$(aws sns create-topic --name budget-alerts --region us-east-1 --query TopicArn --output text)

# Topic policy MUST allow BOTH budgets.amazonaws.com AND ce.amazonaws.com
cat > /tmp/budget-topic-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": ["budgets.amazonaws.com", "ce.amazonaws.com"]},
    "Action": "sns:Publish",
    "Resource": "$TOPIC_ARN"
  }]
}
EOF
aws sns set-topic-attributes --topic-arn "$TOPIC_ARN" \
  --attribute-name Policy --attribute-value file:///tmp/budget-topic-policy.json

aws sns subscribe --topic-arn "$TOPIC_ARN" --protocol email \
  --notification-endpoint finops@example.com
```

**Encrypted topic caveat:** if the topic uses SSE-KMS with a customer
CMK, the KMS key policy MUST grant `kms:GenerateDataKey*` and
`kms:Decrypt` to BOTH `budgets.amazonaws.com` and `ce.amazonaws.com`.
AWS-managed `alias/aws/sns` works out-of-the-box. Customer CMK without
the grant silently drops notifications — no error, no log. Email
subscriptions require the recipient to confirm; until confirmed,
`list-subscriptions-by-topic` shows `PendingConfirmation`.

### Step 9 — Cost filters (service / linked account / tag / region)

(See Step 2 for the full CostFilters reference.) Common patterns:

| Pattern | CostFilters JSON |
|---|---|
| Payer-wide budget (no filter) | omit `CostFilters` |
| Per linked account | `{"LinkedAccount": ["123456789012"]}` |
| EC2 only | `{"Service": ["Amazon Elastic Compute Cloud - Compute"]}` |
| Production-tagged resources | `{"TagKeyValue": ["Environment$production"]}` |
| Multi-region | `{"Region": ["US East (N. Virginia)", "EU (Ireland)"]}` |
| RI spend only | `{"PurchaseType": ["Reserved Instances"]}` |

Always verify dimension values before deploying:
`aws ce get-dimension-values --dimension SERVICE --time-period ...`.

### Step 10 — Verification

```bash
aws budgets describe-budget --account-id 111111111111 --budget-name prod-monthly-cost
aws budgets describe-notifications-for-budget --account-id 111111111111 --budget-name prod-monthly-cost
aws budgets describe-budget-actions --account-id 111111111111 --budget-name prod-monthly-cost
aws budgets describe-budget-action-executions --account-id 111111111111 \
  --budget-name prod-monthly-cost \
  --time-period Start=2026-08-01T00:00:00Z,End=2026-08-10T23:59:59Z
aws ce get-anomaly-monitors
aws ce get-anomaly-subscriptions
aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts
aws sns list-subscriptions-by-topic --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts
```

## NEVER do these things (top)

1. **NEVER create a budget without at least one notification, action, or
   explicit "no notification" note.** `create-budget` alone does NOT
   alert. Without a `create-notification` call, the budget is silent
   spend — the operator will not learn about a breach until the invoice
   arrives. The CLI path is the most common source of this mistake
   because the console wizard attaches a default notification
   implicitly.

2. **NEVER provision a budget action (IAM/EC2/SSM) without first
   verifying the ExecutionRoleArn exists and trusts
   `budgets.amazonaws.com`.** Budget Actions cannot assume an arbitrary
   role. The role trust policy MUST have
   `Principal: Service: budgets.amazonaws.com` with `sts:AssumeRole`.
   A role that trusts only an IAM user or another role will fail at
   execution time, not at create time.

3. **NEVER attach budget actions to usage budgets (RI_*, SP_*).** The
   API rejects this. Usage budgets support notifications only — no
   IAM/EC2/SSM action. Use a separate COST budget if you need an action
   tier on Reserved Instance or Savings Plan commitments.

4. **NEVER reuse a Budgets SNS topic for Cost Anomaly Detection without
   adding `ce.amazonaws.com` to the topic policy.** Budgets publishes
   as `budgets.amazonaws.com`; Cost Explorer publishes as
   `ce.amazonaws.com`. A topic policy that allows only
   `budgets.amazonaws.com` silently drops anomaly alerts — no error, no
   CloudTrail event for the publish.

5. **NEVER deploy a customer-CMK-encrypted SNS topic for Budgets or
   Anomaly alerts without granting `kms:GenerateDataKey*` and
   `kms:Decrypt` to `budgets.amazonaws.com` and `ce.amazonaws.com` in
   the key policy.** AWS-managed `alias/aws/sns` works out-of-the-box;
   customer CMKs do not. Symptom: no alerts delivered, no error logged.

(Additional: never set `BudgetLimit.Amount=0` — API rejects; use `0.01`
for zero-spend. Never use `FORECAST` notifications on usage budgets —
API rejects. Never assume email SNS subscriptions are active without
confirmation. Never set `BudgetLimit.Amount` < 0.01.)

## Output format

```text
BUDGET: <budget-name> in <account / scope>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Budget type: COST | RI_UTILIZATION | RI_COVERAGE | SP_UTILIZATION | SP_COVERAGE | ANOMALY
  [✓|✗] Scope: <account | linked account | service | tag | region>
  [✓|✗] Amount / target: <$amount for COST | % for USAGE>
  [✓|✗] Time period: MONTHLY | DAILY | QUARTERLY | ANNUALLY
  [✓|✗] Alerts: <list with NotificationType ACTUAL|FORECAST, Threshold, ComparisonOperator>
  [✓|✗] Budget actions: <list with action type, threshold, target, approval model>
  [✓|✗] Action execution role: <ARN, trust on budgets.amazonaws.com verified>
  [✓|✗] SNS topic: <ARN, topic policy includes budgets.amazonaws.com AND ce.amazonaws.com>
  [✓|✗] SNS subscriptions: <list, all confirmed>
  [✓|✗] KMS key policy (if encrypted topic): <grants to budgets + ce verified | N/A>
  [✓|✗] Cost anomaly monitor: <ARN | N/A>
  [✓|✗] Cost anomaly subscription: <ARN, Threshold $X | N/A>
  [✓|✗] Cost filters: <list of CostFilters | none>
VERIFICATION_COMMANDS:
  aws budgets describe-budget --account-id <id> --budget-name <name>
  aws budgets describe-notifications-for-budget --account-id <id> --budget-name <name>
  aws budgets describe-budget-actions --account-id <id> --budget-name <name>
  aws ce get-anomaly-monitors
  aws ce get-anomaly-subscriptions
  aws sns get-topic-attributes --topic-arn <arn>
```

### Worked example — production cost budget with action tier

```text
BUDGET: prod-monthly-cost in 111111111111 (account-wide)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Budget type: COST  | Scope: account-wide | Amount: $10,000 USD | MONTHLY
  [✓] Alerts: 80% / 90% / 100% ACTUAL + 100% FORECAST → SNS budget-alerts
  [✓] Budget actions: APPLY_IAM_POLICY (BudgetDenyAll on SandboxAppRole) at 100% ACTUAL, AUTOMATIC
  [✓] Action role: arn:aws:iam::111111111111:role/BudgetActionsRole (trust verified)
  [✓] SNS topic: arn:aws:sns:us-east-1:111111111111:budget-alerts (policy allows budgets + ce)
  [✓] SNS subscriptions: finops@example.com (confirmed), budget-auto-remediation Lambda
  [✓] KMS key policy: N/A (topic uses alias/aws/sns)
  [✓] Cost anomaly: default monitor + prod-anomaly-subscription (Threshold $100, DAILY, SNS)
  [✓] Cost filters: none
VERIFICATION_COMMANDS:
  aws budgets describe-budget --account-id 111111111111 --budget-name prod-monthly-cost
  aws budgets describe-notifications-for-budget --account-id 111111111111 --budget-name prod-monthly-cost
  aws budgets describe-budget-actions --account-id 111111111111 --budget-name prod-monthly-cost
  aws ce get-anomaly-monitors
  aws ce get-anomaly-subscriptions
  aws sns get-topic-attributes --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts
```

## Error handling (quick triage)

- **`InvalidParameterException` on `create-budget-action`:** role missing
  or trust policy lacks `budgets.amazonaws.com`; policy ARN / target
  principal does not exist; cross-account role not in linked account.
- **`create-notification` succeeds but alerts never fire:** SNS
  subscription is `PendingConfirmation`; topic policy lacks
  `budgets.amazonaws.com` principal; customer-CMK key policy lacks
  `kms:GenerateDataKey*` for `budgets.amazonaws.com`.
- **Cost Anomaly subscription created but no alerts fire:** monitor not
  `ACTIVE`; topic policy lacks `ce.amazonaws.com` principal; subscription
  `Threshold` set above actual impact; monitor <7 days old (needs ~30
  days of CE history).
- **Budget action fires but does not take effect:** role lacks
  `iam:AttachUserPolicy` / `ssm:StartAutomationExecution`;
  `ApprovalModel=MANUAL` and nobody approved it; target resource in a
  different account than the ExecutionRoleArn.

## Decision tree: notify-only vs action tier

```text
Production budget (cannot tolerate deny/stop)?
├── YES → Notify-only (SNS + email). Thresholds: 80/90/100% ACTUAL + 100% FORECAST.
└── NO → Sandbox/dev/test where stop is acceptable?
    ├── YES → 80/90% ACTUAL → SNS only; 100% ACTUAL → APPLY_IAM_POLICY or
    │         RUN_SSM_DOCUMENTS. ApprovalModel: AUTOMATIC for dev, MANUAL for prod-adjacent.
    └── NO → Usage budget (RI_*, SP_*)?
        └── YES → Notify-only (API rejects actions on USAGE budgets).
```

## Recent AWS features (2024-2026)

- **Savings Plan Budget alerts (2024-2025 GA):** AWS Budgets now
  supports `SP_UTILIZATION` and `SP_COVERAGE` budget types natively.
  Previously these were only available via Cost Explorer queries. The
  Budgets API surfaces them as first-class usage budgets with SNS/email
  notifications (no actions — see Step 4 constraint).
- **Cost Anomaly Detection Feedback API GA (2024-2025):**
  `aws ce put-feedback` lets operators annotate false positives and
  true positives directly via CLI. The ML model learns ONLY from
  explicit feedback — console "dismiss" does not train it. Plan a
  runbook step to call `put-feedback` for each reviewed anomaly.
- **Anomaly Monitor `MonitorSpecification` JSON (2024-2025):**
  dimensional monitors now accept a `MonitorSpecification` JSON filter
  for `ANOMALY_TOTAL_IMPACT_ABSOLUTE` and
  `ANOMALY_TOTAL_IMPACT_PERCENTAGE`. Provisioning tip: set both —
  dollar for absolute impact, percent for relative impact.
- **Budget Actions regional expansion (2024-2025):** `RUN_SSM_DOCUMENTS`
  now supports `STOP_RDS_INSTANCE` (in addition to
  `STOP_EC2_INSTANCES`). Use for non-production databases.
- **Cost Explorer tag-based filters in Budgets (2024):**
  `CostFilters.TagKeyValue` now accepts up to 50 tag key-value pairs
  per budget (up from 10). Provisioning tip: complex tag filters still
  require tags to be activated in Billing → Cost Allocation Tags.

## Domain

AWS CloudOps / FinOps — Spend Guardrails & Cost Governance.

## AWS documentation

- **AWS Budgets User Guide** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- **AWS Budgets actions** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html
- **Cost Anomaly Detection** — https://docs.aws.amazon.com/cost-management/latest/userguide/anomaly-detection.html
- **Budgets CLI reference** — https://docs.aws.amazon.com/cli/latest/reference/budgets/
- **Cost Explorer API (CE) CLI reference** — https://docs.aws.amazon.com/cli/latest/reference/ce/
- **Savings Plans + Budgets integration** — https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-budgets.html
- **IAM role for Budget Actions** — https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html#budgets-controls-role
