# Baseline (no-skill) response: ec2-overprovisioned-high-confidence

This file captures what a generic assistant produces WITHOUT the
compute-optimizer-findings-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, confidence gating, per-
finding risk, CLI remediation).

---

This EC2 instance (m5.2xlarge) has a Compute Optimizer finding of
Overprovisioned. The CPU utilization is 8% and memory is 15%, which is
quite low. The recommendation is to change to a t3.large instance which
would save about $150 per month.

You should consider right-sizing this instance to reduce costs. The
performance risk is low (1), so the change should be safe. Make sure to
test after making the change.
