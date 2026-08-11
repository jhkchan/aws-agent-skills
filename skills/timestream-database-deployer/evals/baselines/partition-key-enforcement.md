# Baseline (no-skill) — partition-key-enforcement

> This is the response a model produces **without** the skill
> definition. It creates the table but does not configure partition
> key enforcement, does not explain the query performance trade-off,
> and does not emit the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create the database and table:

```bash
aws timestream-write create-database --database-name MetricsDB
aws timestream-write create-table --database-name MetricsDB --table-name HighCardinalityMetrics
```

That should cover it.
