# Baseline (no-skill) — aurora-postgres-production

> This is the response a model produces **without** the skill definition.
> It produces generic create-db-cluster commands but misses the cluster-vs-
> instance distinction (encryption/deletion-protection are cluster-scoped),
> the 3-AZ reader topology rationale, the pgaudit option group wiring, the
> force_ssl defense-in-depth, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

To create an Aurora PostgreSQL cluster:

1. Create the cluster:
```bash
aws rds create-db-cluster \
  --db-cluster-identifier prod-orders-pg \
  --engine aurora-postgresql \
  --engine-version 16.3 \
  --master-username admin \
  --master-user-password <password> \
  --vpc-security-group-ids sg-prod-db \
  --db-subnet-group-name prod-db-subnet-group
```

2. Create the writer:
```bash
aws rds create-db-instance \
  --db-instance-identifier prod-orders-pg-0 \
  --db-instance-class db.r7g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier prod-orders-pg
```

3. Add readers:
```bash
aws rds create-db-instance \
  --db-instance-identifier prod-orders-pg-1 \
  --db-instance-class db.r7g.large \
  --engine aurora-postgresql \
  --db-cluster-identifier prod-orders-pg
```

4. Enable encryption, backups, Performance Insights in the console
   after creation.

For force_ssl and other tuning, you can configure a parameter group.
