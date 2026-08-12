# Eval prompt: forecast-proactive-action

Design a Budgets automation workflow for the following cost budget
with forecast-driven IAM action. Emit the standard BUDGET ACTION
block (TYPE, LIMIT, TIME_UNIT, THRESHOLD, NOTIFICATION, RESPONSE,
MULTI_ACCOUNT, COST_ALLOCATION_TAGS, VERDICT, TEMPLATE).

Design reference: forecast-proactive-action
Account: 111111111111
Region: us-east-1

Budget type: COST
Limit: $25,000 USD / MONTHLY
Threshold:
  - FORECASTED 90% -> APPLY_IAM_ACTION against user "ci-bot-prod"
  - ACTUAL 100% -> SNS notify
IAM policy to attach: arn:aws:iam::111111111111:policy/budget-restrict-launch
Execution role ARN: arn:aws:iam::111111111111:role/BudgetActionExecutionRole
Cost allocation tags: n/a.
Pre-validation: completed in non-prod.
