# Baseline (no-skill) response: pitr-restore-pitr-disabled

This file captures what a generic assistant produces WITHOUT the
dynamodb-backup-operator skill loaded.

---

You can restore your DynamoDB table to a point in time with:

```bash
aws dynamodb restore-table-to-point-in-time \
  --source-table-name prod-orders-table \
  --target-table-name prod-orders-table-pitr-2026-08-09 \
  --restore-date-time 2026-08-09T10:00:00Z
```

This will create a new table with the data as it was at 10:00 UTC.
Wait for the restore to complete and then point your application at the
new table.
