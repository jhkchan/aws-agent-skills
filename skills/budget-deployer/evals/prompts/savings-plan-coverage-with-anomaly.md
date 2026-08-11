# Eval: savings-plan-coverage-with-anomaly

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — SP_COVERAGE budget (latest GA) + dimensional SERVICE anomaly monitor, ce.amazonaws.com SNS principal verified

## Prompt

Set up spend guardrails for account 111111111111. Two things:
(1) A Savings Plan Coverage budget at 80% MONTHLY, alert when
coverage drops below 80% ACTUAL via SNS
arn:aws:sns:us-east-1:111111111111:budget-alerts (policy allows
budgets.amazonaws.com AND ce.amazonaws.com).
(2) Cost Anomaly Detection with a dimensional SERVICE monitor
and subscription Threshold $250 DAILY to the same SNS topic.
Account: 111111111111.
