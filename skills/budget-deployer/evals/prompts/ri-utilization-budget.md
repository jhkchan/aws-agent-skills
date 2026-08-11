# Eval: ri-utilization-budget

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — RI_UTILIZATION budget, notifications only (no budget actions — API rejects on usage budgets)

## Prompt

Provision an AWS Budget for RI Utilization in account 111111111111.
Budget name "ri-util-target". Target 80% MONTHLY. Alert me when
utilization drops below 80% ACTUAL via SNS topic
arn:aws:sns:us-east-1:111111111111:budget-alerts (policy allows
budgets.amazonaws.com). We have RIs on EC2 m5.large in us-east-1.
Account: 111111111111.
