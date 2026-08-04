# Baseline (no-skill) response: daily-only-no-cur

This file captures what a generic assistant produces WITHOUT the
ce-cost-anomaly-auditor skill loaded.

---

The account has a DAILY anomaly monitor with a DAILY subscription and a
$50 threshold. This seems reasonably configured for an $8,000/month
account. The coverage is okay at 68% RI and 55% SP.

One thing to note is that CUR with resource IDs is not configured. This
means you cannot do resource-level cost analysis in Cost Explorer. You
should set up a Cost and Usage Report with resource IDs if you want to
track costs at the individual resource level.

Consider adding an IMMEDIATE monitor for faster anomaly detection since
the DAILY monitor only evaluates once per day.
