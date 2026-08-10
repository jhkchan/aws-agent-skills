# Baseline (no-skill) — static-param-reboot-warning

> This is the response a model produces **without** the skill definition.
> It creates the parameter group and sets parameters but does not flag
> that shared_buffers and max_connections are static (require reboot).
> It uses ApplyMethod=immediate for all parameters, which silently
> becomes pending-reboot for static ones. It misses the reboot warning
> that the operator needs to plan for.

---

Create a PostgreSQL 16 parameter group for analytics:

```bash
aws rds create-db-parameter-group \
  --db-parameter-group-name analytics-pg16-params \
  --db-parameter-group-family postgres16 \
  --description "Analytics PG16 params"
```

Set shared_buffers, max_connections, work_mem=64MB, and
random_page_cost=1.1. Use immediate apply for all parameters.
