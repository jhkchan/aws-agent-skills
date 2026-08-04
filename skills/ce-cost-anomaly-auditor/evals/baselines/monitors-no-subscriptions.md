# Baseline (no-skill) response: monitors-no-subscriptions

This file captures what a generic assistant produces WITHOUT the
ce-cost-anomaly-auditor skill loaded.

---

The account has two anomaly detection monitors configured (one IMMEDIATE
and one DAILY), which is good. However, there are zero subscriptions
attached to these monitors. This means the monitors will detect anomalies
but nobody will receive notifications about them.

You should create anomaly subscriptions on these monitors so that the
FinOps team gets email or SNS alerts when unusual spend patterns are
detected. The RI and SP coverage looks fine (72% and 60%).

CUR with resource IDs is enabled, so you can do resource-level cost
analysis.
