# Baseline (no-skill) response: aurora-clone-from-snapshot-completed

This file captures what a generic assistant produces WITHOUT the
rds-snapshot-operator skill loaded.

---

To clone your Aurora cluster from the snapshot:

```bash
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier prod-aurora-clone \
  --snapshot-identifier prod-aurora-cluster-snap-20260805 \
  --engine aurora-mysql
```

After the cluster is created, you'll need to create a DB instance in
the cluster. You can check the status with describe-db-clusters.
