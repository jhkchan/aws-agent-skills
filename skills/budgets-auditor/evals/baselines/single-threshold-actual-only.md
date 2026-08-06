# Baseline (no-skill) response: single-threshold-actual-only

This file captures what a generic assistant produces WITHOUT the
budgets-auditor skill loaded.

---

Your budget is configured with a single notification at 100% of actual spend,
delivered via SNS. The SNS topic policy correctly grants the budgets service
principal publish permission, so delivery should work.

The budget looks fine. Your actual spend is $5,400 against an $8,000 limit, so
you are under budget. If you want more visibility you could add additional
thresholds, but the current setup will alert you when you hit the limit.
