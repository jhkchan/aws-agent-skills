# Baseline (no-skill) — t3-development-cluster

> This is the response a model produces **without** the skill
> definition. It creates the cluster but does not flag that t3.medium
> is burstable and NOT recommended for production, does not note the
> single-instance setup lacks failover, and omits the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the dev cluster:

```bash
aws docdb create-db-cluster \
  --db-cluster-identifier dev-docdb \
  --engine docdb \
  --engine-version 4.0.0 \
  --master-username admin \
  --master-user-password 'Password123!' \
  --db-subnet-group-name docdb-dev-subnet \
  --vpc-security-group-ids sg-dev-docdb \
  --backup-retention-period 1
```

Then add a t3 instance:

```bash
aws docdb create-db-instance \
  --db-instance-identifier dev-docdb-1 \
  --db-instance-class db.t3.medium \
  --engine docdb \
  --db-cluster-identifier dev-docdb
```
