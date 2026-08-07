# Baseline (no-skill) response: snapshot-missing-for-pre-migration

This file captures what a generic assistant produces WITHOUT the
rds-backup-restore-operator skill loaded.

---

To restore from the snapshot, run:

```bash
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier prod-checkout-restored \
  --db-snapshot-identifier prod-pre-migration-snap
```

If the snapshot doesn't exist yet, you should create it first:

```bash
aws rds create-db-snapshot \
  --db-instance-identifier prod-checkout \
  --db-snapshot-identifier prod-pre-migration-snap
```

Then wait for it to complete and run the restore.
