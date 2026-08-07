# CloudFront Cache Key Model — Reference

Supplementary reference for the CloudFront Cache Troubleshooter skill.
Walks the full cache key model, cache policy options, and worked examples
per issue category.

## Cache key anatomy

```
cache key = URL path (always)
          + query strings (if QueryStringBehavior includes them)
          + headers (if HeaderBehavior includes them)
          + cookies (if CookieBehavior includes them)
```

Each unique combination of values for the included components produces a
distinct cache entry. Including a high-cardinality component (User-Agent,
Authorization, session cookie) fragments the cache.

## Cache policy structure

A cache policy (`CachePolicyConfig`) has two sections:

1. **TTL settings** — `MinTTL`, `DefaultTTL`, `MaxTTL` (in seconds).
2. **ParametersInCacheKeyAndForwardedToOrigin** — what to include in
   the cache key AND forward to the origin:
   - `HeadersConfig` — `HeaderBehavior` (`none`, `whitelist`, `allExcept`,
     `allViewer`)
   - `CookiesConfig` — `CookieBehavior` (`none`, `whitelist`, `allExcept`,
     `all`)
   - `QueryStringsConfig` — `QueryStringBehavior` (`none`, `whitelist`,
     `allExcept`, `all`)
   - `EnableAcceptEncodingBrotli` / `EnableAcceptEncodingGzip` — whether
     to include `Accept-Encoding` in the cache key for compression

## Managed cache policies

| Policy name | Headers | Cookies | Query strings | Default TTL | Use case |
|---|---|---|---|---|---|
| `AllViewerExceptReservedHeader` | All viewer headers except CloudFront-reserved | All | All | 0 (uses origin) | General-purpose; most common |
| `AllViewer` | All viewer headers | All | All | 0 (uses origin) | When every viewer attribute matters |
| `CachingDisabled` | None | None | None | 0 | Dynamic, non-cacheable content |
| `CachingOptimized` | None | None | None | 86400 (1 day) | Static assets (images, CSS, JS) |
| `CachingOptimizedForUncompressedCompressedObjects` | None | None | None | 86400 | Static assets without compression |
| `Elemental-MediaPackage` | Tailored | Tailored | Tailored | Tailored | MediaPackage video origins |

## TTL precedence

CloudFront determines the TTL for a cached object in this order:

1. If the cache policy `OriginCacheControlHeaders` is set to override,
   use the cache policy's `DefaultTTL` (clamped between `MinTTL` and
   `MaxTTL`).
2. If the cache policy respects origin headers, check the origin's
   `Cache-Control` response header:
   - `max-age=<seconds>`: TTL = `max-age`, clamped between `MinTTL` and
     `MaxTTL`.
   - `s-maxage=<seconds>`: TTL = `s-maxage` (takes precedence over
     `max-age`), clamped.
   - `no-store` or `no-cache`: TTL = 0 (not cached).
   - `Expires` header: TTL = `Expires - now`, clamped.
3. If no origin cache directive, use the cache policy's `DefaultTTL`.

## Worked examples

### Example 1: Origin sends `no-store`, policy has `DefaultTTL=3600`

```
Origin response: Cache-Control: no-store
Cache policy: MinTTL=0, DefaultTTL=3600, MaxTTL=86400
              OriginCacheControlHeaders: respect
Result: CloudFront does NOT cache (origin no-store overrides TTL).
Fix: remove no-store from the origin, OR set policy to override origin
     headers.
```

### Example 2: Origin sends `max-age=60`, policy has `MaxTTL=3600`

```
Origin response: Cache-Control: public, max-age=60
Cache policy: MinTTL=0, DefaultTTL=3600, MaxTTL=3600
              OriginCacheControlHeaders: respect
Result: TTL = max(60, MinTTL) = 60 seconds (origin max-age is respected,
        clamped to MinTTL).
Fix for longer caching: raise origin max-age to 3600, OR set MinTTL=3600
     in the policy (forces at least 3600 even if origin says 60).
```

### Example 3: `User-Agent` in cache key, 10,000 distinct values

```
Cache policy: Headers whitelist [User-Agent]
Result: cache key includes User-Agent; 10,000 distinct User-Agents =
        10,000 cache entries for the same URL. Hit ratio ~0%.
Fix: remove User-Agent from the whitelist. If response varies by client
     type, normalize (e.g., "mobile" vs "desktop") and include the
     normalized header instead.
```

### Example 4: All cookies in cache key

```
Cache policy: CookieBehavior: all
Result: every unique cookie combination = a distinct cache entry.
        Session cookies, analytics cookies, A/B test cookies all fragment.
Fix: switch to whitelist with only cookies that affect the response
     (e.g., "theme", "lang").
```

### Example 5: `Accept-Encoding` not in cache key

```
Cache policy: HeadersConfig none; EnableAcceptEncodingGzip false
Result: CloudFront does not include Accept-Encoding in the cache key.
        A request from a browser (Accept-Encoding: gzip) and from curl
        (no Accept-Encoding) produce the same cache key. CloudFront may
        serve a compressed response to curl or uncompressed to the
        browser.
Fix: enable EnableAcceptEncodingGzip (and Brotli) in the cache policy,
     OR use the managed AllViewerExceptReservedHeader policy (includes
     Accept-Encoding by default).
```

## Cache behavior vs cache policy

A **cache behavior** routes requests to an origin and attaches a cache
policy. A distribution has one **default cache behavior** (matches all
paths) and zero or more **additional cache behaviors** (match specific
path patterns).

```
Distribution
  ├── DefaultCacheBehavior (path: *)
  │     ├── TargetOriginId: origin-1
  │     ├── CachePolicyId: <CachingOptimized>
  │     └── LambdaFunctionAssociations: []
  ├── CacheBehavior (path: /api/*)
  │     ├── TargetOriginId: origin-2
  │     ├── CachePolicyId: <CachingDisabled>
  │     └── LambdaFunctionAssociations: [viewer-request]
  └── CacheBehavior (path: /images/*)
        ├── TargetOriginId: origin-1
        ├── CachePolicyId: <CachingOptimized>
        └── LambdaFunctionAssociations: []
```

A caching issue on `/api/*` but not on `/images/*` means the `/api/*`
cache behavior's policy or Lambda@Edge is the cause — not the default
behavior.

## Origin types and caching implications

| Origin type | Default caching behavior | Notes |
|---|---|---|
| S3 | Objects cached per their metadata | Set `Cache-Control` on the S3 object |
| ALB / EC2 / on-prem | Response headers from the app | App must send `Cache-Control` |
| MediaPackage / MediaLive | Tailored managed policy | Use the Elemental-MediaPackage policy |
| S3 static website | Same as S3 | Prefer S3 REST API origin over website endpoint |

## CloudFront access log fields for cache diagnosis

| Field | What it tells you |
|---|---|
| `x-edge-result-type` | `Hit`, `Miss`, `RefreshHit`, `RefreshMiss`, `Error`, `Denied` |
| `x-edge-response-result-type` | Final result after error handling |
| `x-cache` | `Hit from cloudfront`, `Miss from cloudfront`, `RefreshHit from cloudfront` |
| `cs-cookie` | Cookies sent by the viewer (for cache key analysis) |
| `cs-accept-encoding` | Accept-Encoding header (for compression analysis) |
| `cs-user-agent` | User-Agent (for cache key bloat analysis) |
| `sc-status` | HTTP status code returned to the viewer |
| `sc-bytes` | Bytes returned (compare Hit vs Miss for bandwidth analysis) |
| `time-taken` | Seconds from request to response (Hit should be lower than Miss) |

## Diagnostic flow for any caching issue

```
START
  │
  ▼
curl -I to the ORIGIN: what Cache-Control does the origin send?
  ├── no-store / no-cache / max-age=0 ──→ ORIGIN_NO_CACHE / ORIGIN_NO_STORE
  ├── max-age=<long> + content stale    ──→ STALE_NO_INVALIDATION / TTL_TOO_LONG
  └── public, max-age=<reasonable>      ──→ Origin is OK; check CloudFront
  │
  ▼
get-cache-policy: what is in the cache key?
  ├── User-Agent / Authorization in headers ──→ CACHE_KEY_BLOAT
  ├── CookieBehavior: all                   ──→ CACHE_KEY_BLOAT
  ├── TTL = 0 / CachingDisabled             ──→ CACHE_POLICY_TOO_NARROW
  └── Accept-Encoding not included          ──→ COMPRESSION_CACHE_KEY
  │
  ▼
Access logs: what is x-edge-result-type?
  ├── Miss on every request                 ──→ CACHE_MISS_ALWAYS (origin or policy)
  ├── Error with 403                        ──→ WAF_BLOCK / LAMBDA_EDGE_MUTATION
  ├── Error with 404                        ──→ ORIGIN_ERROR (cached 404)
  └── Mix of Hit and Miss                   ──→ LOW_HIT_RATIO (TTL or cache key)
  │
  ▼
Check WAF and Lambda@Edge:
  ├── WAF web ACL on distribution           ──→ WAF_BLOCK
  └── Lambda@Edge on viewer-response        ──→ LAMBDA_EDGE_MUTATION
  │
  ▼
NEED_MORE_INFO — gather access logs or cache policy details
```
