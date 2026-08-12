# Baseline (no-skill) — schema-change-in-green

> This is the response a model produces **without** the skill
> definition. It applies the schema change directly on the production
> database (blue) instead of creating a Blue/Green Deployment and
> making changes in green, misses the replication from blue to green,
> the green validation step, the blue-frozen requirement, and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

To add the column to your orders table:

```bash
mysql -h prod-orders-db.xxx.us-east-1.rds.amazonaws.com \
  -u admin -p \
  -e "ALTER TABLE orders ADD COLUMN status_code INT DEFAULT 0;"
```

And update the parameter group:

```bash
aws rds modify-db-instance \
  --db-instance-identifier prod-orders-db \
  --db-parameter-group-name prod-mysql80-tuned \
  --apply-immediately
```
