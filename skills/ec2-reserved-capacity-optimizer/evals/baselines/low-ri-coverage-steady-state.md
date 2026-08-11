# Baseline (no-skill) response: low-ri-coverage-steady-state

This file captures what a generic assistant produces WITHOUT the
ec2-reserved-capacity-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, multi-dimension
analysis, specific savings estimates).

---

Your fleet has low RI coverage at 40%. Since 60% of your instances are
running on-demand, you should buy more Reserved Instances to cover them.
You could go with 1-year or 3-year RIs depending on how long you plan
to keep these instances running. The 3-year option gives a bigger
discount but locks you in longer.

Since your utilization is already at 97% on the existing RIs, you're
definitely leaving money on the table by not covering the remaining
instances. Try using Cost Explorer to get purchase recommendations.
