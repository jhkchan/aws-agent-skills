# Baseline (no-skill) — elasticache-redirect-boundary

> This is the response a model produces **without** the skill
> definition. It provisions a MemoryDB cluster for a disposable cache
> workload without recognizing that ElastiCache is the cheaper,
> correct service for non-durable data. A baseline model conflates
> the two services. Generated for with-skill-vs-baseline comparison.

---

Here's how to create your MemoryDB cache:

```bash
aws memorydb create-cluster \
  --cluster-name app-cache \
  --node-type db.r6g.large \
  --acl-name open-access
```

That should give you a Redis cache. Let me know if you need anything
else.
