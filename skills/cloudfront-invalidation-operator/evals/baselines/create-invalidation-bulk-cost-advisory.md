# Baseline (no-skill) response: create-invalidation-bulk-cost-advisory

This file captures what a generic assistant produces WITHOUT the
cloudfront-invalidation-operator skill loaded.

---

To invalidate those 1,247 paths, run:

```bash
aws cloudfront create-invalidation \
  --distribution-id E2XYZ5678GHIJ9 \
  --invalidation-batch file://invalidation-batch.json
```

This will clear the cache for all listed paths. You can verify
the status with get-invalidation afterwards.
