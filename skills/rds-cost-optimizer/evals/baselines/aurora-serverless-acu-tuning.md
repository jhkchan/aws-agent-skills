# Baseline (no-skill) response: aurora-serverless-acu-tuning

This file captures what a generic assistant produces WITHOUT the
rds-cost-optimizer skill loaded — the contrast that proves the skill adds
structure (deterministic VERDICT, min-ACU floor-cost model, ACU-vs-baseline
comparison, serverless-vs-fixed-instance decision).

---

Your Aurora Serverless v2 database has a minimum ACU of 8 but the average
usage is only around 4 ACU. You could lower the minimum ACU setting to save
on costs since you're paying for 8 ACU even when you only need 4. The actual
usage pattern shows it scales down overnight so a lower minimum would capture
those savings. You can change the scaling configuration in the console.
