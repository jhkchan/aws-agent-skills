# Baseline (no-skill) — analytics-redirect-boundary

> This is the response a model produces **without** the skill
> definition. It provisions a Neptune DB cluster without recognizing
> that PageRank/connected-components is an analytical (OLAP) workload
> that belongs in Neptune Analytics, not Neptune DB. Neptune DB has no
> built-in algorithm library — a baseline model conflates the two
> services. Generated for with-skill-vs-baseline comparison.

---

Here's how to create your Neptune cluster for PageRank:

```bash
aws neptune create-db-cluster \
  --db-cluster-identifier research-graph \
  --engine neptune \
  --db-instance-class db.x2gdb.16xlarge

aws neptune create-db-instance \
  --db-instance-identifier research-graph-1 \
  --db-cluster-identifier research-graph \
  --db-instance-class db.x2gdb.16xlarge
```

You can then run PageRank by writing it as a Gremlin traversal.

That should give you what you need.
