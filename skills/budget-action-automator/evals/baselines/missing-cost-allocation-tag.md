# Baseline (no-skill) response: missing-cost-allocation-tag

This file captures what a generic assistant produces WITHOUT the
budget-action-automator skill loaded.

---

You can scope the budget by tag using CostFilters. Set it to
`env:prod` so only prod resources are counted toward the budget.

```
aws budgets create-budget --budget '{"CostFilters": {"Tag": ["env:prod"]}, ...}'
```

Add an SNS notification at 90% of $20K. The budget will alert you
when prod spend crosses $18K.
