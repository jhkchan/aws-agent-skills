# Baseline (no-skill) response: create-invalidation-staging-continuous-deployment-ready

This file captures what a generic assistant produces WITHOUT the
cloudfront-invalidation-operator skill loaded.

---

To invalidate /api/v2/* on your CloudFront distribution, run:

```bash
aws cloudfront create-invalidation \
  --distribution-id E1ABC2DEF3GHI4 \
  --invalidation-batch '{"CallerReference":"stg-20260810-001",
    "Paths":{"Quantity":1,"Items":["/api/v2/*"]}}'
```

This will clear the edge cache for all objects under /api/v2/.
