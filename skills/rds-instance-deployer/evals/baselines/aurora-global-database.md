# Baseline (no-skill) — aurora-global-database

> This is the response a model produces **without** the skill definition.
> It produces a generic create-db-cluster in each region but misses the
> Global Database topology (create-global-cluster first), the per-region
> CMK requirement, the Backtrack configuration on the primary only, and
> the one-way failover caveat. Generated for with-skill-vs-baseline
> comparison.

---

To set up Aurora across regions:

1. Create primary cluster in us-east-1:
```bash
aws rds create-db-cluster \
  --db-cluster-identifier commerce-global-primary \
  --engine aurora-mysql \
  --engine-version 8.0 \
  --master-username admin \
  --master-user-password <password> \
  --region us-east-1 \
  --storage-encrypted \
  --kms-key-id alias/commerce-rds-key \
  --backup-retention-period 14
```

2. Create secondary cluster in eu-west-1:
```bash
aws rds create-db-cluster \
  --db-cluster-identifier commerce-global-secondary \
  --engine aurora-mysql \
  --engine-version 8.0 \
  --region eu-west-1 \
  --storage-encrypted \
  --kms-key-id alias/commerce-rds-key-eu
```

3. Set up cross-region replication in the console or via DMS.

For Backtrack, configure it on the primary after creation.
