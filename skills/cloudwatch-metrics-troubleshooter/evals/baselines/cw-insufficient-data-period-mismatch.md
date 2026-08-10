# Baseline (no-skill) response: cw-insufficient-data-period-mismatch

This file captures what a generic assistant produces WITHOUT the
cloudwatch-metrics-troubleshooter skill loaded — the contrast that
proves the skill adds structure (deterministic VERDICT, category-aware
walk, specific remediation).

---

Your alarm is in INSUFFICIENT_DATA because it's not seeing enough
data points. Your heartbeat metric only emits every 5 minutes, but
the alarm has Period 60 and EvaluationPeriods 5. That means it needs
5 data points within 5 minutes, but you only emit 1 every 5 minutes.

You should either increase the Period to 300 (5 minutes) so each
evaluation window captures one data point, or lower the
EvaluationPeriods to 1. You might also want to set TreatMissingData
to `notBreaching` so missing data is treated as healthy.
