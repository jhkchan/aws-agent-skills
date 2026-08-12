# Baseline (no-skill) response: ri-coverage-budget

This file captures what a generic assistant produces WITHOUT the
budget-action-automator skill loaded.

---

You can create an RI coverage budget with BudgetType set to
RI_COVERAGE. Set the limit to 75% and add an SNS notification when
it drops below that.

```
aws budgets create-budget --budget '{"BudgetType": "RI_COVERAGE", "BudgetLimit": {"Amount": "75", "Unit": "PERCENTAGE"}, ...}'
```

If RI coverage falls below 75% the SNS topic gets a notification.
You can use this to keep your commitment strategy on track.
