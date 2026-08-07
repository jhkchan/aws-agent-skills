# Baseline (no-skill) response: stale-content-no-invalidation

This file captures what a generic assistant produces WITHOUT the
cloudfront-cache-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

Your CloudFront distribution is serving stale content. The `Age: 7200`
header means the object has been cached for 2 hours, and your origin
sends `Cache-Control: public, max-age=86400` (24 hours), so CloudFront
will keep serving the cached version until the TTL expires.

To fix this, you need to invalidate the cached content so CloudFront
fetches the new version from the origin:

```bash
aws cloudfront create-invalidation --distribution-id E3C4D5E6F7 \
  --paths "/api/config.json"
```

After the invalidation completes, CloudFront will fetch the updated
content from S3 on the next request. You should also consider adding
an invalidation step to your deployment process so this happens
automatically in the future.

If you want content to update faster without invalidation, lower the
`max-age` on the origin to something like 300 (5 minutes).
