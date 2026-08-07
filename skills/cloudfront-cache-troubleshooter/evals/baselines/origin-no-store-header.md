# Baseline (no-skill) response: origin-no-store-header

This file captures what a generic assistant produces WITHOUT the
cloudfront-cache-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your CloudFront distribution is not caching any responses. Since every
request shows `x-cache: Miss from cloudfront`, CloudFront is forwarding
all requests to the origin.

You should try raising the TTL in your cache policy. Currently you have
`CachingOptimized` with a default TTL of 86400 seconds, which should be
enough. You could also try creating a custom cache policy with a higher
TTL.

Another option is to check if your origin is sending headers that prevent
caching. Sometimes origins send headers that tell CloudFront not to
cache.

To fix this, try updating your cache policy or switching to a different
managed policy. You can also try invalidating the cache and testing
again:

```bash
aws cloudfront create-invalidation --distribution-id E1A2B3C4D5 \
  --paths "/*"
```
