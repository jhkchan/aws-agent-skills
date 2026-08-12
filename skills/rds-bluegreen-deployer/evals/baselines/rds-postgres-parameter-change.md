# Baseline (no-skill) — rds-postgres-parameter-change

> This is the response a model produces **without** the skill
> definition. It suggests modifying the parameter group directly on the
> production instance instead of using Blue/Green for zero-downtime,
> misses the green validation step, the replication verification, the
> endpoint DNS auto-follow behavior, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

To change the parameter group on your PostgreSQL instance:

```bash
aws rds modify-db-instance \
  --db-instance-identifier prod-pg-db \
  --db-parameter-group-name prod-pg14-tuned \
  --apply-immediately
```

This will apply the new parameters right away.
