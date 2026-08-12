# Baseline (no-skill) response: forecast-proactive-action

This file captures what a generic assistant produces WITHOUT the
budget-action-automator skill loaded.

---

You can configure a forecast-based budget action. Set the threshold
type to FORECASTED at 90% and attach an IAM action that restricts
the CI bot user.

```
aws budgets put-budget-action --action-type APPLY_IAM_ACTION ...
```

The IAM policy will be attached when the forecast crosses 90%. Make
sure the execution role has the right permissions.
