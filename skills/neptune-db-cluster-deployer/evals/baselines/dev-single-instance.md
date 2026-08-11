# Baseline (no-skill) — dev-single-instance

> This is the response a model produces **without** the skill
> definition. It creates a single-instance dev cluster but misses
> the explicit "NO failover" notation, the neptune_enforce_ssl=1
> hygiene flag, and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Here's how to create a dev Neptune cluster:

```bash
aws neptune create-db-cluster \
  --db-cluster-identifier dev-graph \
  --engine neptune \
  --db-instance-class db.r6g.large
```

That should work for functional testing.
