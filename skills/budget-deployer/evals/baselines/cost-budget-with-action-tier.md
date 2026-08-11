# Baseline (no-skill) — cost-budget-with-action-tier

> This is the response a model produces **without** the skill definition.
> It lists some AWS CLI commands but misses the ExecutionRoleArn trust
> verification, the ce.amazonaws.com SNS principal requirement for
> anomaly alerts, the FORECAST notification pairing, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-baseline
> comparison.

---

Here's how to create a cost budget with actions:

1. Create the budget:
```bash
aws budgets create-budget --account-id 111111111111 \
  --budget '{"BudgetName":"prod-monthly-cost","BudgetLimit":{"Amount":"10000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}'
```

2. Add a notification at 100%:
```bash
aws budgets create-notification --account-id 111111111111 \
  --budget-name prod-monthly-cost \
  --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":100,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=arn:aws:sns:us-east-1:111111111111:budget-alerts,Type=SNS
```

3. Add a budget action:
```bash
aws budgets create-budget-action --account-id 111111111111 \
  --budget-name prod-monthly-cost \
  --notification-type ACTUAL \
  --action-type APPLY_IAM_POLICY \
  --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
  --definition '{"IamActionDefinition":{"PolicyArn":"arn:aws:iam::111111111111:policy/BudgetDenyAll","Roles":["SandboxAppRole"]}}' \
  --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionsRole \
  --approval-model AUTOMATIC
```

That should set up the budget with the action.
