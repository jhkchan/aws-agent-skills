# Baseline (no-skill) — production-multi-az-changestreams

> This is the response a model produces **without** the skill
> definition. It creates the cluster but misses the change streams
> parameter group requirement (needs change_streams_log_retention_duration
> > 0 and a reboot), the storage autoscaling ceiling warning (hitting it
> causes STORAGE_FULL), the no-query-optimizer indexing requirement
> (indexes must be created before queries), and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the cluster:

```bash
aws docdb create-db-cluster \
  --db-cluster-identifier orders-docdb \
  --engine docdb \
  --engine-version 5.0.0 \
  --master-username admin \
  --master-user-password 'Password123!' \
  --db-subnet-group-name docdb-subnet-group \
  --vpc-security-group-ids sg-docdb-001
```

Then create instances:

```bash
aws docdb create-db-instance \
  --db-instance-identifier orders-docdb-primary \
  --db-instance-class db.r5.large \
  --engine docdb \
  --db-cluster-identifier orders-docdb
```

Then connect and use it.
