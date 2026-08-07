# Baseline (no-skill) — mysql-multi-az-commerce

> This is the response a model produces **without** the skill definition.
> It produces a create-db-instance command but misses the encryption-at-
> creation immutability, the parameter group tuning rationale, the IOPS-
> to-storage ratio check (6000 IOPS / 200 GB = 30:1, within MySQL's 500:1
> cap), and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

To create a MySQL Multi-AZ instance:

```bash
aws rds create-db-instance \
  --db-instance-identifier commerce-mysql-prod \
  --db-instance-class db.m7g.large \
  --engine mysql \
  --engine-version 8.0 \
  --master-username admin \
  --master-user-password <password> \
  --allocated-storage 200 \
  --storage-type gp3 \
  --multi-az \
  --vpc-security-group-ids sg-commerce-db \
  --db-subnet-group-name prod-db-subnet-group \
  --backup-retention-period 7
```

After creation you can enable Performance Insights and Enhanced
Monitoring in the console. For parameter group tuning, you can
modify innodb_buffer_pool_size and max_connections via a custom
parameter group.
