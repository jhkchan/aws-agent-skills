# Baseline (no-skill) response: insufficient-context-need-distribution-id

This file captures what a generic assistant produces WITHOUT the
cloudfront-cache-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, category-aware walk,
specific remediation).

---

It sounds like your CloudFront distribution is not caching content. To
help diagnose this, I need more information:

1. What is your CloudFront distribution ID or domain name?
2. What is the origin (S3 bucket, ALB, etc.)?
3. What cache policy are you using?
4. What do the `curl -I` response headers show?

Once you provide this, I can help you figure out why caching is not
working. Common causes include origin headers that prevent caching,
cache policy TTL set to 0, or too many parameters in the cache key.

In the meantime, you could try using the `CachingOptimized` managed
policy for static content, or check if your origin is sending
`Cache-Control: no-store`.
