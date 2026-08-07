# Eval prompt: origin-no-store-header

Diagnose the following CloudFront caching issue. Walk the cache diagnostic
decision tree and emit the standard VERDICT block (DISTRIBUTION, VERDICT,
ROOT_CAUSE, CACHE_ISSUE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A CloudFront distribution `E1A2B3C4D5` (`d123.cloudfront.net`) is not
caching any responses. Every request to the distribution shows `x-cache:
Miss from cloudfront` and `Age: 0` in the response headers. The
operations team reports elevated origin load.

## Known facts

- `get-distribution-config` shows:
  - `DefaultCacheBehavior.CachePolicyId` is the managed `CachingOptimized`
    policy (`658327ea-f89d-4fab-a63d-7e88639e58f6`).
  - No Lambda@Edge functions on any behavior.
  - No WAF (`WebACLId` is empty).
  - Origin: S3 bucket `my-content-bucket.s3.amazonaws.com`.
- `get-cache-policy` for `CachingOptimized`:
  - `MinTTL: 1`, `DefaultTTL: 86400`, `MaxTTL: 31536000`
  - `HeadersConfig.HeaderBehavior: none` (no headers in cache key)
  - `CookiesConfig.CookieBehavior: none`
  - `QueryStringsConfig.QueryStringBehavior: none`
  - `OriginCacheControlHeaders: respect`
- `curl -I https://my-content-bucket.s3.amazonaws.com/index.html` returns:
  ```
  Cache-Control: no-store
  Content-Type: text/html
  ```
- `curl -I https://d123.cloudfront.net/index.html` returns:
  ```
  x-cache: Miss from cloudfront
  Age: 0
  ```
- CloudFront access logs: `x-edge-result-type: Miss` on 100% of requests.

## Symptom

Every request is a cache miss. The origin receives every request. The
cache policy is correctly configured for static content (CachingOptimized,
high TTL). The cause is the origin's `Cache-Control: no-store` header,
which overrides the cache policy and prevents caching.
