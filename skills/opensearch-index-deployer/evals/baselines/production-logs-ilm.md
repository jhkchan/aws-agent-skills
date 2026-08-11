# Baseline (no-skill) — production-logs-ilm

> This is the response a model produces **without** the skill
> definition. It creates the index but misses the ILM rollover
> dependency on the rollover alias having is_write_index=true, the
> shard sizing heuristic (10-50 GB per shard), the strict dynamic
> mapping recommendation, the index template application order
> (before index creation), and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the index:

```json
PUT /logs-app
{
  "settings": { "number_of_shards": 5, "number_of_replicas": 1 }
}
```

Then create an ILM policy and attach it.
