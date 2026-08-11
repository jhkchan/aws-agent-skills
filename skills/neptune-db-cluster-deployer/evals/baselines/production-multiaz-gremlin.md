# Baseline (no-skill) — production-multiaz-gremlin

> This is the response a model produces **without** the skill definition.
> It lists CLI commands but misses the encryption-immutability warning,
> the neptune_enforce_ssl-at-creation pattern, the 60% buffer cache
> rule, the Neptune Analytics boundary, the single-writer bottleneck,
> and the READY_TO_DEPLOY checklist format. Generated for with-skill-
> vs-baseline comparison.

---

Here's how to create a Neptune cluster:

1. Create the cluster:
```bash
aws neptune create-db-cluster \
  --db-cluster-identifier prod-graph \
  --engine neptune \
  --db-instance-class db.r6g.8xlarge
```

2. Add instances:
```bash
aws neptune create-db-instance \
  --db-instance-identifier prod-graph-1 \
  --db-cluster-identifier prod-graph
```

3. Add encryption:
```bash
aws neptune modify-db-cluster \
  --db-cluster-identifier prod-graph \
  --kms-key-id alias/prod-graph-kms
```

That should cover it.
