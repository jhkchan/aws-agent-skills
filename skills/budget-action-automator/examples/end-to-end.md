# End-to-end usage scenario: budget-action-automator

A walkthrough showing the skill designing two budget actions for
the same account: an AUTOMATION_DEPLOYED cost budget with SNS
notification and forecast-driven IAM action, and a REVIEW_REQUIRED
tag-scoped budget where the tag is not activated in the Billing
console. Demonstrates the threshold matrix and the cost-allocation-
tag prerequisite.

## Input (user prompt)

> Set up budget automation for our production account. We want
> alerting at 80% forecast on the $25K monthly cost budget and IAM
> restriction on the CI bot at 90% forecast. Also, separately, a
> $20K budget on prod-only spend tagged env=prod.

```
Design reference: prod-budget-rollout
Account: 111111111111
Region: us-east-1

Budget 1: total-cost-budget
  Type: COST
  Limit: $25,000 USD / MONTHLY
  Threshold:
    - FORECASTED 80% (SNS notify)
    - FORECASTED 90% (IAM action against ci-bot-prod)
    - ACTUAL 100% (SNS notify)
  IAM policy to attach: arn:aws:iam::111111111111:policy/budget-restrict-launch
  SNS topic ARN: arn:aws:sns:us-east-1:111111111111:budget-alerts
  Execution role ARN: arn:aws:iam::111111111111:role/BudgetActionExecutionRole
  Pre-validation: completed in non-prod.

Budget 2: env-tag-scoped-budget
  Type: COST
  Limit: $20,000 USD / MONTHLY
  CostFilters: {Tag: ["env:prod"]}
  Threshold: Actual 90% (SNS notify)
  SNS topic ARN: arn:aws:sns:us-east-1:111111111111:budget-alerts
  Cost allocation tag status: env is NOT activated in Billing console.
```

## Skill output

```text
BUDGET: prod-budget-rollout / total-cost-budget
TYPE: COST
LIMIT: 25000 USD
TIME_UNIT: MONTHLY
THRESHOLD:
  - Forecast: 80% (SNS notify — ops team warning)
  - Forecast: 90% (APPLY_IAM_ACTION on ci-bot-prod)
  - Actual: 100% (SNS notify — breach alert)
NOTIFICATION:
  - Topic: arn:aws:sns:us-east-1:111111111111:budget-alerts
  - Targets: ops@company.com, Slack #finops-alerts
RESPONSE:
  - IAM: attach arn:aws:iam::111111111111:policy/budget-restrict-launch to user ci-bot-prod on forecast breach
MULTI_ACCOUNT: single (111111111111)
COST_ALLOCATION_TAGS: n/a
ROLLOVER: none
VERDICT: AUTOMATION_DEPLOYED
GAP: None
TEMPLATE:
  aws budgets create-budget --account-id 111111111111 --budget '{"BudgetName":"total-cost-budget","BudgetLimit":{"Amount":"25000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}'
  aws budgets create-notification --account-id 111111111111 --budget-name total-cost-budget --notification '{"NotificationType":"FORECASTED","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"}' --subscribers '[{"SubscriptionType":"SNS","Address":"arn:aws:sns:us-east-1:111111111111:budget-alerts"}]'
  aws budgets put-budget-action --account-id 111111111111 --budget-name total-cost-budget --notification-type FORECASTED --action-type APPLY_IAM_ACTION --action-threshold '{"ActionThresholdValue":90,"ActionThresholdType":"PERCENTAGE"}' --definition '{"IamActionDefinition":{"PolicyArn":"arn:aws:iam::111111111111:policy/budget-restrict-launch","Users":["ci-bot-prod"]}}' --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionExecutionRole --approval-model AUTOMATIC

BUDGET: prod-budget-rollout / env-tag-scoped-budget
TYPE: COST
LIMIT: 20000 USD
TIME_UNIT: MONTHLY
THRESHOLD:
  - Actual: 90% (SNS notify)
NOTIFICATION:
  - Topic: arn:aws:sns:us-east-1:111111111111:budget-alerts
RESPONSE: notify-only
MULTI_ACCOUNT: single
COST_ALLOCATION_TAGS: NOT-ACTIVATED (tag 'env' is not active in Billing console)
ROLLOVER: none
VERDICT: REVIEW_REQUIRED
GAP: Cost allocation tag 'env' is not activated. The budget CostFilters clause will match zero spend until activated. Activate via aws ce update-cost-allocation-tags-status --tag-keys env --status Active and wait 24 hours before creating the budget.
TEMPLATE: (blocked until tags activated)
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED for
total-cost-budget + REVIEW_REQUIRED for env-tag-scoped-budget.**
Roll out the first budget immediately; the tag-scoped budget is
blocked until cost allocation tags are activated.

## What the skill caught that a generic assistant misses

1. **The forecast-probabilistic caveat.** A generic assistant
   treats `FORECASTED` as deterministic. The skill notes the
   80% confidence interval and pairs forecast at 90% with actual
   at 100% as backup.

2. **The IAM non-detach gotcha.** A generic assistant wires the
   IAM action and forgets the recovery path. The skill flags that
   `APPLY_IAM_ACTION` does NOT detach on budget reset — wire a
   Lambda or monthly cleanup.

3. **The SNS topic access policy.** A generic assistant skips the
   topic policy. The skill requires `Service: budgets.amazonaws.com`
   in the topic policy or the notification silently fails.

4. **The cost-allocation-tag prerequisite.** A generic assistant
   ships the tag-scoped budget and assumes it works. The skill
   refuses — REVIEW_REQUIRED — because the tag is not activated.
   The budget would silently match zero spend.

5. **The approval-model progression.** A generic assistant wires
   `ApprovalModel: AUTOMATIC` from day one. The skill requires the
   3-cycle validation protocol (notify-only → IAM non-prod → SCP
   prod) before flipping to automatic in production.

## Slash-command invocation

```
/aws:automate-budget-action
```

Or via the orchestrator:

```
/aws:pipeline
You: "set up budget automation for production"
```

## CLI routing

```bash
node cli/bin/cli.js route "automate budget action"
# [Phase: Automate | Skills routed: budget-action-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Discover existing budgets
aws budgets describe-budgets \
  --account-id 111111111111 --region us-east-1 --profile default

# Check existing budget actions
aws budgets describe-budget-action \
  --account-id 111111111111 \
  --budget-name total-cost-budget \
  --action-id <action-id> --region us-east-1 --profile default

# Check action execution history
aws budgets describe-budget-action-histories \
  --account-id 111111111111 \
  --budget-name total-cost-budget \
  --action-id <action-id> \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --region us-east-1 --profile default

# Verify cost allocation tags are activated
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=TAG,Key=env \
  --region us-east-1 --profile default

# Verify the SNS topic policy allows budgets.amazonaws.com
aws sns get-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:111111111111:budget-alerts \
  --region us-east-1 --profile default --query 'Attributes.Policy'

# Verify the execution role trust policy
aws iam get-role \
  --role-name BudgetActionExecutionRole \
  --query 'Role.AssumeRolePolicyDocument' \
  --region us-east-1 --profile default --output json
```

Then paste the output into the skill for workflow design.

## Complementary controls

Pair this skill with Cost Anomaly Detection for layered monitoring:

- **Budgets** — known spend limits, threshold enforcement
- **Cost Anomaly Detection** — ML-based anomaly detection for
  unknown spend patterns

Wire CAD subscriptions to a different SNS topic than budget alerts
to keep the audit trail separate. Use the `ce-cost-anomaly-auditor`
skill to verify CAD coverage gaps.
