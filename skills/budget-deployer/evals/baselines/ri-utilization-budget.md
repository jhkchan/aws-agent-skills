# Baseline (no-skill) — ri-utilization-budget

> This is the response a model produces **without** the skill definition.
> It creates the budget but misses the LESS_THAN_THRESHOLD comparison
> operator for utilization budgets (defaults to GREATER_THAN which never
> fires), does not note that usage budgets reject budget actions, and
> omits the READY_TO_DEPLOY checklist. Generated for with-skill-vs-
> baseline comparison.

---

Here's how to create an RI utilization budget:

```bash
aws budgets create-budget --account-id 111111111111 \
  --budget '{"BudgetName":"ri-util-target","BudgetLimit":{"Amount":"80","Unit":"PERCENTAGE"},"TimeUnit":"MONTHLY","BudgetType":"RI_UTILIZATION"}'
```

Then add a notification:
```bash
aws budgets create-notification --account-id 111111111111 \
  --budget-name ri-util-target \
  --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=arn:aws:sns:us-east-1:111111111111:budget-alerts,Type=SNS
```

That sets up the RI utilization budget with an alert.
