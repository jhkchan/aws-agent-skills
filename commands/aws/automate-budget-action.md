---
description: Design AWS Budgets automated action workflows with the right threshold pairing (forecast + actual), notification wiring (SNS, Slack via Lambda), enforcement response (APPLY_IAM_ACTION, APPLY_SCP_FAMILY, APPLY_SSM_ACTION, EventBridge to Lambda for custom), multi-account rollout via Organizations Payer or CloudFormation StackSet, cost allocation tag prerequisite check, and Budgets vs Cost Anomaly Detection complementary use. Enforces guardrails — ApprovalModel MANUAL before AUTOMATIC, 3-cycle validation (notify only, IAM non-prod, SCP prod), scoped SCPs at the innermost OU, CloudTrail audit on every action. Emits AUTOMATION_DEPLOYED with budget template or REVIEW_REQUIRED with the specific gap.
nl_triggers:
  - "automate budget action"
  - "put-budget-action"
  - "budget breach SCP"
  - "budget SNS notification"
  - "forecast budget action"
  - "RI coverage budget"
  - "RI utilization budget"
  - "budget multi-account payer"
  - "cost allocation tag budget"
  - "Budgets API automation"
  - "budget EventBridge Lambda"
  - "budget Slack notification"
  - "APPLY_SCP_FAMILY"
  - "APPLY_IAM_ACTION"
  - "APPLY_SSM_ACTION STOP_EC2_INSTANCES"
  - "budget rollover"
  - "budget cost filters tag"
  - "Budgets vs Cost Anomaly Detection"
routes_to: budget-action-automator
---

# /aws:automate-budget-action

Activate the `budget-action-automator` skill and design an AWS
Budgets automation workflow with the right notification and
enforcement response.

## What it does

Reads a budget requirement (cost / usage / RI coverage / RI
utilization), threshold configuration (forecast + actual), and
response scope (notify only / IAM action / SCP deny / SSM stop /
Lambda custom), then applies a 15-step design process:

1. Classify the budget goal (cost containment, commitment performance,
   usage tracking).
2. Pick the budget type and time period (MONTHLY, QUARTERLY, ANNUALLY).
3. Choose threshold type (FORECASTED, ACTUAL, or paired).
4. Wire SNS notification with the budgets.amazonaws.com topic policy.
5. Apply SCP deny for hard enforcement (APPLY_SCP_FAMILY).
6. Apply IAM policy via budget action (APPLY_IAM_ACTION).
7. EventBridge to Lambda for custom actions (Slack, tag, multi-region).
8. Stop non-prod EC2 via APPLY_SSM_ACTION.
9. Tag untagged resources via EventBridge + Lambda + Resource Groups API.
10. Slack notification via Lambda (SNS forwarder).
11. Multi-account rollout via Organizations Payer / StackSet.
12. Cost allocation tag enforcement BEFORE budget creation.
13. Forecast-based proactive action (3-7 day warning).
14. Budget vs Cost Anomaly Detection complementary use.
15. Budget rollover / reset semantics (Lambda-driven).

Emits a deterministic VERDICT per budget:

```text
BUDGET: <reference>
TYPE: <COST | USAGE | RI_COVERAGE | RI_UTILIZATION | SAVINGS_PLANS_COVERAGE | SAVINGS_PLANS_UTILIZATION>
LIMIT: <amount> <unit>
TIME_UNIT: <MONTHLY | QUARTERLY | ANNUALLY | DAILY>
THRESHOLD:
  - Forecast: <value>% (response)
  - Actual: <value>% (response)
NOTIFICATION:
  - Topic: <SNS ARN>
  - Targets: <list>
RESPONSE:
  - SCP / IAM / SSM / Lambda: <configuration>
MULTI_ACCOUNT: <single | payer-scoped | stack-set-per-OU>
COST_ALLOCATION_TAGS: <activated | not-activated | n/a>
ROLLOVER: <none | lambda-driven>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
GAP: <if REVIEW_REQUIRED, the specific missing piece>
TEMPLATE: <CLI snippet or YAML for the budget configuration>
```

## When to invoke

Paste a budget requirement and ask:

- "alert at 80% forecast on $10K monthly cost budget"
- "deny new EC2 launches at 100% actual spend via SCP"
- "tag-scoped budget for env=prod with SNS notify"
- "configure RI coverage budget at 75% target"
- "stop non-prod EC2 at 110% budget breach"
- "multi-account budget rollout via Organizations Payer"
- "Slack notification on budget forecast"
- "validate our budget enforcement workflow for gaps"

A bare budget type + threshold + "automate" routes here via the
orchestrator.

## Inputs

- **Required:** budget_type (COST | USAGE | RI_COVERAGE |
  RI_UTILIZATION), limit_amount, time_unit (MONTHLY / QUARTERLY /
  ANNUALLY / DAILY).
- **Recommended:** threshold_pairs (forecast %, actual %),
  response_type (notify / IAM / SCP / SSM / Lambda), sns_topic_arn,
  multi_account_scope (single / payer / stack-set).
- **For SCP enforcement:** org_id, target_ou_id or account_id,
  existing_scp_policy_id (or scp_policy_document to pre-create).
- **For IAM enforcement:** policy_arn, target_users list.
- **For tag-scoped budgets:** cost_filters (Tag key=value),
  confirmation that the tag is activated in Billing console.

## Outputs

- One BUDGET ACTION block per budget with THRESHOLD, NOTIFICATION,
  RESPONSE, MULTI_ACCOUNT, COST_ALLOCATION_TAGS, VERDICT, and
  TEMPLATE fields.
- For AUTOMATION_DEPLOYED verdicts: a working create-budget /
  create-notification / put-budget-action CLI sequence with the
  exact parameter mapping and execution role trust policy.
- For REVIEW_REQUIRED verdicts: a specific GAP citation (missing
  cost allocation tag activation, destructive SCP without validation,
  standalone account cannot use SCP, etc.).
- Expert-knowledge callouts (forecast probabilistic, IAM non-detach
  on recovery, ECR push-time scan gap analog, 3-cycle validation).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 4 Automate specialist for FinOps budget enforcement).
- `/aws:audit-budgets` for budget threshold posture audits (this
  skill designs automation; the auditor reviews configuration).
- `/aws:audit-ce-cost-anomaly` for Cost Anomaly Detection coverage
  (complementary monitoring layer to Budgets).
- `/aws:automate-cost-anomaly-response` for ML-based anomaly
  response (Budgets is threshold-based; CAD is ML-based).
- `/aws:deploy-budget` for plain budget deployment without
  automated actions (this skill adds enforcement).
---
