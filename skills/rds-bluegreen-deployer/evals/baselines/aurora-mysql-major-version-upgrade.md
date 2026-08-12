# Baseline (no-skill) — aurora-mysql-major-version-upgrade

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the green environment
> validation step (the most critical pre-switchover checkpoint), the
> 2x cost implication during the Blue/Green lifecycle, the replication
> lag verification before switchover, the switchover downtime
> characteristics (1-minute DNS switch), the endpoint CNAME auto-follow
> behavior, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

To upgrade Aurora MySQL from 5.7 to 8.0:

```bash
aws rds create-blue-green-deployment \
  --source arn:aws:rds:us-east-1:123456789012:cluster:prod-mysql-db \
  --target-engine-version "8.0"
```

Wait for it to be available, then switch over.
