# Baseline (no-skill) response: sns-policy-missing

This file captures what a generic assistant produces WITHOUT the
budgets-auditor skill loaded.

---

Your budget has a notification set up at 100% of the actual spend, pointing at
an SNS topic. The SNS topic policy grants publish permission to your account
root.

This looks reasonable. The account root has access to publish to the topic,
and the budget notification is configured to send to that topic when you hit
100% of your budget. You might also want to add a notification at a lower
threshold like 80% so you get an earlier warning.
