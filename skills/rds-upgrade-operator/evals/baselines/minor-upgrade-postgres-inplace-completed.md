# Baseline (no-skill) response: minor-upgrade-postgres-inplace-completed

This file captures what a generic assistant produces WITHOUT the
rds-upgrade-operator skill loaded.

---

To upgrade your Aurora PostgreSQL cluster from 14.10 to 14.11, run:

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier prod-orders-cluster \
  --engine-version 14.11 \
  --apply-immediately
```

This will apply the minor version upgrade immediately. The cluster will
be in the "upgrading" state for a few minutes. You can check the status
with `aws rds describe-db-clusters`.
