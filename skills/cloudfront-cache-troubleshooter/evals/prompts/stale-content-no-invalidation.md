# Eval prompt: stale-content-no-invalidation

Diagnose the following CloudFront caching issue. Walk the cache diagnostic
decision tree and emit the standard VERDICT block (DISTRIBUTION, VERDICT,
ROOT_CAUSE, CACHE_ISSUE, EVIDENCE, ROOT_CAUSE_CATALOG, REMEDIATION).

## Scenario

A CloudFront distribution `E3C4D5E6F7` (`d789.cloudfront.net`) serves
stale content for the path `/api/config.json`. The S3 origin was updated
30 minutes ago with new config data, but CloudFront still serves the old
version. The operator expected the content to update immediately after
the S3 push.

## Known facts

- `get-distribution-config` shows:
  - Default cache behavior targets S3 origin `config-bucket`.
  - `CachePolicyId`: custom policy `P2B3C4D5E6F7G8H9`.
  - No Lambda@Edge functions. No WAF.
- `get-cache-policy` for the custom policy:
  - `OriginCacheControlHeaders: respect`
  - `MinTTL: 60`, `DefaultTTL: 3600`, `MaxTTL: 86400`
  - No headers, cookies, or query strings in the cache key.
- `curl -I https://config-bucket.s3.amazonaws.com/api/config.json`
  returns:
  ```
  Cache-Control: public, max-age=86400
  Content-Type: application/json
  ```
- `curl -I https://d789.cloudfront.net/api/config.json` returns:
  ```
  x-cache: Hit from cloudfront
  Age: 7200
  Cache-Control: public, max-age=86400
  ```
- `list-invalidations` for the distribution: the most recent invalidation
  was 7 days ago (for a different path). No invalidation was sent after
  the S3 update 30 minutes ago.
- The S3 object was updated via `aws s3 cp new-config.json
  s3://config-bucket/api/config.json` 30 minutes ago, confirmed by
  `aws s3api head-object` showing `LastModified: 2026-08-07T10:00:00Z`.

## Symptom

CloudFront serves the cached (stale) version of `/api/config.json`
because the TTL (24 hours from origin `max-age=86400`) has not expired
and no invalidation was sent after the S3 update. The `Age: 7200` header
confirms the object has been cached for 2 hours. This is expected
behaviour — CloudFront caches until the TTL expires or an invalidation
clears the cache.
