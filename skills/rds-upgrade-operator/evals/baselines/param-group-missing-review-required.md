# Baseline (no-skill) response: param-group-missing-review-required

This file captures what a generic assistant produces WITHOUT the
rds-upgrade-operator skill loaded.

---

To upgrade from PostgreSQL 13 to 14, run:

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier prod-analytics-cluster \
  --engine-version 14.9 \
  --apply-immediately
```

You should also make sure you have a parameter group for PostgreSQL 14.
You can use the default one or create a custom one. After the upgrade,
verify the cluster status with `describe-db-clusters`.
