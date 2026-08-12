# Baseline (no-skill) response: cost-budget-sns-notification

This file captures what a generic assistant produces WITHOUT the
budget-action-automator skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, threshold pairing,
SNS topic access policy, multi-account scoping, expert Budgets
knowledge).

---

You can set up an AWS Budget to alert when your monthly cost goes
over $10K. Use create-budget with the cost amount and an SNS
notification at 80%. Add an email subscriber too.

```
aws budgets create-budget --account-id 111111111111 --budget '...'
```

You need an SNS topic ARN. Then subscribe an email address. The
notification threshold is set when you create the notification.

If you want it to also fire at 100%, add another notification.
