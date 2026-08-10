# Baseline (no-skill) — missing-db-family

> This is the response a model produces **without** the skill definition.
> It picks an arbitrary family (e.g., postgres15) without flagging the
> missing engine version as a prerequisite gap. It does not produce the
> PREREQUISITES_MISSING verdict and does not ask the user to verify
> their DB engine version before proceeding.

---

Here's how to create your parameter group. I'll assume PostgreSQL:

```bash
aws rds create-db-parameter-group \
  --db-parameter-group-name app-pg-params \
  --db-parameter-group-family postgres15 \
  --description "App parameters"
```

You can check your DB engine with `describe-db-instances`.
