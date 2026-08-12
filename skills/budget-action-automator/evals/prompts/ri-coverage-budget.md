# Eval prompt: ri-coverage-budget

Design a Budgets automation workflow for the following RI coverage
budget. Emit the standard BUDGET ACTION block (TYPE, LIMIT,
TIME_UNIT, THRESHOLD, NOTIFICATION, RESPONSE, MULTI_ACCOUNT,
COST_ALLOCATION_TAGS, VERDICT, TEMPLATE). Note any special
semantics for RI coverage vs cost budgets.

Design reference: ri-coverage-budget
Account: 111111111111
Region: us-east-1

Budget type: RI_COVERAGE
Limit: 75 (% coverage) / MONTHLY
Threshold: Actual < 75% (SNS notify — coverage dropped)
SNS topic ARN: arn:aws:sns:us-east-1:111111111111:commitment-alerts
Existing RI utilization: 96% (RIs in use are utilized).
Cost allocation tags: n/a.
