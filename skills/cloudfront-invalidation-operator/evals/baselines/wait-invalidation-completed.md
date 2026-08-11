# Baseline (no-skill) response: wait-invalidation-completed

This file captures what a generic assistant produces WITHOUT the
cloudfront-invalidation-operator skill loaded.

---

The invalidation I2XYZ5678UVW90 has status Completed. Your cache
should be cleared for the /* path. You can verify by checking the
status:

```bash
aws cloudfront get-invalidation \
  --distribution-id E1ABC2DEF3GHI4 \
  --id I2XYZ5678UVW90
```

Since it shows Completed, the invalidation is done.
