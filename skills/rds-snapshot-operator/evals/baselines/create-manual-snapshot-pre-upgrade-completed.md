# Baseline (no-skill) response: create-manual-snapshot-pre-upgrade-completed

This file captures what a generic assistant produces WITHOUT the
rds-snapshot-operator skill loaded.

---

To create a manual snapshot before your RDS upgrade, use:

```bash
aws rds create-db-snapshot \
  --db-instance-identifier prod-orders-db \
  --db-snapshot-identifier prod-orders-db-pre-upgrade-20260805
```

Wait for the snapshot to become available with
`aws rds describe-db-snapshots`. Once it's available, you can proceed
with the engine upgrade.
