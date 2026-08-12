# Baseline (no-skill) response: global-database-upgrade-review-required

This file captures what a generic assistant produces WITHOUT the
rds-upgrade-operator skill loaded.

---

To upgrade a global Aurora cluster from MySQL 5.7 to 8.0, upgrade the
primary Region first, then the secondary Regions will be upgraded
automatically:

```bash
aws rds modify-db-cluster \
  --db-cluster-identifier prod-payments-cluster \
  --engine-version 8.0.mysql_aurora.3.04.0 \
  --apply-immediately \
  --region us-east-1
```

Then check the secondary Regions to make sure they were upgraded too.
The upgrade may take several hours depending on the data size.
