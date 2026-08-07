# Baseline (no-skill) response: multiaz-nonprod-removal

This file captures what a generic assistant produces WITHOUT the
rds-cost-optimizer skill loaded — the contrast that proves the skill adds
structure (deterministic VERDICT, environment-aware Multi-AZ gating,
compute-doubling cost quantification).

---

Your staging database has Multi-AZ enabled which means you're paying for two
instances. Since this is a staging environment and you don't need high
availability, you can turn off Multi-AZ to save money. This will roughly
halve your compute costs. You can disable Multi-AZ through the modify-db-
instance command.
