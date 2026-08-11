# Baseline (no-skill) — savings-plan-coverage-with-anomaly

> This is the response a model produces **without** the skill definition.
> It omits the SP_COVERAGE budget type (often defaults to a cost budget
> instead), uses the wrong SNS principal for the anomaly subscription,
> and does not mention that the ce.amazonaws.com principal must be added
> to the topic policy separately from budgets.amazonaws.com. Generated
> for with-skill-vs-baseline comparison.

---

To set up the spend guardrails:

1. Budget:
```bash
aws budgets create-budget --account-id 111111111111 \
  --budget '{"BudgetName":"sp-coverage","BudgetLimit":{"Amount":"80","Unit":"PERCENTAGE"},"TimeUnit":"MONTHLY","BudgetType":"SP_COVERAGE"}'
```

2. Notification:
```bash
aws budgets create-notification --account-id 111111111111 \
  --budget-name sp-coverage \
  --notification '{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":80,"ThresholdType":"PERCENTAGE"}' \
  --subscribers Address=arn:aws:sns:us-east-1:111111111111:budget-alerts,Type=SNS
```

3. Anomaly detection:
```bash
aws ce create-anomaly-subscription --anomaly-subscription '{"Name":"anomaly-sub","Frequency":"DAILY","Threshold":250,"MonitorArn":"arn:aws:ce::111111111111:anomaly-monitor/default","Subscribers":[{"Address":"arn:aws:sns:us-east-1:111111111111:budget-alerts","Type":"SNS"}]}'
```

That should cover the spend guardrails.
