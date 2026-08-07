# Baseline (no-skill) response: user-agent-in-cache-key

This file captures what a generic assistant produces WITHOUT the
cloudfront-cache-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your CloudFront cache hit ratio is only 4% for static assets, which is
very low. Since your static files have hashed names and the origin sends
`Cache-Control: public, max-age=86400`, the caching should work well.

The low hit ratio could be caused by a few things:

1. Your cache policy might be including too many parameters in the cache
   key. Check if you have any headers or cookies included that create
   many variations.

2. Your traffic might have a long-tail pattern where each asset is only
   requested once.

3. Your TTL might be too short.

Try increasing the TTL and check your cache policy settings. You can
also try using the `CachingOptimized` managed policy for your static
assets:

```bash
aws cloudfront update-distribution --id E2B3C4D5E6 \
  --if-match <ETag> \
  --distribution-config file://config.json
```

Monitor the hit ratio after the change.
