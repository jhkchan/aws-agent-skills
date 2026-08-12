# Baseline (no-skill) response: rollback-via-pitr-review-required

This file captures what a generic assistant produces WITHOUT the
rds-upgrade-operator skill loaded.

---

To roll back to the pre-upgrade state, restore from the point-in-time
backup:

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier prod-orders-db \
  --target-db-instance-identifier prod-orders-db-rollback \
  --restore-time 2026-08-04T02:50:00Z
```

This will create a new instance. Note that the endpoint will be
different. After the restore completes, update your application
connection strings to point to the new instance.
