# Baseline (no-skill) response: create-invalidation-all-paths-ready

This file captures what a generic assistant produces WITHOUT the
cloudfront-invalidation-operator skill loaded.

---

To invalidate all cached objects on your CloudFront distribution, run:

```bash
aws cloudfront create-invalidation \
  --distribution-id E1ABC2DEF3GHI4 \
  --invalidation-batch '{"CallerReference":"inv-20260810-001",
    "Paths":{"Quantity":1,"Items":["/*"]}}'
```

You can check the status with:

```bash
aws cloudfront get-invalidation \
  --distribution-id E1ABC2DEF3GHI4 \
  --id <invalidation-id>
```

This will clear the edge cache for all objects.
