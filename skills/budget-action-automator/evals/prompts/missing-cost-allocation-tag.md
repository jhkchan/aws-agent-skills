# Eval prompt: missing-cost-allocation-tag

Design a Budgets automation workflow for the following tag-scoped
cost budget. Emit the standard BUDGET ACTION block (TYPE, LIMIT,
TIME_UNIT, THRESHOLD, NOTIFICATION, RESPONSE, MULTI_ACCOUNT,
COST_ALLOCATION_TAGS, VERDICT, TEMPLATE).

Design reference: missing-cost-allocation-tag
Account: 111111111111
Region: us-east-1

Budget type: COST
Limit: $20,000 USD / MONTHLY
CostFilters: {Tag: ["env:prod"]}
Threshold: Actual 90% (SNS notify)
SNS topic ARN: arn:aws:sns:us-east-1:111111111111:budget-alerts
Cost allocation tags: env is NOT activated in Billing console.
  Recent ce get-cost-and-usage --group-by Type=TAG,Key=env
  returns only $NULL rows.
