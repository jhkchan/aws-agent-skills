# Baseline (no-skill) — postgres15-common-tuning

> This is the response a model produces **without** the skill definition.
> It produces a basic create-db-parameter-group command but misses the
> static vs dynamic distinction (does not flag that shared_buffers and
> max_connections require a reboot), the formula syntax
> ({DBInstanceClassMemory/4}), the ApplyMethod field, the association
> step (ModifyDBInstance), and the structured checklist output format.

---

Here's how to create your PostgreSQL parameter group:

```bash
aws rds create-db-parameter-group \
  --db-parameter-group-name payments-pg15-params \
  --db-parameter-group-family postgres15 \
  --description "Payments PG15 params"
```

Then set your parameters with `modify-db-parameter-group` and
associate it with your DB instance.
