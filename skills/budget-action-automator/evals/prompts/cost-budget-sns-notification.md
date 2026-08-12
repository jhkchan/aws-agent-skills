# Eval prompt: cost-budget-sns-notification

Design a Budgets automation workflow for the following cost budget
requirement. Emit the standard BUDGET ACTION block (TYPE, LIMIT,
TIME_UNIT, THRESHOLD, NOTIFICATION, RESPONSE, MULTI_ACCOUNT,
COST_ALLOCATION_TAGS, VERDICT, TEMPLATE).

Design reference: cost-budget-sns-notification
Account: 111111111111
Region: us-east-1

Budget type: COST
Limit: $10,000 USD / MONTHLY
Threshold: Forecast 80% (SNS notify), Actual 100% (SNS notify)
SNS topic ARN: arn:aws:sns:us-east-1:111111111111:budget-alerts
Topic policy: already grants budgets.amazonaws.com publish.
Cost allocation tags: n/a (no CostFilters).
