# Baseline (no-skill) response: pitr-restore-in-window

This file captures what a generic assistant produces WITHOUT the
dynamodb-backup-operator skill loaded.

---

To restore prod-orders-table to 10:00 UTC:

```bash
aws dynamodb restore-table-to-point-in-time \
  --source-table-name prod-orders-table \
  --target-table-name prod-orders-table-pitr-2026-08-09 \
  --restore-date-time 2026-08-09T10:00:00Z
```

This creates a new table with the data as of 10:00 UTC. Update your
application to use the new table name once the restore completes.
