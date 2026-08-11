# Baseline (no-skill) — missing-domain-endpoint

> This is the response a model produces **without** the skill
> definition. It proceeds to create the index without flagging the
> missing domain endpoint and auth credentials, leading to API call
> failures. Does not emit a PREREQUISITES_MISSING verdict. Generated
> for with-skill-vs-baseline comparison.

---

Sure, here is the index:

```json
PUT /my-index
{
  "settings": { "number_of_shards": 5, "number_of_replicas": 1 }
}
```
