# Baseline (no-skill) response: no-deletion-protection-prod

---

This instance is private, encrypted, and Multi-AZ, which is a good posture.
One concern is that `DeletionProtection: false`, so the instance could be
deleted accidentally. You may want to enable deletion protection for a
production database. Backups and monitoring look fine.
