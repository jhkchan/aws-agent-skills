# Baseline (no-skill) response: snapshot-restore-backup-creating

This file captures what a generic assistant produces WITHOUT the
dynamodb-backup-operator skill loaded.

---

You can restore from that backup with:

```bash
aws dynamodb restore-table-from-backup \
  --target-table-name prod-orders-table-restored-2026-08-09 \
  --backup-arn arn:aws:dynamodb:us-east-1:111111111111:table/prod-orders-table/backup/01709999999999-migrating
```

Wait for the table to become ACTIVE and then point your app at it.
