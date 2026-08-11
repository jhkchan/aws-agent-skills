# Baseline (no-skill) — missing-sns-and-action-role

> This is the response a model produces **without** the skill definition.
> It fails to identify the missing ExecutionRoleArn and the SNS topic
> policy gap (lacks budgets.amazonaws.com), and proceeds to emit CLI
> commands that will fail at runtime. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to set up the dev budget with an action:

```bash
aws budgets create-budget --account-id 111111111111 \
  --budget '{"BudgetName":"dev-spend","BudgetLimit":{"Amount":"5000","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}'

aws budgets create-notification --account-id 111111111111 \
  --budget-name dev-spend \
  --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":100,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=arn:aws:sns:us-east-1:111111111111:dev-alerts,Type=SNS

aws budgets create-budget-action --account-id 111111111111 \
  --budget-name dev-spend \
  --notification-type ACTUAL \
  --action-type APPLY_IAM_POLICY \
  --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
  --definition '{"IamActionDefinition":{"PolicyArn":"arn:aws:iam::111111111111:policy/BudgetDenyAll","Roles":["DevRole"]}}' \
  --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionsRole \
  --approval-model AUTOMATIC
```

That should create the budget with the deny policy action.
