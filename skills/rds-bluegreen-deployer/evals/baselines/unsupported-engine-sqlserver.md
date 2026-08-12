# Baseline (no-skill) — unsupported-engine-sqlserver

> This is the response a model produces **without** the skill
> definition. It attempts to create the Blue/Green Deployment without
> flagging that SQL Server is an unsupported engine, which will result
> in an API error at runtime. Does not emit a PREREQUISITES_MISSING
> verdict. Generated for with-skill-vs-baseline comparison.

---

Sure, here is the Blue/Green Deployment:

```bash
aws rds create-blue-green-deployment \
  --source arn:aws:rds:us-east-1:123456789012:db:prod-sqlserver-db \
  --target-engine-version "15.00.4311.2" \
  --target-db-parameter-group-name prod-sqlserver2022-params
```

Wait for green to be available and then switch over.
