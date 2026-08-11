# Baseline (no-skill) response: cached-error-response-stale-502-after-recovery

---

Your CloudFront distribution is still serving 502 errors. The origin
appears healthy based on direct probes. Possible explanations:

1. CloudFront may still be caching old error responses.
2. Wait a few minutes for the cache to expire.
3. Try creating an invalidation to clear the cache.
4. Check the Custom Error Response configuration in the distribution.

You can invalidate the cache with:
`aws cloudfront create-invalidation --distribution-id <id> --paths '/*'`
