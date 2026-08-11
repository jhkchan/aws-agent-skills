# Baseline (no-skill) — sql-server-core-tracking

> This is the response a model produces **without** the skill
> definition. It sets the count but misses the Core counting type
> (often defaults to vCPU), the SQL Server-specific coreFactor rule,
> and the hard-limit enforcement flag. Does not emit a
> READY_TO_DEPLOY checklist. Generated for with-skill-vs-baseline
> comparison.

---

```bash
aws license-manager create-license-configuration \
  --name "sql-server" \
  --license-count 24
```

That should cover your SQL Server licensing.
