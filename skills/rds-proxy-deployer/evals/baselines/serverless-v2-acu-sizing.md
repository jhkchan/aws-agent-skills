# Baseline (no-skill) — serverless-v2-acu-sizing

> This is the response a model produces **without** the skill
> definition. It creates the proxy but sets MaxConnectionsPercent at the
> proxy level (wrong — it belongs on the target group), misses the ACU-
> based sizing logic, and does not note that the target must be the
> cluster for Serverless v2. Generated for with-skill-vs-baseline
> comparison.

---

Create the proxy:

```bash
aws rds create-db-proxy \
  --db-proxy-name serverless-proxy \
  --engine-family POSTGRESQL
```

Set max connections to 200 and connect.
