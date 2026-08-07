# Baseline (no-skill) response: pitr-restore-target-subnet-missing

This file captures what a generic assistant produces WITHOUT the
rds-backup-restore-operator skill loaded.

---

To restore your RDS instance to a point in time, use:

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier prod-orders-db \
  --target-db-instance-identifier prod-orders-db-pitr-2026-08-07 \
  --restore-time 2026-08-07T10:00:00Z
```

The restore will create a new instance. You may need to specify the subnet
group and security group.

Wait for the restore to complete with:
```
aws rds wait db-instance-available --db-instance-identifier prod-orders-db-pitr-2026-08-07
```

Then connect to the new instance endpoint.
