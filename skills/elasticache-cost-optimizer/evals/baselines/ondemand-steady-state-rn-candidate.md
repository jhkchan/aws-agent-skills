# Baseline (no-skill) response: ondemand-steady-state-rn-candidate

This file captures what a generic assistant produces WITHOUT the
elasticache-cost-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, RN sizing math, 1-yr vs
3-yr break-even, anti-pattern: don't commit RN on clusters with
migration plans).

---

Your cluster has been running On-Demand for 12 months on
cache.r6g.2xlarge. You should probably look at Reserved Nodes since
the workload is steady and mission-critical. A 1-year or 3-year
Reserved Node would give you a significant discount.

Check the Reserved Node offerings in the ElastiCache console to see
which one fits.
