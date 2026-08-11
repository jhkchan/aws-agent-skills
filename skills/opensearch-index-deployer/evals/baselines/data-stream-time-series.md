# Baseline (no-skill) — data-stream-time-series

> This is the response a model produces **without** the skill
> definition. It creates a regular index instead of a data stream,
> misses the data stream template requirement, the append-only
> semantics, the backing index lifecycle, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create an index for metrics:

```json
PUT /metrics-ds
{
  "settings": { "number_of_shards": 10, "number_of_replicas": 1 }
}
```

Then ingest your metrics data into it.
