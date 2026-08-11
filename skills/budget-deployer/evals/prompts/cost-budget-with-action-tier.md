# Eval: cost-budget-with-action-tier

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — all checklist items verified, IAM policy action wired, FORECAST + ACTUAL thresholds, anomaly subscription on default monitor

## Prompt

Provision a production AWS Budget named "prod-monthly-cost" in
account 111111111111 for the whole account (no filters). Budget
amount $10,000 USD MONTHLY. Alerts at 80/90/100% ACTUAL and 100%
FORECAST to SNS topic arn:aws:sns:us-east-1:111111111111:budget-alerts
(policy already allows budgets.amazonaws.com and ce.amazonaws.com).
Budget action: APPLY_IAM_POLICY
(arn:aws:iam::111111111111:policy/BudgetDenyAll) on SandboxAppRole
at 100% ACTUAL, ApprovalModel AUTOMATIC. ExecutionRoleArn
arn:aws:iam::111111111111:role/BudgetActionsRole (trust verified on
budgets.amazonaws.com). Also wire Cost Anomaly Detection: default
monitor, subscription prod-anomaly-subscription Threshold $100
DAILY to the same SNS topic.
