# Baseline (no-skill) — data-tiering-cost-optimized

> This is the response a model produces **without** the skill
> definition. It creates a cluster but misses the data-tiering one-way
> door (cannot enable post-creation), the db.r6gd requirement for
> tiering, the hot/cold latency tradeoff, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Here's how to create a MemoryDB cluster for your analytics workload:

```bash
aws memorydb create-cluster \
  --cluster-name analytics-db \
  --node-type db.r6g.24xlarge \
  --acl-name open-access \
  --num-shards 3
```

You can enable data tiering later if you need it.
