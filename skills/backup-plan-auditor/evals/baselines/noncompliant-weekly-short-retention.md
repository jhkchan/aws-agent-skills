# Baseline (no-skill) response: noncompliant-weekly-short-retention

This file captures what a generic assistant produces WITHOUT the
backup-plan-auditor skill loaded.

---

This backup plan runs weekly (every Monday) with a 7-day retention
period. The vault has a compliance-mode lock and uses a customer-managed
key, which is good.

You might want to consider running backups more frequently than weekly
for better recovery point objectives. Also, 7-day retention is quite
short — depending on your compliance requirements, you may need longer
retention periods.

The plan covers one EC2 instance which is fine.
