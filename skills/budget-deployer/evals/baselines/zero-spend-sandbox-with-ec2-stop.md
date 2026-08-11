# Baseline (no-skill) — zero-spend-sandbox-with-ec2-stop

> This is the response a model produces **without** the skill definition.
> It sets BudgetLimit.Amount=0 (API rejects), misses the 50% ACTUAL
> threshold pattern that fires on the first dollar, and does not verify
> the action role trust policy before create-budget-action. Generated
> for with-skill-vs-baseline comparison.

---

Set up a zero-spend budget on the sandbox:

```bash
aws budgets create-budget --account-id 111111111111 \
  --budget '{"BudgetName":"sandbox-zero-spend","BudgetLimit":{"Amount":"0","Unit":"USD"},"TimeUnit":"MONTHLY","BudgetType":"COST"}'
```

Add notification at 100%:
```bash
aws budgets create-notification --account-id 111111111111 \
  --budget-name sandbox-zero-spend \
  --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":100,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=arn:aws:sns:us-east-1:111111111111:security-alerts,Type=SNS
```

Add the IAM action:
```bash
aws budgets create-budget-action --account-id 111111111111 \
  --budget-name sandbox-zero-spend \
  --notification-type ACTUAL \
  --action-type APPLY_IAM_POLICY \
  --action-threshold '{"ActionThresholdValue":100,"ActionThresholdType":"PERCENTAGE"}' \
  --definition '{"IamActionDefinition":{"PolicyArn":"arn:aws:iam::111111111111:policy/BudgetDenyAll","Roles":["SandboxFullAccessRole"]}}' \
  --execution-role-arn arn:aws:iam::111111111111:role/BudgetActionsRole \
  --approval-model AUTOMATIC
```

That covers the sandbox guardrail.
