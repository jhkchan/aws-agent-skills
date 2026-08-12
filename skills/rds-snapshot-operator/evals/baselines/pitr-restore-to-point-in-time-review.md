# Baseline (no-skill) response: pitr-restore-to-point-in-time-review

This file captures what a generic assistant produces WITHOUT the
rds-snapshot-operator skill loaded.

---

To restore your RDS instance to a point in time:

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier prod-orders-db \
  --target-db-instance-identifier prod-orders-db-pitr \
  --restore-time 2026-08-05T14:35:00Z
```

This will create a new instance. You may need to update your connection
strings after the restore completes.
