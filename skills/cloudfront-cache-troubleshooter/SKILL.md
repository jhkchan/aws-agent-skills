---
name: cloudfront-cache-troubleshooter
description: >-
  Diagnoses CloudFront caching issues via a symptom-to-cause decision
  tree covering cache misses on every request, stale content served,
  unexpected cache key variation, 403/404 errors from cache, and low
  cache hit ratio. Walks Cache-Control headers from origin, cache
  policy configuration (managed vs custom), TTL settings, query
  string/header/cookie inclusion in cache key, x-edge-result-type and
  x-cache headers in access logs, Lambda@Edge response modifications,
  and WAF blocks. Emits a deterministic verdict (ROOT_CAUSE_FOUND |
  NEED_MORE_INFO | ESCALATE) with the specific cache issue and evidence
  from CloudFront access logs, cache policy inspection, and curl
  response headers. Use when content is not cached, stale content is
  served, hit ratio is low, or CloudFront returns 403/404 unexpectedly.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline diagnosis works from pasted response headers, access
  log excerpts, and cache policy JSON. Live-account diagnosis uses aws
  cloudfront get-distribution-config, get-cache-policy, aws cloudfront
  get-monitoring-sample, curl -I against the distribution and origin, and
  CloudFront access logs via aws logs get-log-events (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - CloudFront
  - caching
  - cache miss
  - cache hit ratio
  - stale content
  - cache key
  - cache policy
  - Cache-Control
  - max-age
  - no-cache
  - no-store
  - TTL
  - x-edge-result-type
  - x-cache
  - Lambda@Edge
  - origin shield
  - managed policy
  - AllViewerExceptReservedHeader
  - invalidation
  - troubleshooting
tags: [cloudfront, networking, troubleshoot, caching, cdn, cache-policy, ttl, lambda-at-edge]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 2
  supports_pipeline: true
  entry_point: false
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
  lifecycle_status: active
  when_to_use: >-
    Diagnosing CloudFront cache misses on every request, stale content
    being served, unexpected cache key variation (different content per
    user), 403/404 errors from the cache edge, low cache hit ratio with
    elevated origin load, or Lambda@Edge / WAF interference with caching;
    validating whether the root cause is origin headers, cache policy
    misconfiguration, TTL settings, invalidation gaps, or cache key bloat.
  when_not_to_use: >-
    CloudFront distribution configuration posture audits (use
    cloudfront-distribution-auditor), origin failover / multi-origin
    setup (use cloudfront-distribution-deployer), TLS certificate issues
    on the distribution (use acm-certificate-expiry-auditor), or WAF rule
    authoring (use wafv2-web-acl-auditor). This skill diagnoses caching
    root cause; it does not audit distribution security posture.
  activation_triggers:
    - "CloudFront cache miss every request"
    - "CloudFront not caching"
    - "CloudFront stale content"
    - "CloudFront content not updating"
    - "CloudFront cache hit ratio low"
    - "CloudFront origin load high"
    - "CloudFront 403 from cache"
    - "CloudFront 404 from edge"
    - "CloudFront different content per user"
    - "CloudFront cache key variation"
    - "CloudFront cache policy misconfigured"
    - "x-cache Miss from cloudfront"
    - "x-edge-result-type Miss"
    - "troubleshoot CloudFront caching"
  invocation_schema: >-
    Input: either (a) a symptom description (cache miss pattern, stale
    content report, hit-ratio drop), optionally paired with cache policy
    JSON and response headers, OR (b) a distribution ID plus caller
    context (origin URL, observed x-cache header, access log excerpt) for
    live-account diagnosis. Output: a deterministic
    DISTRIBUTION / VERDICT / ROOT_CAUSE / CACHE_ISSUE / EVIDENCE /
    REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO,
    ESCALATE} and CACHE_ISSUE ∈ {ORIGIN_NO_CACHE, ORIGIN_NO_STORE,
    CACHE_POLICY_TOO_NARROW, CACHE_KEY_BLOAT, TTL_TOO_SHORT,
    STALE_NO_INVALIDATION, ORIGIN_HEADER_OVERRIDE, LAMBDA_EDGE_MUTATION,
    WAF_BLOCK, COMPRESSION_CACHE_KEY, ORIGIN_ERROR, UNKNOWN}.
---

# CloudFront Cache Troubleshooter

## Activation

Activate this skill when the user reports a CloudFront caching issue.
Trigger phrases: "CloudFront cache miss every request", "CloudFront not
caching", "CloudFront stale content", "CloudFront content not updating",
"CloudFront cache hit ratio low", "CloudFront origin load high",
"CloudFront 403 from cache", "CloudFront 404 from edge", "CloudFront
different content per user", "CloudFront cache key variation", "CloudFront
cache policy misconfigured", "x-cache Miss from cloudfront",
"x-edge-result-type Miss", "troubleshoot CloudFront caching".

## Mindset

**One-line takeaway:** every CloudFront caching problem is a mismatch
between what the cache key captures, what the origin allows to be cached,
and what the cache policy TTL instructs. The diagnostic walk identifies
which of these three is broken.

Three facts make CloudFront cache diagnosis different from generic CDN
debugging:

- **CloudFront caches by cache key, not by URL alone.** The cache key =
  URL path + query strings (in the cache policy) + headers (in the cache
  policy) + cookies (in the cache policy). Two requests with the same URL
  but different `Accept-Encoding` headers (one not in the cache policy)
  produce the same cache key and get the same response — even if the
  origin would have returned different content. Conversely, including
  `User-Agent` in the cache policy fragments the cache so badly that hit
  ratio drops to near zero.

- **Origin `Cache-Control` headers dominate unless the cache policy
  overrides them.** If the origin sends `Cache-Control: no-cache,
  no-store`, CloudFront will not cache the response regardless of the
  cache policy TTL. The cache policy can override origin headers with
  `MinTTL` / `DefaultTTL` / `MaxTTL`, but only if
  `OriginCacheControlHeaders` handling is set to override. Operators who
  "set the TTL to 1 hour" without checking the origin headers see zero
  caching because the origin sends `no-store`.

- **`x-edge-result-type` in access logs is the ground truth.** The
  values `Hit`, `Miss`, `RefreshHit`, `RefreshMiss`, `Error`,
  `LimitExceeded`, `CapacityExceeded`, and `Denied` each name a specific
  cache behaviour. `Miss` every time means the cache key or origin
  headers prevent caching. `RefreshHit` means CloudFront revalidated
  with the origin (stale-while-revalidate). `Error` with a 502/503/504
  means the origin returned an error that CloudFront could not serve
  from cache.

## Quick reference — symptom to cache issue

| Observed signal | Cache issue | First probe |
|---|---|---|
| `x-edge-result-type: Miss` on every request; `x-cache: Miss from cloudfront` | ORIGIN_NO_CACHE / ORIGIN_NO_STORE / CACHE_POLICY_TOO_NARROW | `curl -I` to origin for `Cache-Control` headers; cache policy TTL |
| Content served is hours/days old; origin updated but CloudFront serves old | STALE_NO_INVALIDATION / TTL_TOO_LONG | Origin `Cache-Control: max-age` vs cache behavior TTL; invalidation history |
| Same URL, different content per user; hit ratio near zero | CACHE_KEY_BLOAT | Cache policy headers/cookies/query strings; look for `User-Agent`, `Authorization` |
| 403 / 404 from CloudFront; origin returns 200 | WAF_BLOCK / LAMBDA_EDGE_MUTATION | WAF web ACL on the distribution; Lambda@Edge function logs |
| Hit ratio dropping; origin load rising; no content change | CACHE_KEY_BLOAT / TTL_TOO_SHORT | Cache policy `DefaultTTL`; number of values in cache key |
| `RefreshHit` frequent; origin receives `If-Modified-Since` every request | TTL_EXPIRED / STALE-REVALIDATE | Origin `Cache-Control: max-age` vs cache behavior `MinTTL` |

See the ordered steps below for the full diagnostic walk.

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the cache signal

Before any deep walk, gather these three pieces.

| Signal | Source | Why required |
|---|---|---|
| **Distribution ID or domain** | User-provided or `aws cloudfront list-distributions` | All get-distribution-config calls need this |
| **Symptom (cache miss vs stale vs variation)** | User report + `curl -I` response headers | Drives the symptom category |
| **x-edge-result-type / x-cache from access logs** | CloudFront access logs (S3) or `curl -I` | The ground truth for what the edge is doing |

If the user has not provided the distribution ID or domain, output:

```text
DISTRIBUTION: <distribution ID or domain, or unknown>
VERDICT: NEED_MORE_INFO
REASON: Cannot diagnose without the distribution ID or domain. Identify
  the distribution with aws cloudfront list-distributions, or from the
  application's CloudFront domain in the URL.
MISSING:
  - Distribution ID or domain
  - Symptom description (cache miss every request? stale content? variation?)
  - curl -I response headers from CloudFront AND from the origin
```

If the user reports "CloudFront is not caching" but does not know which
distribution or which behavior, ask for the domain name. Then run:

```bash
aws cloudfront list-distributions \
  --query 'DistributionList.Items[*].{id:Id,domain:DomainName,aliases:Aliases.Items,enabled:Enabled}' \
  --output json

# For a specific distribution, read the cache behaviors and policies.
aws cloudfront get-distribution-config --id <distribution-id> \
  --query 'DistributionConfig.DefaultCacheBehavior.{target:TargetOriginId,cachePolicy:CachePolicyId,lam:LambdaFunctionAssociations,ttl:DefaultTTL}' \
  --output json
```

### Step 1: Identify the symptom category

Map the observed state to one of five categories.

| Category | Signature | Diagnostic step |
|---|---|---|
| **A. CACHE_MISS_ALWAYS** | `x-edge-result-type: Miss` on every request; `x-cache: Miss from cloudfront` | Step 2 |
| **B. STALE_CONTENT** | Content served is old; origin updated but CloudFront serves stale; no invalidation sent | Step 3 |
| **C. CACHE_KEY_VARIATION** | Same URL, different content per user; hit ratio near zero; many cache entries for same path | Step 4 |
| **D. ERROR_FROM_CACHE** | 403/404 from CloudFront; origin returns 200; `x-edge-result-type: Error` | Step 5 |
| **E. LOW_HIT_RATIO** | Hit ratio dropping; origin load rising; mix of Hit and Miss in logs | Step 6 |

If the symptom matches more than one category, prioritise:
CACHE_MISS_ALWAYS precedes ERROR_FROM_CACHE precedes CACHE_KEY_VARIATION
precedes STALE_CONTENT precedes LOW_HIT_RATIO. A cache-miss-every-request
is the most severe; it means zero caching.

### Step 2: CACHE_MISS_ALWAYS diagnostic

Every request is a `Miss`. CloudFront forwards to the origin every time.
The cause is one of: origin sends `no-cache` / `no-store`, the cache
policy TTL is 0, the cache policy is `CachingDisabled`, or the response
is not cacheable (e.g., `Set-Cookie` in the response with a cookie not in
the cache policy).

**Diagnostic walk:**

1. **Check the origin's `Cache-Control` headers.** This is the #1 cause.
   Run `curl -I` directly against the origin (bypassing CloudFront):

```bash
# Direct to origin (bypass CloudFront):
curl -sI https://origin.example.com/path/to/content | grep -iE 'cache-control|expires|pragma|set-cookie|content-type'

# Via CloudFront:
curl -sI https://d123.cloudfront.net/path/to/content | grep -iE 'x-cache|x-amz-cf-id|cache-control|age|set-cookie'
```

| Origin header | Effect on caching | Fix |
|---|---|---|
| `Cache-Control: no-store` | CloudFront never caches | Remove or change to `public, max-age=3600` |
| `Cache-Control: no-cache` | CloudFront revalidates every request (RefreshMiss) | Change to `public, max-age=3600` for cacheable content |
| `Cache-Control: max-age=0` | Same as `no-cache` — revalidates every request | Raise to the desired TTL |
| `Cache-Control: private` | CloudFront does not cache (intended for browser-only) | Change to `public` for CDN-cacheable content |
| `Pragma: no-cache` | Legacy HTTP/1.0 no-cache | Remove |
| `Expires: 0` or past date | Legacy HTTP/1.0 expiry | Set to a future date or use `Cache-Control: max-age` |
| `Set-Cookie` in response | CloudFront caches IF the cookie is in the cache policy; otherwise may skip caching | Add the cookie to the cache policy, or remove `Set-Cookie` from cacheable responses |

2. **Check the cache policy TTL settings.** Even if the origin allows
   caching, a cache policy with `MinTTL: 0, DefaultTTL: 0, MaxTTL: 0`
   disables caching. The managed policy `CachingDisabled` explicitly
   sets all TTLs to 0.

```bash
aws cloudfront get-cache-policy --id <cache-policy-id> \
  --query 'CachePolicy.CachePolicyConfig.{minTTL:MinTTL,defaultTTL:DefaultTTL,maxTTL:MaxTTL,headers:ParametersInCacheKeyAndForwardedToOrigin.HeadersConfig.HeaderBehavior,cookies:ParametersInCacheKeyAndForwardedToOrigin.CookiesConfig,query:ParametersInCacheKeyAndForwardedToOrigin.QueryStringsConfig}' \
  --output json
```

3. **Check if the cache policy is `CachingDisabled`.** The managed policy
   ID for `CachingDisabled` is `4135ea2d-6df8-44a3-9df3-4b5a84be39ad`. If
   this is attached to the behavior, caching is off by design.

4. **Check if the origin returns different status codes.** CloudFront
   only caches 200, 206, 301, 302, 304, 404 (optionally). A 302 redirect
   loop or a 500 error prevents caching.

**Common fix patterns:**

- Origin sends `no-store`: update the origin to send
  `Cache-Control: public, max-age=3600` (or the desired TTL). For S3
  origins, set the object metadata via `aws s3api put-object` with
  `--cache-control`.
- Cache policy TTL is 0: update the cache policy to set
  `DefaultTTL: 3600` (1 hour) or the desired value. Use the managed
  policy `CachingOptimized` (`658327ea-f89d-4fab-a63d-7e88639e58f6`) for
  static content.
- `Set-Cookie` preventing caching: either add the cookie to the cache
  policy (if the cookie affects the response), or configure the origin to
  not send `Set-Cookie` on cacheable responses.

### Step 3: STALE_CONTENT diagnostic

Content is served from cache but it is old — the origin has updated but
CloudFront continues serving the cached version. The cause is one of:
the TTL has not expired yet (expected behaviour without invalidation),
no invalidation was sent after the origin update, or the cache behavior
overrides origin headers with a longer TTL than intended.

**Diagnostic walk:**

1. **Determine whether an invalidation is needed.** CloudFront serves
   cached content until the TTL expires OR an invalidation clears the
   cache. If the origin updated but no invalidation was sent, CloudFront
   serves stale content until the TTL expires. This is expected behaviour,
   not a bug.

2. **Check the origin's `Cache-Control: max-age` vs the cache behavior
   TTL.** If the origin sends `max-age=86400` (24 hours) but the operator
   expects content to update within minutes, the TTL is too long. The fix
   is to lower the origin's `max-age` OR set the cache policy
   `MaxTTL` to override.

3. **Check the cache policy `OriginCacheControlHeaders` handling.** If
   the cache policy is set to respect origin headers
   (`OriginCacheControlHeaders: respect`), CloudFront uses the origin's
   `max-age`. If set to override, CloudFront uses the policy's
   `DefaultTTL`. A mismatch between what the operator expects and which
   mode is active produces stale content.

4. **Check invalidation history.** If the operator sent an invalidation
   for `/*` but the stale content persists, the invalidation may have
   been for a different distribution, or the invalidation is still in
   progress (check `aws cloudfront get-invalidation`).

```bash
# List recent invalidations.
aws cloudfront list-invalidations --distribution-id <id> \
  --query 'InvalidationList.Items[*].{id:Id,status:Status,paths:InvalidationBatch.Paths.Items,created:CreateTime}' \
  --output json

# Check the origin's actual Cache-Control header.
curl -sI https://origin.example.com/path | grep -i 'cache-control'

# Check what CloudFront received (Age header shows how long the object
# has been in the cache):
curl -sI https://d123.cloudfront.net/path | grep -iE 'x-cache|age|cache-control'
```

| Sub-symptom | Root cause | Fix |
|---|---|---|
| Origin updated, no invalidation sent, TTL not expired | Expected behaviour — TTL prevents refresh | Send an invalidation for the updated paths, OR wait for TTL expiry |
| Invalidation sent but content still stale | Invalidation for wrong paths, or still in progress | Verify `get-invalidation` status; verify paths match (`/images/*` vs `/*`) |
| Origin `max-age=86400` but operator expects 5-min updates | TTL too long for the use case | Lower origin `max-age` to 300, OR set cache policy `MaxTTL: 300` to override |
| Cache policy overrides origin `max-age` with longer TTL | `OriginCacheControlHeaders` set to override, `DefaultTTL` too high | Change to respect origin headers, OR lower `DefaultTTL` |
| Stale after a deployment; old content in cache | No invalidation as part of the deploy pipeline | Add an invalidation step to the CI/CD pipeline |

**Common fix patterns:**

- Send an invalidation for the updated paths:

```bash
aws cloudfront create-invalidation --distribution-id <id> \
  --paths "/path/to/updated/*" "/specific/file.html"
```

- For path-based invalidation vs `/*`: prefer specific paths to avoid
  invalidating the entire cache (which spikes origin load). Use `/*`
  only for full-site updates.
- Add an invalidation step to the deploy pipeline so that every deploy
  automatically clears the cache for changed paths.
- For frequently-updated content, set a shorter TTL (e.g.,
  `max-age=300` for 5 minutes) rather than relying on invalidation.

### Step 4: CACHE_KEY_VARIATION diagnostic

Same URL but different content per user; hit ratio near zero; the cache
has many entries for the same path. The cause is cache key bloat: too
many headers, cookies, or query strings in the cache policy, creating a
unique cache entry for each variation.

**The cache key formula (memorise this):**

```
cache key = URL path
          + query strings (if QueryStringBehavior = allSpecified or allExcept)
          + headers (if HeaderBehavior = whitelist or allExcept)
          + cookies (if CookieBehavior = whitelist or allExcept)
```

Any value included in the cache policy creates a distinct cache entry
for each unique combination of values. Including `User-Agent` (thousands
of distinct values) fragments the cache into near-zero hit ratio.

**Diagnostic walk:**

1. **Read the cache policy's `ParametersInCacheKeyAndForwardedToOrigin`.**
   This is the cache key definition.

```bash
aws cloudfront get-cache-policy --id <cache-policy-id> \
  --query 'CachePolicy.CachePolicyConfig.ParametersInCacheKeyAndForwardedToOrigin' \
  --output json
```

| Cache policy setting | Effect on cache key | Recommendation |
|---|---|---|
| `HeadersConfig.HeaderBehavior: none` | No headers in cache key | Default; use unless response varies by header |
| `HeadersConfig.HeaderBehavior: whitelist` + specific headers | Listed headers in cache key | Only include headers that affect the response |
| `QueryStringsConfig.QueryStringBehavior: all` | ALL query strings in cache key | Use only if every query param affects the response |
| `QueryStringsConfig.QueryStringBehavior: none` | No query strings in cache key | Use for static content |
| `CookiesConfig.CookieBehavior: all` | ALL cookies in cache key | Almost never correct — fragments cache |
| `CookiesConfig.CookieBehavior: whitelist` + specific cookies | Listed cookies in cache key | Only include cookies that affect the response (e.g., `session`) |

2. **Check for known cache-key-fragmenting headers.** The most common
   offenders:
   - `User-Agent` — thousands of distinct values; almost never affects
     the response. Do NOT include in the cache key.
   - `Authorization` — unique per user; fragments cache. Use only if the
     content is truly per-user.
   - `Accept` — varies by browser; include `Accept-Encoding` for
     compression but not `Accept` for content negotiation unless the
     origin truly negotiates.
   - `X-Forwarded-For` — unique per client; never include in cache key.

3. **Check if `Accept-Encoding` is in the cache key for compressed
   content.** CloudFront requires `Accept-Encoding` in the cache key to
   serve compressed responses (gzip, Brotli). If `Accept-Encoding` is NOT
   in the cache key, CloudFront may serve uncompressed content or fail to
   compress. The managed policy `AllViewerExceptReservedHeader` includes
   `Accept-Encoding` by default.

4. **Check the number of unique cache entries.** CloudFront access logs
   show `x-edge-result-type`. If every request is a `Miss` for the same
   URL, the cache key is different per request. Compare `cs-cookie` and
   `cs-accept-encoding` fields in the logs to identify the varying
   component.

**Managed policy reference:**

| Managed policy | ID | Cache key includes | Use case |
|---|---|---|---|
| `AllViewerExceptReservedHeader` | `4135ea2d-6df8-44a3-9df3-4b5a84be39ad` (placeholder — see AWS docs for current) | All viewer headers except reserved; all query strings; all cookies | Most common; use when response varies by viewer headers |
| `AllViewer` | — | All viewer headers; all query strings; all cookies | Use when every viewer attribute affects the response (rare) |
| `CachingDisabled` | `4135ea2d-6df8-44a3-9df3-4b5a84be39ad` | Nothing (TTL = 0) | Use for dynamic, non-cacheable content |
| `CachingOptimized` | `658327ea-f89d-4fab-a63d-7e88639e58f6` | No headers, no query strings, no cookies; high TTL | Use for static assets (images, CSS, JS) |
| `Elemental-MediaPackage` | — | Tailored for MediaPackage origins | Use for MediaPackage video |

**Common fix patterns:**

- Remove `User-Agent` from the cache policy headers whitelist. Use
  `none` or only include headers that genuinely affect the response.
- Switch from `CookiesConfig.CookieBehavior: all` to `whitelist` with
  only the cookies that affect the response (e.g., `theme`, `lang`).
- For static assets (images, CSS, JS), use the managed `CachingOptimized`
  policy (no headers, no cookies, no query strings in cache key).
- For dynamic APIs, use `CachingDisabled` and do not attempt to cache.
- For content that varies by a specific header (e.g., `Accept-Language`
  for i18n), use `AllViewerExceptReservedHeader` and accept the cache
  fragmentation as a tradeoff.

### Step 5: ERROR_FROM_CACHE diagnostic

CloudFront returns 403 or 404; the origin returns 200. The cause is one
of: WAF blocking the request, Lambda@Edge modifying the response, the
origin returning an error that CloudFront caches, or a cache behavior
pointing to the wrong origin.

**Diagnostic walk:**

1. **Check for WAF on the distribution.** A WAF web ACL on the
   distribution can block requests before they reach the cache or origin.
   A blocked request returns 403 with `x-amzn-waf-action: BLOCK`.

```bash
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.WebACLId' --output text

# If a WAF is attached, check the web ACL for BLOCK rules.
aws wafv2 get-web-acl --scope CLOUDFRONT --id <web-acl-id> \
  --query 'WebACL.Rules[*].{name:Name,action:Action,priority:Priority}' \
  --output json
```

2. **Check for Lambda@Edge functions on the behavior.** A Lambda@Edge
   function on `viewer-response` or `origin-response` can modify the
   response status code, headers, or body. A bug in the function can
   return 403/404 where the origin returned 200.

```bash
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.DefaultCacheBehavior.LambdaFunctionAssociations.Items[*].{type:EventType,arn:LambdaFunctionARN,includeBody:IncludeBody}' \
  --output json
```

3. **Check the origin directly.** Run `curl -I` against the origin,
   bypassing CloudFront. If the origin returns 200 but CloudFront returns
   403/404, the issue is in the CloudFront layer (WAF, Lambda@Edge, or
   cache behavior).

```bash
# Direct to origin:
curl -sI https://origin.example.com/path

# Via CloudFront:
curl -sI https://d123.cloudfront.net/path
```

4. **Check if CloudFront is caching a 404 from the origin.** CloudFront
   caches 404 responses if the cache policy allows it (the
   `errorResponseCachingBehavior` or the response's `Cache-Control`). A
   transient 404 from the origin can get cached and persist even after
   the origin recovers.

5. **Check the cache behavior target origin.** If the cache behavior
   points to the wrong origin (e.g., an S3 bucket that was deleted), the
   origin returns 404 and CloudFront serves it.

| Sub-symptom | Root cause | Probe |
|---|---|---|
| 403 with `x-amzn-waf-action: BLOCK` | WAF web ACL blocking the request | Read the WAF rules; check for BLOCK rules on the path/IP |
| 403 without WAF action header | Lambda@Edge returning 403, or origin returning 403 | Check Lambda@Edge logs; curl the origin directly |
| 404 that persists after origin recovers | CloudFront cached a transient 404 | Invalidate the path; check `errorResponseCachingBehavior` |
| 404 on a specific path | Cache behavior pointing to wrong origin | Compare `TargetOriginId` to the actual origin |
| Intermittent 502/503/504 | Origin timeout or error; CloudFront returns the error | Check origin health; `origin-response` Lambda@Edge for errors |

**Common fix patterns:**

- WAF blocking: review the WAF rules. If a rule is blocking legitimate
  traffic, adjust the rule or add an IP to the allowlist.
- Lambda@Edge mutation: review the function code. If the function is
  modifying the response status code or body incorrectly, fix the
  function or remove it from the behavior.
- Cached 404: send an invalidation for the path. Set
  `errorResponseCachingBehavior` to a low TTL or 0 for 404s if the
  origin is flaky.
- Wrong origin: update the cache behavior's `TargetOriginId` to the
  correct origin.

### Step 6: LOW_HIT_RATIO diagnostic

Hit ratio is dropping; origin load is rising; the cache is serving a mix
of `Hit` and `Miss` in logs. The cause is one of: cache key bloat (too
many variations), TTL too short (objects expire before re-request), the
origin sending `no-cache` on some responses, or a traffic pattern change
(long-tail content that is requested once).

**Diagnostic walk:**

1. **Check the CloudFront metrics.** The `CacheHitRate` metric shows the
   ratio directly. `OriginLatency` rising alongside a hit-ratio drop
   confirms the origin is receiving more requests.

```bash
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=<id> \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average --output json
```

2. **Analyze the access logs for the Miss pattern.** Group `Miss` entries
   by path, query string, and headers to identify what is varying.

3. **Check if the long tail is the cause.** If the content catalog grew
   (more unique URLs), each URL is a cache miss on first request. This is
   expected and not a configuration issue. The fix is pre-warming
   (requesting the content after publish) or accepting the lower ratio.

4. **Check if the origin is sending inconsistent `Cache-Control` headers.**
   If some responses from the origin include `no-cache` and others
   include `max-age=3600`, the cache ratio will be inconsistent. Inspect
   the origin responses for a sample of paths.

| Sub-symptom | Root cause | Fix |
|---|---|---|
| `CacheHitRate` dropping after a traffic increase | Long-tail content — more unique URLs | Pre-warm new content; accept lower ratio for long tail |
| `CacheHitRate` low for a specific path pattern | Cache key bloat on that behavior | Narrow the cache policy for that behavior |
| `CacheHitRate` low with frequent `RefreshHit` | TTL expired; objects revalidated frequently | Raise the TTL if content changes infrequently |
| `CacheHitRate` low on dynamic API paths | Dynamic content is not cacheable | Use `CachingDisabled` for truly dynamic paths; separate cache behavior |
| `CacheHitRate` low after a deploy | Invalidation cleared the cache | Expected post-invalidation; ratio recovers as traffic re-populates cache |

**Common fix patterns:**

- Separate static and dynamic content into different cache behaviors
  with different cache policies. Static assets get `CachingOptimized`;
  dynamic API gets `CachingDisabled` or a narrow policy.
- Raise the TTL for content that changes infrequently. For S3 objects
  that are immutable (versioned by hash in the filename), set
  `max-age=31536000` (1 year).
- Use Origin Shield to improve the cache hit ratio at the origin level
  (a second-tier cache between CloudFront edge and the origin).
- Pre-warm the cache for high-traffic content after deploys by
  requesting the URLs from the CloudFront domain.

### Step 7: Map to root-cause catalog

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Origin sends `Cache-Control: no-store` or `no-cache` | CACHE_MISS_ALWAYS (ORIGIN_NO_CACHE) | Update origin to send `public, max-age=<TTL>` |
| 2 | Cache policy TTL is 0 or `CachingDisabled` attached | CACHE_MISS_ALWAYS (CACHE_POLICY_TOO_NARROW) | Switch to `CachingOptimized` or set `DefaultTTL > 0` |
| 3 | No invalidation sent after origin update | STALE_CONTENT (STALE_NO_INVALIDATION) | Send invalidation; add to CI/CD pipeline |
| 4 | TTL too long for frequently-updated content | STALE_CONTENT (TTL_TOO_LONG) | Lower `max-age` or cache policy `MaxTTL` |
| 5 | `User-Agent` or `Authorization` in cache key | CACHE_KEY_VARIATION (CACHE_KEY_BLOAT) | Remove from cache policy headers |
| 6 | All cookies in cache key | CACHE_KEY_VARIATION (CACHE_KEY_BLOAT) | Switch to `whitelist` with only necessary cookies |
| 7 | WAF blocking requests | ERROR_FROM_CACHE (WAF_BLOCK) | Adjust WAF rules; add allowlist |
| 8 | Lambda@Edge modifying response | ERROR_FROM_CACHE (LAMBDA_EDGE_MUTATION) | Fix function; remove from behavior |
| 9 | Cached transient 404 from origin | ERROR_FROM_CACHE (ORIGIN_ERROR) | Invalidate path; lower 404 cache TTL |
| 10 | `Accept-Encoding` not in cache key for compressed content | CACHE_KEY_VARIATION (COMPRESSION_CACHE_KEY) | Add `Accept-Encoding` to cache policy |

### Step 8: Verify the fix

- **For origin header changes:** update the origin and verify with
  `curl -I` that the new `Cache-Control` header is returned. Then request
  via CloudFront twice — the second request should show `x-cache: Hit
  from cloudfront`.
- **For cache policy changes:** update the distribution config. Wait for
  the deployment to complete (status `Deployed`). Then test with `curl
  -I` twice.
- **For invalidation:** wait for the invalidation to complete
  (`get-invalidation` status `Completed`). Then request the path — the
  first request should be a `Miss`, the second a `Hit`.
- **For WAF changes:** verify that the blocked requests now succeed.
  Check WAF sample requests for any remaining blocks.
- **For Lambda@Edge changes:** deploy the updated function version.
  CloudFront propagates the function to edge locations (takes a few
  minutes). Then test.

### Step 9: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** The walk identified a specific cache issue and a
  specific configuration element (origin header, cache policy field, WAF
  rule, Lambda@Edge function). Output REMEDIATION with the exact change.
- **NEED_MORE_INFO.** The walk reached a step where the operator cannot
  supply evidence (e.g., access logs are not enabled, or the cache
  policy ID is unknown). Output the list of missing inputs.
- **ESCALATE.** The walk identifies a cause outside the operator's scope:
  an AWS-side CloudFront event, a Lambda@Edge function owned by another
  team, or a WAF rule managed centrally. Output the escalation target.

## Output format

```text
DISTRIBUTION: <distribution ID or domain>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <cache issue name> — <specific root cause>
CACHE_ISSUE: <ORIGIN_NO_CACHE | ORIGIN_NO_STORE | CACHE_POLICY_TOO_NARROW |
              CACHE_KEY_BLOAT | TTL_TOO_SHORT | STALE_NO_INVALIDATION |
              ORIGIN_HEADER_OVERRIDE | LAMBDA_EDGE_MUTATION | WAF_BLOCK |
              COMPRESSION_CACHE_KEY | ORIGIN_ERROR | UNKNOWN>
EVIDENCE:
  - <origin response header>: <value>
  - <cache policy field>: <value>
  - <x-edge-result-type from access logs>: <value>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific config change with CLI command>
  2. <verification command>
  3. <post-apply monitoring>
```

### Worked example — origin sending no-store

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

### Worked example — User-Agent in cache key

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

## Diagnostic command reference

```bash
# 1. Distribution config — cache behaviors, policies, origins.
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.{origins:Origins.Items,behaviors:CacheBehaviors.Items,default:DefaultCacheBehavior,webACL:WebACLId}' \
  --output json

# 2. Cache policy details (the cache key definition).
aws cloudfront get-cache-policy --id <cache-policy-id> \
  --query 'CachePolicy.CachePolicyConfig.{ttl:{min:MinTTL,def:DefaultTTL,max:MaxTTL},params:ParametersInCacheKeyAndForwardedToOrigin}' \
  --output json

# 3. List managed cache policies (for reference).
aws cloudfront list-cache-policies --type managed \
  --query 'CachePolicyList.Items[*].{id:Id,name:Name,desc:Comment}' \
  --output json

# 4. Recent invalidations.
aws cloudfront list-invalidations --distribution-id <id> \
  --query 'InvalidationList.Items[*].{id:Id,status:Status,paths:InvalidationBatch.Paths.Items}' \
  --output json

# 5. CloudFront metrics — CacheHitRate.
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=<id> \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average --output json

# 6. Test caching directly — request twice, check x-cache.
curl -sI https://<distribution-domain>/path | grep -iE 'x-cache|age|cache-control'
curl -sI https://<distribution-domain>/path | grep -iE 'x-cache|age|cache-control'

# 7. Test origin directly (bypass CloudFront).
curl -sI https://<origin-domain>/path | grep -iE 'cache-control|expires|pragma|set-cookie'

# 8. WAF on the distribution.
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.WebACLId' --output text

# 9. Lambda@Edge functions on the behavior.
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.DefaultCacheBehavior.LambdaFunctionAssociations.Items[*].{type:EventType,arn:LambdaFunctionARN}' \
  --output json

# 10. CloudFront access logs (if logging enabled, logs in S3).
#     Use aws logs get-log-events if exported to CloudWatch Logs, or
#     aws s3 ls / cp to retrieve from the S3 logging bucket.
```

## Anti-Patterns — NEVER

- NEVER assume the cache policy TTL controls caching when the origin
  sends `Cache-Control: no-store`. The origin header overrides the
  policy unless the policy explicitly overrides origin headers. Always
  check the origin's `Cache-Control` first.

- NEVER include `User-Agent` in the cache key. Thousands of distinct
  User-Agent values fragment the cache. If the response truly varies by
  client type, normalize the header (e.g., `mobile` vs `desktop`) before
  including it.

- NEVER use `CookiesConfig.CookieBehavior: all` unless the response truly
  varies by every cookie. `all` includes analytics cookies, session
  cookies, and A/B test cookies — each fragments the cache. Use
  `whitelist` with only the cookies that affect the response.

- NEVER confuse `no-cache` with `no-store`. `no-cache` allows caching
  but requires revalidation on every request (`RefreshHit` /
  `RefreshMiss`). `no-store` prohibits caching entirely. The fix for
  `no-cache` is to allow revalidation; the fix for `no-store` is to
  remove the header.

- NEVER invalidate `/*` when a path-specific invalidation suffices.
  `/*` clears the entire cache, spiking origin load as every object is
  re-fetched. Use specific paths (`/images/*`, `/api/v2/*`) to limit
  the impact.

- NEVER assume CloudFront is caching 404s from the origin by default.
  CloudFront caches 404 only if `errorResponseCachingBehavior` allows it
  or the 404 response includes a `Cache-Control` header. Check both
  before declaring a cached-404 as the cause.

- NEVER set `MaxTTL` lower than `MinTTL` on a cache policy. This produces
  unpredictable caching behaviour. Always ensure `MinTTL <= DefaultTTL
  <= MaxTTL`.

- NEVER deploy a Lambda@Edge function on `viewer-response` without
  testing. The function runs on every response at the edge; a bug
  affects all viewers globally. Test in a staging environment first.

- NEVER assume `x-cache: Hit from cloudfront` means the content is
  fresh. A `Hit` can be a stale object served within its TTL. If the
  content is stale, the issue is TTL or invalidation, not the cache
  status.

- NEVER use the same cache behavior for static and dynamic content.
  Static assets need `CachingOptimized` (high TTL, no headers/cookies);
  dynamic APIs need `CachingDisabled` or a narrow policy. Mixing them
  produces poor hit ratio or stale dynamic content.

- NEVER forget `Accept-Encoding` in the cache key for compressed
  content. Without it, CloudFront may serve a compressed response to a
  client that cannot decompress, or fail to compress at all. The managed
  policy `AllViewerExceptReservedHeader` includes it by default.

## Remediation guidance

### For ORIGIN_NO_CACHE / ORIGIN_NO_STORE

1. Verify the origin's `Cache-Control` header with `curl -I` directly
   to the origin.
2. For S3 origins: update object metadata with
   `aws s3api copy-object --cache-control "public, max-age=3600"
   --metadata-directive REPLACE`.
3. For ALB/EC2 origins: update the application to send
   `Cache-Control: public, max-age=3600` on cacheable responses.
4. If the origin cannot be changed, configure the cache policy to
   override origin cache headers with `MinTTL`, `DefaultTTL`, `MaxTTL`.

### For CACHE_POLICY_TOO_NARROW

1. Read the current cache policy TTL settings.
2. If `CachingDisabled` is attached, switch to `CachingOptimized` for
   static content, or a custom policy with `DefaultTTL > 0`.
3. If all TTLs are 0, raise `DefaultTTL` to the desired cache duration.

### For STALE_NO_INVALIDATION

1. Send an invalidation for the updated paths:
   `aws cloudfront create-invalidation --distribution-id <id>
   --paths "/updated/*"`.
2. Add an invalidation step to the CI/CD pipeline for future deploys.
3. For frequently-updated content, lower the TTL rather than relying on
   invalidation.

### For TTL_TOO_LONG

1. Lower the origin's `Cache-Control: max-age` to the desired freshness
   window.
2. Or set the cache policy `MaxTTL` to cap the TTL regardless of origin
   headers.
3. Verify that `OriginCacheControlHeaders` is set to respect or override
   as intended.

### For CACHE_KEY_BLOAT

1. Read the cache policy `ParametersInCacheKeyAndForwardedToOrigin`.
2. Remove `User-Agent`, `Authorization`, `X-Forwarded-For` from the
   headers whitelist.
3. Switch `CookiesConfig.CookieBehavior` from `all` to `whitelist` with
   only necessary cookies.
4. Switch `QueryStringsConfig.QueryStringBehavior` from `all` to
   `none` (static) or `allSpecified` (dynamic with specific params).

### For WAF_BLOCK

1. Read the WAF web ACL rules on the distribution.
2. Identify the BLOCK rule that matches the legitimate traffic.
3. Adjust the rule (narrow the match condition) or add an allowlist
   exception.
4. Verify with `curl -I` that the request now succeeds.

### For LAMBDA_EDGE_MUTATION

1. Read the Lambda@Edge function code on the behavior.
2. Identify where the function modifies the response status, headers, or
   body.
3. Fix the function; deploy a new version.
4. Update the distribution to use the new function version ARN.
5. Wait for CloudFront to propagate (a few minutes).

### For ORIGIN_ERROR (cached transient error)

1. Invalidate the cached error response:
   `aws cloudfront create-invalidation --distribution-id <id>
   --paths "/erroring-path/*"`.
2. Lower the `errorResponseCachingBehavior` TTL for the relevant status
   code (e.g., set 404 TTL to 0 if the origin is flaky).
3. Verify the origin now returns 200 for the path.

## Recent AWS features (2024-2026)

- **CloudFront KeyValueStore for Lambda@Edge (2024 GA):** a lightweight
  key-value store accessible from Lambda@Edge functions without calling
  the origin. Reduces the need for origin calls in edge logic, improving
  cache hit ratio.
- **CloudFront Origin Shield enhancements (2024-2025):** Improved
  Origin Shield hit ratio metrics and finer-grained control. Use Origin
  Shield as a second-tier cache to improve the origin-side hit ratio.
- **CloudFront additional metrics (2024-2025):** More granular
  per-cache-behavior metrics including `OriginRequestCount`,
  `4xxErrorRate`, `5xxErrorRate` per behavior. Use these to isolate
  cache issues to a specific behavior rather than the whole distribution.
- **Cache policy override improvements (2024):** Better support for
  overriding origin `Cache-Control` with the cache policy's
  `OriginCacheControlHeaders` setting. Troubleshoot stale content by
  checking whether the policy respects or overrides origin headers.
- **CloudFront Logs to CloudWatch Logs (2024-2025):** Direct export of
  CloudFront access logs to CloudWatch Logs (in addition to S3). Enables
  real-time log analysis via CloudWatch Logs Insights for cache-miss
  pattern detection.
- **Response Headers Policy (2024-2025 enhancements):** More
  granular control over response headers including security headers
  (HSTS, CSP) without Lambda@Edge. Troubleshoot response header issues by
  checking the response headers policy attached to the behavior.

## References

See `references/cache-key-model.md` for the full cache key model with
worked examples, and `references/diagnostic-commands.md` for the
canonical command script per cache issue category.

## Domain

AWS CloudOps / CloudFront CDN Caching, Cache Policy, and Edge Performance.

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

**Diagnostic:**
- Inspect `cs-accept-encoding` and other `cs-*` fields in CloudFront
  access logs for case variation across requests to the same URL.
- If the cache policy whitelists a header, ALL distinct case variants
  of that header name create distinct cache entries.

**Fix:**
- Prefer the managed `AllViewerExceptReservedHeader` policy — it
  normalizes header handling and includes only the headers CloudFront
  needs for routing and compression.
- For custom policies, normalize header names at the origin or via a
  Lambda@Edge `origin-request` function before the cache lookup.
- Avoid including case-varying headers (`Accept`, `Accept-Language`) in
  the cache key unless the origin truly negotiates on them.

## Edge case: Lambda@Edge response modification invalidates the cache entry

A Lambda@Edge function on the `viewer-response` or `origin-response`
event runs AFTER CloudFront has computed the cache key. The function
can modify the response headers, body, or status code — but those
modifications apply to the cached response. A function that mutates
the response per-request produces a response that does NOT match the
cache key's expected content for subsequent requests.

**Failure patterns:**
- A `viewer-response` function adding `Set-Cookie` with a unique trace
  ID per request taints the cached object — every viewer sees a
  different Set-Cookie value for the "same" cache entry.
- An `origin-response` function stripping `Age` or rewriting
  `Cache-Control: no-store` rewrites the cached response, producing
  inconsistent caching behavior for the same URL.
- A function that mutates the response body (e.g., HTML rewriting)
  bakes that mutation into the cached entry — subsequent hits serve
  the mutated body even to viewers that did not trigger the mutation.

**Diagnostic:**
- If hit ratio is near zero but the cache policy and origin headers
  look correct, inspect every Lambda@Edge function on the behavior.
- Detach the function temporarily and observe whether hit ratio
  recovers — the fastest causal test.
- CloudFront access logs show `x-edge-result-type: Miss` even though
  the same URL is being requested repeatedly.

**Fix:**
- Move per-request response-header mutations (trace IDs, nonces) into
  a `viewer-response` function that ALSO sets `Cache-Control: private`
  so the variation is not cached at the edge.
- Never generate per-request unique values in an `origin-response`
  function — those taint the cached object for all subsequent viewers.
- Separate cacheable content from per-viewer mutations using two cache
  behaviors: one cached (origin response untouched), one uncached
  (`CachingDisabled`, per-viewer mutation allowed).

## AWS documentation

- **Amazon CloudFront Developer Guide** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html
- **CloudFront caching** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ConfiguringCaching.html
- **Cache policies** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-the-cache-key.html
- **CloudFront access logs** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/AccessLogs.html
- **Lambda@Edge** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html
- **CloudFront metrics** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudwatch-monitoring.html
- **CloudFront CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudfront/
