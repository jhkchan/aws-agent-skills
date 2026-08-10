# Baseline (no-skill) response: on-demand-backup-create-ready

This file captures what a generic assistant produces WITHOUT the
dynamodb-backup-operator skill loaded.

---

You can create an on-demand backup with:

```bash
aws dynamodb create-backup \
  --table-name prod-orders-table \
  --backup-name prod-orders-table-pre-migration-2026-08-09
```

The backup will be stored in S3 and you can use it later to restore the
table if needed.
