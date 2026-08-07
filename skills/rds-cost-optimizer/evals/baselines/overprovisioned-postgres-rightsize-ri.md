# Baseline (no-skill) response: overprovisioned-postgres-rightsize-ri

This file captures what a generic assistant produces WITHOUT the
rds-cost-optimizer skill loaded — the contrast that proves the skill adds
structure (deterministic VERDICT, FreeableMemory signal, Graviton layering,
RI pricing model, stacking order).

---

This PostgreSQL database looks underutilized at 12% average CPU. You should
consider right-sizing to a smaller instance class. Since it's PostgreSQL you
could also look at Graviton instances which are cheaper. For the pricing
model, you might want to look into Reserved Instances or Savings Plans for
steady-state workloads. Make sure to test after any changes.
