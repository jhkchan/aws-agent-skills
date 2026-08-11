# Baseline (no-skill) — alias-reindex-zero-downtime

> This is the response a model produces **without** the skill
> definition. It suggests reindexing but misses the atomic alias
> swap pattern (remove + add in one POST _aliases call), the
> background reindex option (wait_for_completion=false), the
> mapping immutability explanation for why reindex is required,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Reindex from the old index to a new one:

```json
POST _reindex
{
  "source": { "index": "products-v1" },
  "dest": { "index": "products-v2" }
}
```

Then point your application to the new index.
