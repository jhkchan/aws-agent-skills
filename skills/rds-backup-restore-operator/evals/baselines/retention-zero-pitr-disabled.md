# Baseline (no-skill) response: retention-zero-pitr-disabled

This file captures what a generic assistant produces WITHOUT the
rds-backup-restore-operator skill loaded.

---

To restore to a point in time, run:

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier prod-analytics-db \
  --target-db-instance-identifier prod-analytics-db-pitr \
  --restore-time 2026-08-07T08:00:00Z
```

This will create a new instance with the data as of that time. After the
restore completes, you can connect to the new instance endpoint.

If the restore fails, you may need to enable backups first:
```
aws rds modify-db-instance --db-instance-identifier prod-analytics-db \
  --backup-retention-period 7 --apply-immediately
```
