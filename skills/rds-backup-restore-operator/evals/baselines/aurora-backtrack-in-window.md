# Baseline (no-skill) response: aurora-backtrack-in-window

This file captures what a generic assistant produces WITHOUT the
rds-backup-restore-operator skill loaded.

---

You can backtrack your Aurora cluster with:

```bash
aws rds backtrack-db-cluster \
  --db-cluster-identifier aurora-prod-cluster \
  --backtrack-to-timestamp 2026-08-07T09:00:00Z
```

This should rewind the cluster to before the bad UPDATE. Aurora backtrack is
fast and doesn't create a new cluster.

Wait for it to complete and verify the data is correct.
