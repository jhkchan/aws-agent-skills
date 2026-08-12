# Baseline (no-skill) — forensic-query-patterns

> This is the response a model produces **without** the skill
> definition. It creates the EDS but does not provide forensic query
> patterns, misses the time-range optimization requirement, and does
> not emit the READY_TO_DEPLOY checklist. Generated for
> with-skill-vs-baseline comparison.

---

Create the EDS:

```bash
aws cloudtrail create-event-data-store --name "forensic-eds"
```

Then query with SQL.
