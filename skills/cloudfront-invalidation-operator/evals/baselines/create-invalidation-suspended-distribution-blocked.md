# Baseline (no-skill) response: create-invalidation-suspended-distribution-blocked

This file captures what a generic assistant produces WITHOUT the
cloudfront-invalidation-operator skill loaded.

---

To invalidate the cache on your distribution, run:

```bash
aws cloudfront create-invalidation \
  --distribution-id E3SUSPENDED001 \
  --invalidation-batch '{"CallerReference":"inv-20260810-003",
    "Paths":{"Quantity":1,"Items":["/*"]}}'
```

This will clear the edge cache for all objects.
