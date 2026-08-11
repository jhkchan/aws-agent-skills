# Baseline (no-skill) — knn-vector-search

> This is the response a model produces **without** the skill
> definition. It creates a vector index but misses that index.knn
> must be set at creation time (immutable), the method/space_type
> selection, the ef_search setting, and the READY_TO_DEPLOY
> checklist format. Generated for with-skill-vs-baseline comparison.

---

Create the index with a knn_vector field:

```json
PUT /vector-search-v1
{
  "mappings": {
    "properties": {
      "embedding": { "type": "knn_vector", "dimension": 768 }
    }
  }
}
```
