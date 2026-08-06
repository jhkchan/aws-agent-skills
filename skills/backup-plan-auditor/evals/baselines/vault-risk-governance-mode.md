# Baseline (no-skill) response: vault-risk-governance-mode

This file captures what a generic assistant produces WITHOUT the
backup-plan-auditor skill loaded.

---

This backup plan backs up a staging EC2 instance daily with 30-day
retention. The vault has a lock with 30-day minimum retention and uses
a customer-managed KMS key.

The vault lock is currently in governance mode with a 30-day
changeable-for-days period, meaning it will become permanent in 30 days.
This is a reasonable configuration — the governance mode gives you time
to verify the settings before the lock becomes irreversible.

The plan covers one EC2 instance which is fine for a staging environment.
