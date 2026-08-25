---
name: cloudfront-cache-troubleshooter
description: Diagnoses CloudFront caching issues via a symptom-to-cause decision tree covering cache misses on every request, stale content served, unexpected cache key variation, 403/404 errors from cache, and low cache hit ratio. Walks Cache-Control headers from origin, cache policy configuration (managed vs custom), TTL settings, query string/header/cookie inclusion in cache key, x-edge-result-type and x-cache headers in access logs, Lambda@Edge response modifications, and WAF blocks. Emits a deterministic verdict (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE) with the specific cache issue and evidence from CloudFront access logs, cache policy inspection, and curl response headers. Use when content is not cached, stale content is served, hit ratio is low, or CloudFront returns 403/404 unexpectedly.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works from pasted response headers, access log excerpts, and cache policy JSON. Live-account diagnosis uses aws cloudfront get-distribution-config, get-cache-policy, aws cloudfront get-monitoring-sample, curl -I against the distribution and origin, and CloudFront access logs via aws logs get-log-events (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: troubleshoot
  skill_class: capability
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  lifecycle_status: active
  when_to_use: Diagnosing CloudFront cache misses on every request, stale content being served, unexpected cache key variation (different content per user), 403/404 errors from the cache edge, low cache hit ratio with elevated origin load, or Lambda@Edge / WAF interference with caching; validating whether the root cause is origin headers, cache policy misconfiguration, TTL settings, invalidation gaps, or cache key bloat.
  when_not_to_use: CloudFront distribution configuration posture audits (use cloudfront-distribution-auditor), origin failover / multi-origin setup (use cloudfront-distribution-deployer), TLS certificate issues on the distribution (use acm-certificate-expiry-auditor), or WAF rule authoring (use wafv2-web-acl-auditor). This skill diagnoses caching root cause; it does not audit distribution security posture.
  activation_triggers: CloudFront cache miss every request, CloudFront not caching, CloudFront stale content, CloudFront content not updating, CloudFront cache hit ratio low, CloudFront origin load high, CloudFront 403 from cache, CloudFront 404 from edge, CloudFront different content per user, CloudFront cache key variation, CloudFront cache policy misconfigured, x-cache Miss from cloudfront, x-edge-result-type Miss, troubleshoot CloudFront caching
  invocation_schema: 'Input: either (a) a symptom description (cache miss pattern, stale content report, hit-ratio drop), optionally paired with cache policy JSON and response headers, OR (b) a distribution ID plus caller context (origin URL, observed x-cache header, access log excerpt) for live-account diagnosis. Output: a deterministic DISTRIBUTION / VERDICT / ROOT_CAUSE / CACHE_ISSUE / EVIDENCE / REMEDIATION block where VERDICT ∈ {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and CACHE_ISSUE ∈ {ORIGIN_NO_CACHE, ORIGIN_NO_STORE, CACHE_POLICY_TOO_NARROW, CACHE_KEY_BLOAT, TTL_TOO_SHORT, STALE_NO_INVALIDATION, ORIGIN_HEADER_OVERRIDE, LAMBDA_EDGE_MUTATION, WAF_BLOCK, COMPRESSION_CACHE_KEY, ORIGIN_ERROR, UNKNOWN}.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: CloudFront, caching, cache miss, cache hit ratio, stale content, cache key, cache policy, Cache-Control, max-age, no-cache, no-store, TTL, x-edge-result-type, x-cache, Lambda@Edge, origin shield, managed policy, AllViewerExceptReservedHeader, invalidation, troubleshooting
  tags: cloudfront, networking, troubleshoot, caching, cdn, cache-policy, ttl, lambda-at-edge
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

Three facts make CloudFront cache diagnosis different:

- **CloudFront caches by cache key, not by URL alone.** The cache key =
  URL path + query strings + headers + cookies (per the cache policy).
  Including `User-Agent` fragments the cache so badly that hit ratio
  drops to near zero.
- **Origin `Cache-Control` headers dominate unless the cache policy
  overrides them.** If the origin sends `Cache-Control: no-store`,
  CloudFront will not cache regardless of the policy TTL.
- **`x-edge-result-type` in access logs is the ground truth.** Values:
  `Hit`, `Miss`, `RefreshHit`, `RefreshMiss`, `Error`, `LimitExceeded`,
  `CapacityExceeded`, `Denied`. `Miss` every time means cache key or
  origin headers prevent caching.

## Expert heuristic

Five senior-CDN-engineer heuristics (edge-only hit ratio, Lambda@Edge header rewrites, Origin Shield break-even, compression size limits, Functions vs Lambda@Edge cache timing) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when the symptom contradicts the cache policy analysis.

## Quick reference — symptom to cache issue

| Observed signal | Cache issue | First probe |
|---|---|---|
| `x-edge-result-type: Miss` on every request | ORIGIN_NO_CACHE / ORIGIN_NO_STORE / CACHE_POLICY_TOO_NARROW | `curl -I` to origin for `Cache-Control`; cache policy TTL |
| Content hours/days old; origin updated | STALE_NO_INVALIDATION / TTL_TOO_LONG | Origin `max-age` vs behavior TTL; invalidation history |
| Same URL, different content per user | CACHE_KEY_BLOAT | Cache policy headers/cookies/query strings |
| 403 / 404 from CloudFront; origin returns 200 | WAF_BLOCK / LAMBDA_EDGE_MUTATION | WAF web ACL; Lambda@Edge logs |
| Hit ratio dropping; origin load rising | CACHE_KEY_BLOAT / TTL_TOO_SHORT | Cache policy `DefaultTTL`; cache key values |
| `RefreshHit` frequent; origin gets `If-Modified-Since` | TTL_EXPIRED / STALE-REVALIDATE | Origin `max-age` vs behavior `MinTTL` |

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the cache signal

| Signal | Source | Why required |
|---|---|---|
| **Distribution ID or domain** | User-provided or `list-distributions` | All get-distribution-config calls need this |
| **Symptom (miss vs stale vs variation)** | User report + `curl -I` | Drives the symptom category |
| **x-edge-result-type / x-cache** | Access logs (S3) or `curl -I` | Ground truth for edge behavior |

If distribution/domain unknown:

list-distributions / get-distribution-config discovery commands moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Run them when the distribution ID or domain is unknown.

### Step 1: Identify the symptom category

| Category | Signature | Diagnostic step |
|---|---|---|
| **A. CACHE_MISS_ALWAYS** | `Miss` on every request; `x-cache: Miss from cloudfront` | Step 2 |
| **B. STALE_CONTENT** | Content old; origin updated; no invalidation sent | Step 3 |
| **C. CACHE_KEY_VARIATION** | Same URL, different content per user; hit ratio near zero | Step 4 |
| **D. ERROR_FROM_CACHE** | 403/404 from CloudFront; origin returns 200; `x-edge-result-type: Error` | Step 5 |
| **E. LOW_HIT_RATIO** | Hit ratio dropping; origin load rising; mix of Hit and Miss | Step 6 |

Priority if multiple match: CACHE_MISS_ALWAYS > ERROR_FROM_CACHE >
CACHE_KEY_VARIATION > STALE_CONTENT > LOW_HIT_RATIO.

### Step 2: CACHE_MISS_ALWAYS diagnostic

Every request is a `Miss`. Cause: origin sends `no-cache`/`no-store`, cache
policy TTL is 0, `CachingDisabled` attached, or response not cacheable.

**Diagnostic walk:**

1. **Check origin `Cache-Control`** (#1 cause). `curl -I` directly to origin:

```bash
# Direct to origin (bypass CloudFront):
curl -sI https://origin.example.com/path/to/content | grep -iE 'cache-control|expires|pragma|set-cookie'

# Via CloudFront:
curl -sI https://d123.cloudfront.net/path/to/content | grep -iE 'x-cache|age|cache-control'
```

| Origin header | Effect | Fix |
|---|---|---|
| `Cache-Control: no-store` | Never caches | Change to `public, max-age=3600` |
| `Cache-Control: no-cache` | Revalidates every request (RefreshMiss) | Change to `public, max-age=3600` |
| `Cache-Control: max-age=0` | Same as no-cache | Raise to desired TTL |
| `Cache-Control: private` | Not cached (browser-only) | Change to `public` |
| `Pragma: no-cache` | Legacy HTTP/1.0 no-cache | Remove |
| `Set-Cookie` in response | May skip caching if cookie not in policy | Add cookie to policy or remove Set-Cookie |

2. **Check cache policy TTL:** `MinTTL: 0, DefaultTTL: 0, MaxTTL: 0` disables
   caching. Managed `CachingDisabled` (ID `4135ea2d-6df8-44a3-9df3-4b5a84be39ad`)
   explicitly sets all TTLs to 0.

```bash
aws cloudfront get-cache-policy --id <cache-policy-id> \
  --query 'CachePolicy.CachePolicyConfig.{minTTL:MinTTL,defaultTTL:DefaultTTL,maxTTL:MaxTTL,headers:ParametersInCacheKeyAndForwardedToOrigin.HeadersConfig.HeaderBehavior}' \
  --output json
```

3. **Check if origin returns cacheable status codes.** CloudFront caches
   200, 206, 301, 302, 304, 404 (optionally).

**Common fixes:**
- Origin sends `no-store`: update origin to `Cache-Control: public, max-age=3600`.
  For S3: `aws s3api put-object` with `--cache-control`.
- Cache policy TTL is 0: set `DefaultTTL: 3600` or use managed
  `CachingOptimized` (`658327ea-f89d-4fab-a63d-7e88639e58f6`).
- `Set-Cookie` preventing caching: add cookie to policy or remove from response.

### Step 3: STALE_CONTENT diagnostic

Content served from cache but old — origin updated but CloudFront serves
cached version. Cause: TTL not expired (expected without invalidation), no
invalidation sent, or cache behavior overrides origin with longer TTL.

**Diagnostic walk:**

1. **Determine if invalidation is needed.** CloudFront serves cached content
   until TTL expires OR invalidation clears it. No invalidation after origin
   update = stale until TTL expires. This is expected, not a bug.
2. **Compare origin `max-age` vs cache behavior TTL.** If origin sends
   `max-age=86400` but operator expects minutes, TTL is too long.
3. **Check `OriginCacheControlHeaders` handling.** If set to respect,
   CloudFront uses origin's `max-age`. If override, uses policy `DefaultTTL`.
4. **Check invalidation history.** If invalidation sent but stale persists,
   it may be for wrong paths or still in progress.

```bash
# List recent invalidations.
aws cloudfront list-invalidations --distribution-id <id> \
  --query 'InvalidationList.Items[*].{id:Id,status:Status,paths:InvalidationBatch.Paths.Items,created:CreateTime}' \
  --output json

# Check the Age header (how long object has been cached):
curl -sI https://d123.cloudfront.net/path | grep -iE 'x-cache|age|cache-control'
```

| Sub-symptom | Root cause | Fix |
|---|---|---|
| No invalidation sent, TTL not expired | Expected behaviour | Send invalidation OR wait for TTL |
| Invalidation sent but still stale | Wrong paths or in progress | Verify `get-invalidation` status; paths match |
| Origin `max-age=86400` but expects 5-min | TTL too long | Lower origin `max-age` or policy `MaxTTL` |
| Stale after deployment | No invalidation in CI/CD | Add invalidation step to deploy pipeline |

**Common fixes:**
- Send invalidation: `aws cloudfront create-invalidation --distribution-id <id> --paths "/updated/*"`.
  Prefer specific paths over `/*` to avoid spiking origin load.
- Add invalidation to CI/CD pipeline.
- For frequently-updated content, set shorter TTL (`max-age=300`).

### Step 4: CACHE_KEY_VARIATION diagnostic

Same URL but different content per user; hit ratio near zero. Cause: cache
key bloat — too many headers, cookies, or query strings creating unique
entries.

**Cache key formula:** `cache key = URL path + query strings (per policy) +
headers (per policy) + cookies (per policy)`. Any value included creates a
distinct entry per unique combination.

**Diagnostic walk:**

1. **Read cache policy `ParametersInCacheKeyAndForwardedToOrigin`:**

```bash
aws cloudfront get-cache-policy --id <cache-policy-id> \
  --query 'CachePolicy.CachePolicyConfig.ParametersInCacheKeyAndForwardedToOrigin' \
  --output json
```

| Cache policy setting | Effect | Recommendation |
|---|---|---|
| `HeadersConfig.HeaderBehavior: none` | No headers in key | Default; use unless response varies |
| `QueryStringsConfig.QueryStringBehavior: all` | ALL query strings in key | Only if every param affects response |
| `CookiesConfig.CookieBehavior: all` | ALL cookies in key | Almost never correct — fragments cache |
| `CookiesConfig.CookieBehavior: whitelist` + specific | Listed cookies only | Only cookies that affect response |

2. **Check for fragmenting headers:** `User-Agent` (thousands of values),
   `Authorization` (unique per user), `X-Forwarded-For` (unique per client).
   Do NOT include these in the cache key.
3. **Check `Accept-Encoding`** — required in cache key for compressed content.
   Managed `AllViewerExceptReservedHeader` includes it by default.
4. **Check access logs:** if every request is `Miss` for same URL, cache key
   varies per request. Compare `cs-cookie` and `cs-accept-encoding` fields.

See `references/worked-examples.md` for the managed policy reference table
and cache key normalization details.

**Common fixes:**
- Remove `User-Agent` from headers whitelist. Use `none` or only headers
  that affect the response.
- Switch `CookiesConfig.CookieBehavior` from `all` to `whitelist` with
  only necessary cookies.
- For static assets, use managed `CachingOptimized`.
- For dynamic APIs, use `CachingDisabled`.

### Step 5: ERROR_FROM_CACHE diagnostic

CloudFront returns 403 or 404; origin returns 200. Cause: WAF blocking,
Lambda@Edge modifying response, cached transient error, or wrong origin.

**Diagnostic walk:**

1. **Check for WAF:** `aws cloudfront get-distribution-config --id <id>
   --query 'DistributionConfig.WebACLId'`. Blocked requests return 403
   with `x-amzn-waf-action: BLOCK`.
2. **Check Lambda@Edge on behavior:** a function on `viewer-response` or
   `origin-response` can modify status code/headers/body.
3. **Check origin directly:** `curl -I` bypassing CloudFront. If origin
   returns 200 but CloudFront returns 403/404, issue is in CloudFront layer.
4. **Check for cached 404:** CloudFront caches 404 if policy allows it
   (`errorResponseCachingBehavior`). A transient 404 can persist after
   origin recovers.
5. **Check cache behavior target origin:** if pointing to deleted/wrong
   origin, origin returns 404.

```bash
# Check WAF rules if attached:
aws wafv2 get-web-acl --scope CLOUDFRONT --id <web-acl-id> \
  --query 'WebACL.Rules[*].{name:Name,action:Action,priority:Priority}' --output json

# Check Lambda@Edge functions:
aws cloudfront get-distribution-config --id <id> \
  --query 'DistributionConfig.DefaultCacheBehavior.LambdaFunctionAssociations.Items[*].{type:EventType,arn:LambdaFunctionARN}' \
  --output json
```

| Sub-symptom | Root cause | Fix |
|---|---|---|
| 403 with `x-amzn-waf-action: BLOCK` | WAF blocking | Adjust WAF rules; add allowlist |
| 403 without WAF header | Lambda@Edge returning 403 | Check function logs; curl origin directly |
| 404 persists after origin recovers | Cached transient 404 | Invalidate; lower 404 cache TTL |
| 404 on specific path | Wrong TargetOriginId | Update behavior's TargetOriginId |

See `references/worked-examples.md` for Lambda@Edge response modification
edge cases.

### Step 6: LOW_HIT_RATIO diagnostic

Hit ratio dropping; origin load rising; mix of Hit and Miss. Cause: cache
key bloat, TTL too short, origin sending `no-cache` on some responses, or
long-tail content (more unique URLs).

**Diagnostic walk:**

1. **Check `CacheHitRate` metric:**

```bash
aws cloudwatch get-metric-statistics --namespace AWS/CloudFront \
  --metric-name CacheHitRate \
  --dimensions Name=DistributionId,Value=<id> \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average --output json
```

2. **Analyze access logs** for the Miss pattern — group by path, query
   string, headers.
3. **Check long tail:** if content catalog grew, each URL is a miss on
   first request (expected). Fix: pre-warming or accept lower ratio.
4. **Check inconsistent origin headers:** some responses with `no-cache`,
   others with `max-age=3600` = inconsistent ratio.

| Sub-symptom | Root cause | Fix |
|---|---|---|
| Drop after traffic increase | Long-tail content | Pre-warm; accept lower ratio |
| Low for specific path | Cache key bloat on that behavior | Narrow the cache policy |
| Low with frequent `RefreshHit` | TTL expired; frequent revalidation | Raise TTL |
| Low after deploy | Invalidation cleared cache | Expected; ratio recovers |

**Common fixes:**
- Separate static and dynamic content into different cache behaviors.
- Raise TTL for content that changes infrequently. S3 immutable objects:
  `max-age=31536000` (1 year).
- Use Origin Shield as second-tier cache.
- Pre-warm cache after deploys.

### Step 7: Map to root-cause catalog

| # | Root cause | Category | Fix pattern |
|---|---|---|---|
| 1 | Origin sends `Cache-Control: no-store` or `no-cache` | CACHE_MISS_ALWAYS (ORIGIN_NO_CACHE) | Update origin to `public, max-age=<TTL>` |
| 2 | Cache policy TTL is 0 or `CachingDisabled` | CACHE_MISS_ALWAYS (CACHE_POLICY_TOO_NARROW) | Switch to `CachingOptimized` or set `DefaultTTL > 0` |
| 3 | No invalidation after origin update | STALE_CONTENT (STALE_NO_INVALIDATION) | Send invalidation; add to CI/CD |
| 4 | TTL too long for frequently-updated content | STALE_CONTENT (TTL_TOO_LONG) | Lower `max-age` or policy `MaxTTL` |
| 5 | `User-Agent` or `Authorization` in cache key | CACHE_KEY_VARIATION (CACHE_KEY_BLOAT) | Remove from cache policy headers |
| 6 | All cookies in cache key | CACHE_KEY_VARIATION (CACHE_KEY_BLOAT) | Switch to `whitelist` with necessary cookies |
| 7 | WAF blocking requests | ERROR_FROM_CACHE (WAF_BLOCK) | Adjust WAF rules; add allowlist |
| 8 | Lambda@Edge modifying response | ERROR_FROM_CACHE (LAMBDA_EDGE_MUTATION) | Fix function; remove from behavior |
| 9 | Cached transient 404 | ERROR_FROM_CACHE (ORIGIN_ERROR) | Invalidate; lower 404 cache TTL |
| 10 | `Accept-Encoding` not in cache key for compressed content | CACHE_KEY_VARIATION (COMPRESSION_CACHE_KEY) | Add `Accept-Encoding` to policy |

### Step 8: Verify the fix

- **Origin header changes:** verify with `curl -I`, request via CloudFront
  twice — second should show `x-cache: Hit from cloudfront`.
- **Cache policy changes:** wait for Deployed status, test with `curl -I` twice.
- **Invalidation:** wait for Completed status, request path — first Miss,
  second Hit.
- **WAF changes:** verify blocked requests now succeed.
- **Lambda@Edge changes:** deploy new version, wait for propagation (minutes).

### Step 9: Decide — ROOT_CAUSE_FOUND vs NEED_MORE_INFO vs ESCALATE

- **ROOT_CAUSE_FOUND.** Walk identified a specific cache issue and config
  element. Output REMEDIATION with exact change.
- **NEED_MORE_INFO.** Operator cannot supply evidence (logs not enabled,
  policy ID unknown). Output the list of missing inputs.
- **ESCALATE.** Cause outside operator's scope (AWS-side event, Lambda@Edge
  owned by another team, WAF managed centrally). Output escalation target.

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

See `references/worked-examples.md` for full worked examples (origin
no-store, User-Agent cache key bloat).

## STRICT output contract

This section codifies the exact output shape the eval harness asserts
against. Every invocation MUST produce output that matches this contract.

### Required output structure

Every response MUST be a single block with these literal labels, in this
order:

```text
DISTRIBUTION: <distribution ID or domain>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <cache issue name> — <specific root cause>
CACHE_ISSUE: <ORIGIN_NO_CACHE | ORIGIN_NO_STORE | CACHE_POLICY_TOO_NARROW |
              CACHE_KEY_BLOAT | TTL_TOO_SHORT | STALE_NO_INVALIDATION |
              ORIGIN_HEADER_OVERRIDE | LAMBDA_EDGE_MUTATION | WAF_BLOCK |
              COMPRESSION_CACHE_KEY | ORIGIN_ERROR | UNKNOWN>
EVIDENCE:
  - <signal source>: <observed value>
  - <signal source>: <observed value>
  - <signal source>: <observed value>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific config change with CLI command>
  2. <verification command>
  3. <post-apply monitoring>
```

### FORBIDDEN output patterns

1. **NEVER diagnose without checking the x-cache header first.** A
   ROOT_CAUSE_FOUND without an EVIDENCE row citing the observed `x-cache`
   value is rejected.
2. **NEVER blame the cache policy without checking origin Cache-Control
   headers — the origin header overrides the policy.** A ROOT_CAUSE_FOUND
   citing `CACHE_POLICY_TOO_NARROW` or `TTL_TOO_SHORT` without EVIDENCE
   showing the origin's actual `Cache-Control` is rejected.
3. **NEVER suggest `/*` invalidation without confirming content is stale.**
   `/*` invalidations are expensive and spike origin load. Always prefer
   path-specific invalidations; reserve `/*` for full-site updates only.
4. **NEVER confuse `no-cache` with `no-store`.** `no-cache` allows caching
   but requires revalidation (RefreshHit/RefreshMiss); `no-store` prohibits
   caching entirely. Mislabeling is rejected.
5. **NEVER substitute lowercase or markdown-styled labels for the literal
   all-caps `DISTRIBUTION:`, `VERDICT:`, `ROOT_CAUSE:`, `CACHE_ISSUE:`,
   `EVIDENCE:`, `ROOT_CAUSE_CATALOG:`, `REMEDIATION:`.** The eval harness
   pattern-matches on exact labels.

### Perfect example output

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

## Anti-Patterns — NEVER (top 5)

1. NEVER assume the cache policy TTL controls caching when the origin sends
   `Cache-Control: no-store`. The origin header overrides the policy unless
   explicitly overridden. Always check the origin's `Cache-Control` first.
2. NEVER include `User-Agent` in the cache key — thousands of distinct
   values fragment the cache. If response truly varies by client, normalize
   the header before including it.
3. NEVER use `CookiesConfig.CookieBehavior: all` unless the response truly
   varies by every cookie. Use `whitelist` with only cookies that affect
   the response.
4. NEVER invalidate `/*` when path-specific invalidation suffices — `/*`
   clears the entire cache, spiking origin load. Use specific paths.
5. NEVER set `MaxTTL` lower than `MinTTL` on a cache policy. Always ensure
   `MinTTL <= DefaultTTL <= MaxTTL`.

See `references/worked-examples.md` for additional anti-patterns (no-cache
vs no-store confusion, x-cache Hit meaning, Accept-Encoding for compressed
content, static vs dynamic mixing).

## Diagnostic command quick reference

Diagnostic command quick-reference listing (config, cache policy, invalidations, CacheHitRate, x-cache probes, origin bypass, Lambda@Edge) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand for live-account probing.

See `references/diagnostic-commands.md` for the full command script per
cache issue category.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when Functions vs Lambda@Edge timing, KeyValueStore, Origin Shield metrics, or Logs-to-CloudWatch are in play.

## References

- `references/cache-key-model.md` — full cache key model with worked examples
- `references/diagnostic-commands.md` — canonical command script per cache issue
- `references/worked-examples.md` — worked examples, managed policy reference,
  cache key normalization, and Lambda@Edge edge cases
- [references/advanced-patterns.md](references/advanced-patterns.md) — senior-engineer heuristics and recent AWS features (2024-2026) moved from SKILL.md

## Domain

AWS CloudOps / CloudFront CDN Caching, Cache Policy, and Edge Performance.

## AWS documentation

- **Amazon CloudFront Developer Guide** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/Introduction.html
- **CloudFront caching** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/ConfiguringCaching.html
- **Cache policies** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/controlling-the-cache-key.html
- **CloudFront access logs** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/AccessLogs.html
- **Lambda@Edge** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/lambda-at-the-edge.html
- **CloudFront metrics** — https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/cloudwatch-monitoring.html
- **CloudFront CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/cloudfront/
