# Baseline (no-skill) — missing-cmk-and-subnet-group

> This is the response a model produces **without** the skill definition.
> It blindly issues a create-db-instance command without flagging the
> missing DB subnet group or the missing KMS CMK — exactly the
> prerequisites the skill is designed to catch. Generated for
> with-skill-vs-baseline comparison.

---

Here's how to create your PostgreSQL instance:

```bash
aws rds create-db-instance \
  --db-instance-identifier users-db-prod \
  --db-instance-class db.m7g.large \
  --engine postgres \
  --engine-version 16 \
  --master-username admin \
  --master-user-password <password> \
  --allocated-storage 50 \
  --storage-encrypted
```

You'll need to specify a subnet group and KMS key when prompted.
After creation you can enable backups and deletion protection.
