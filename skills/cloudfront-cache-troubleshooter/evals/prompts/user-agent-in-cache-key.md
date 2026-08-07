# Eval prompt: user-agent-in-cache-key

Diagnose the following CloudFront caching issue. Walk the cache diagnostic
decision tree and emit the standard VERDICT block (DISTRIBUTION, VERDICT,
ROOT_CAUSE, CACHE_ISSUE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A CloudFront distribution `E2B3C4D5E6` (`d456.cloudfront.net`) has a
cache hit ratio of 4% for the `/static/*` path pattern, well below the
target of 90%. The origin load is elevated proportionally.

## Known facts

- `get-distribution-config` shows a cache behavior for `/static/*` with:
  - `CachePolicyId`: a custom policy `P1A2B3C4D5E6F7G8`
  - `TargetOriginId`: S3 origin `static-assets-bucket`
- `get-cache-policy` for the custom policy:
  - `HeadersConfig.HeaderBehavior: whitelist`
  - `HeadersConfig.Headers.Items: ["User-Agent"]`
  - `CookiesConfig.CookieBehavior: none`
  - `QueryStringsConfig.QueryStringBehavior: none`
  - `MinTTL: 1`, `DefaultTTL: 86400`, `MaxTTL: 31536000`
- `curl -I https://static-assets-bucket.s3.amazonaws.com/app.abc123.js`
  returns:
  ```
  Cache-Control: public, max-age=86400
  Content-Type: application/javascript
  ```
- CloudFront access logs: `x-edge-result-type: Miss` on 95% of requests
  to `/static/*`; the 5% hits come from repeated User-Agent strings
  (e.g., `curl/8.0`).
- CloudWatch `CacheHitRate` for the distribution: 4% (global average);
  for `/static/*` specifically: ~3-5%.
- The static assets have hashed filenames (e.g., `app.abc123.js`,
  `vendor.def456.css`) and do NOT vary by client type. A mobile browser
  and a desktop browser receive the same file.

## Symptom

Low cache hit ratio (4% vs 90% target) for static assets that do not
vary by client. The `User-Agent` header in the cache policy whitelist
creates a distinct cache entry for each of the thousands of distinct
User-Agent strings, fragmenting the cache.
