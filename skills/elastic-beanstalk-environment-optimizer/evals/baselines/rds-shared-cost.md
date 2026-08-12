# Baseline (no-skill) — rds-shared-cost

> This is the response a model produces **without** the skill
> definition. It suggests using smaller RDS instances but misses the
> shared external RDS strategy (one instance serving all three
> environments with separate databases), the Graviton cost advantage
> (db.t4g.medium ~20% cheaper), and the lifecycle decoupling benefit
> (detaching RDS from environment prevents accidental deletion).
> Generated for with-skill-vs-baseline comparison.

---

You can try using smaller RDS instances for dev environments.
Consider db.t3.small instead of db.t3.medium.

```bash
aws rds modify-db-instance \
  --db-instance-identifier my-dev-db-1 \
  --db-instance-class db.t3.small \
  --apply-immediately
```

This saves about $20 per instance per month.
