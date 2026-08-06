# Baseline (no-skill) response: capacity-mismatch-no-autoscaling

This file captures what a generic assistant produces WITHOUT the
dynamodb-table-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, expert knowledge deltas).

---

The table is using provisioned capacity with 100 RCUs and 50 WCUs. It has
encryption and PITR set up correctly. You might want to consider adding
autoscaling or switching to on-demand mode if your traffic varies. The current
fixed capacity could lead to throttling during traffic spikes.

Consider setting up application autoscaling for the table.
