# Baseline (no-skill) — missing-subnet-group

> This is the response a model produces **without** the skill
> definition. It does not verify the subnet group exists before
> attempting cluster creation, would hit an API error at runtime, and
> does not provide the prerequisite-check / READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the cluster:

```bash
aws docdb create-db-cluster \
  --db-cluster-identifier orders-docdb \
  --engine docdb \
  --engine-version 5.0.0 \
  --master-username admin \
  --master-user-password 'Password123!' \
  --db-subnet-group-name docdb-missing-subnet \
  --vpc-security-group-ids sg-docdb-001
```

Then add instances.
