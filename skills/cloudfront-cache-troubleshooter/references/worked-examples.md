# CloudFront Cache Troubleshooter — Worked Examples and Advanced Patterns

## Worked example 1: Origin sending no-store

```text
DISTRIBUTION: E1A2B3C4D5 (d123.cloudfront.net)
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: ORIGIN_NO_STORE — the origin returns "Cache-Control: no-store"
  on all responses, which instructs CloudFront never to cache.
CACHE_ISSUE: ORIGIN_NO_STORE
EVIDENCE:
  - curl -I https://origin.example.com/api/data: response includes
    "Cache-Control: no-store"
  - curl -I https://d123.cloudfront.net/api/data: "x-cache: Miss from
    cloudfront" on every request; "Age: 0"
  - get-cache-policy: CachePolicyId is CachingOptimized
    (658327ea-f89d-4fab-a63d-7e88639e58f6), MinTTL=1, DefaultTTL=86400
    — the policy is correct; the origin header overrides it
  - CloudFront access logs: x-edge-result-type "Miss" on 100% of requests
    to /api/data/*
ROOT_CAUSE_CATALOG: #1 (origin sends no-store)
REMEDIATION:
  1. Update the origin to send Cache-Control: public, max-age=3600 for
     cacheable API responses. For an S3 origin:
     aws s3api copy-object --bucket my-bucket --key api/data.json \
       --copy-source my-bucket/api/data.json \
       --cache-control "public, max-age=3600" \
       --metadata-directive REPLACE
  2. Verify the origin header:
     curl -sI https://origin.example.com/api/data | grep -i cache-control
     Expect: "Cache-Control: public, max-age=3600"
  3. Request via CloudFront twice; the second request should show
     "x-cache: Hit from cloudfront":
     curl -sI https://d123.cloudfront.net/api/data | grep -i x-cache
```

## Worked example 2: User-Agent in cache key

```text
DISTRIBUTION: E2B3C4D5E6 (d456.cloudfront.net)
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: CACHE_KEY_BLOAT — the cache policy includes "User-Agent" in
  the cache key headers whitelist. Thousands of distinct User-Agent
  values fragment the cache so that almost every request is a Miss.
CACHE_ISSUE: CACHE_KEY_BLOAT
EVIDENCE:
  - get-cache-policy: HeadersConfig.HeaderBehavior "whitelist",
    HeadersConfig.Headers.Quantity 1, Headers.Items ["User-Agent"]
  - CloudFront access logs: x-edge-result-type "Miss" on 95% of requests
    to /static/*; the remaining 5% are hits from repeated User-Agent
    strings (e.g., curl/8.0)
  - CloudWatch CacheHitRate for /static/*: 4% (target: > 90%)
  - The /static/* behavior serves immutable assets (hashed filenames);
    response does not vary by User-Agent
ROOT_CAUSE_CATALOG: #5 (User-Agent in cache key)
REMEDIATION:
  1. Update the cache policy to remove User-Agent from the headers
     whitelist. For static assets, use the managed CachingOptimized
     policy (no headers, no cookies, no query strings):
     aws cloudfront update-distribution --id E2B3C4D5E6 \
       --if-match <ETag> \
       --distribution-config file://updated-config.json
     Where the /static/* behavior's CachePolicyId is set to
     658327ea-f89d-4fab-a63d-7e88639e58f6 (CachingOptimized).
  2. Wait for the distribution to reach Deployed status:
     aws cloudfront get-distribution --id E2B3C4D5E6 \
       --query 'Distribution.Status'
  3. Verify: request the same URL twice with different User-Agents. Both
     should return the same cached object:
     curl -sI -A "Mozilla/5.0" https://d456.cloudfront.net/static/app.js | grep x-cache
     curl -sI -A "curl/8.0" https://d456.cloudfront.net/static/app.js | grep x-cache
     Expect: second request shows "x-cache: Hit from cloudfront"
  4. Monitor CacheHitRate for /static/* over the next hour; expect
     > 90%.
```

## Expert heuristic: cache key normalization

CloudFront normalizes some request attributes before hashing them into
the cache key, but NOT others. Misjudging which is which produces
mysterious cache-key variation that looks like a bug but is by design:

| Attribute | Normalized? | Effect |
|---|---|---|
| HTTP method | YES — lowercased | `GET` and `get` share a cache entry |
| URL path | Case-sensitive (no normalization) | `/Foo` and `/foo` are DIFFERENT cache entries |
| Header NAMES in cache key | NOT normalized | `Accept-Encoding: gzip` and `accept-encoding: gzip` create DIFFERENT cache entries |
| Header VALUES in cache key | NOT normalized | `gzip` and `GZIP` create different cache entries |
| Query string parameter names | NOT normalized | `?foo=1` and `?Foo=1` are different cache entries |
| Cookie names in cache key | NOT normalized | `Session` and `session` cookies create different entries |

**The header-name case trap.** A viewer sending `Accept-Encoding: gzip`
and another sending `accept-encoding: gzip` produce TWO cache entries
even though semantically they request the same compression. Browsers
are inconsistent about header-name case — Safari has historically sent
`Accept-encoding` (lowercase 'e') while Chrome sends `Accept-Encoding`.
A cache policy that whitelists `Accept-Encoding` then fragments the
cache across browser populations.

**Fix:**
- Prefer the managed `AllViewerExceptReservedHeader` policy — it
  normalizes header handling.
- For custom policies, normalize header names at the origin or via a
  Lambda@Edge `origin-request` function before the cache lookup.
- Avoid including case-varying headers (`Accept`, `Accept-Language`) in
  the cache key unless the origin truly negotiates on them.

## Edge case: Lambda@Edge response modification invalidates cache

A Lambda@Edge function on `viewer-response` or `origin-response` runs
AFTER CloudFront has computed the cache key. The function can modify the
response headers, body, or status code — but those modifications apply
to the cached response. A function that mutates the response per-request
produces a response that does NOT match the cache key's expected content.

**Failure patterns:**
- A `viewer-response` function adding `Set-Cookie` with a unique trace
  ID per request taints the cached object — every viewer sees a
  different Set-Cookie for the "same" cache entry.
- An `origin-response` function stripping `Age` or rewriting
  `Cache-Control: no-store` rewrites the cached response.
- A function that mutates the response body (HTML rewriting) bakes that
  mutation into the cached entry.

**Diagnostic:**
- If hit ratio is near zero but cache policy and origin headers look
  correct, inspect every Lambda@Edge function on the behavior.
- Detach the function temporarily and observe whether hit ratio
  recovers — the fastest causal test.

**Fix:**
- Move per-request response-header mutations into a `viewer-response`
  function that ALSO sets `Cache-Control: private` so the variation is
  not cached at the edge.
- Never generate per-request unique values in an `origin-response`
  function.
- Separate cacheable content from per-viewer mutations using two cache
  behaviors: one cached, one uncached (`CachingDisabled`).

## Managed policy reference

| Managed policy | ID | Cache key includes | Use case |
|---|---|---|---|
| `AllViewerExceptReservedHeader` | `4135ea2d-6df8-44a3-9df3-4b5a84be39ad` | All viewer headers except reserved; all query strings; all cookies | Most common; use when response varies by viewer headers |
| `AllViewer` | — | All viewer headers; all query strings; all cookies | Use when every viewer attribute affects the response (rare) |
| `CachingDisabled` | `4135ea2d-6df8-44a3-9df3-4b5a84be39ad` | Nothing (TTL = 0) | Use for dynamic, non-cacheable content |
| `CachingOptimized` | `658327ea-f89d-4fab-a63d-7e88639e58f6` | No headers, no query strings, no cookies; high TTL | Use for static assets (images, CSS, JS) |
| `Elemental-MediaPackage` | — | Tailored for MediaPackage origins | Use for MediaPackage video |
