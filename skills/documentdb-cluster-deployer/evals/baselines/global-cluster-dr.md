# Baseline (no-skill) — global-cluster-dr

> This is the response a model produces **without** the skill
> definition. It creates the global cluster but misses the critical
> caveat that failover is NOT automatic (requires scripting), that
> secondary clusters are read-only until promoted, and that the old
> primary must be deleted from the global cluster during failover.
> Omits the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the global cluster:

```bash
aws docdb create-global-cluster \
  --global-cluster-identifier orders-global \
  --region us-east-1
```

Create the primary:

```bash
aws docdb create-db-cluster \
  --db-cluster-identifier orders-docdb-primary \
  --engine docdb \
  --global-cluster-identifier orders-global \
  --master-username admin \
  --master-user-password 'Password123!' \
  --region us-east-1
```

Create the secondary:

```bash
aws docdb create-db-cluster \
  --db-cluster-identifier orders-docdb-secondary \
  --engine docdb \
  --global-cluster-identifier orders-global \
  --master-username admin \
  --master-user-password 'Password123!' \
  --region eu-west-1
```

The secondary will automatically replicate.
