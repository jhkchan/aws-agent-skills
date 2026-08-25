# Advanced Patterns (load on demand) — CloudFront Cache Troubleshooter

Expert knowledge and recent features moved verbatim from SKILL.md: the five senior-CDN-engineer heuristics and the 2024-2026 feature notes.


---

## Expert heuristic — five senior-CDN-engineer behaviours (moved from SKILL.md)

Five non-obvious behaviors that a senior CDN engineer knows from
operational experience. Each changes the diagnostic conclusion if
missed:

- **Cache hit ratio reported by CloudFront is edge-only, not end-to-
  end.** The `CacheHitRate` metric measures the percentage of requests
  served from edge POPs without going to the origin. But the "true"
  hit ratio also depends on whether Origin Shield is enabled. Without
  Origin Shield, each of the 400+ edge POPs maintains its own
  independent cache. A distribution with 1M unique objects and 50
  requests/object may show a 95% edge hit rate but still send 20,000+
  origin requests (one per object per POP that sees traffic). With
  Origin Shield, all POPs share a single second-tier cache, collapsing
  those 20,000 origin requests into ~1,000. The reported
  `CacheHitRate` does not change, but origin load drops by 95%.

- **Lambda@Edge execution time is NOT included in the cache key, but
  it affects whether a response is cacheable.** If a `viewer-request`
  or `origin-request` function takes > 30 seconds, CloudFront drops
  the connection (504) even if the origin would have returned a
  cacheable 200. More subtly, an `origin-response` function that
  modifies headers (e.g., adding `Cache-Control: no-store`) overrides
  the origin's cacheability directive. The function's execution time
  is billed separately and does not appear in the `Age` header. When
  diagnosing cache misses on behaviors with Lambda@Edge, always check
  whether the function is rewriting cache headers — the cache policy
  may be correct but the function is overriding it at runtime.

- **Origin Shield doubles the cache storage cost but can halve origin
  requests.** Origin Shield is billed at the same data transfer rate
  as standard CloudFront-to-origin traffic, but it adds a second cache
  layer. For distributions with high object count and low per-object
  request volume, Origin Shield's cost can exceed the origin request
  savings. Break-even is typically ~3 requests per object per POP per
  TTL window. Below that, Origin Shield is a net cost increase; above
  it, a net savings.

- **Compressed objects have strict size limits; uncompressed have no
  explicit limit but face practical timeouts.** CloudFront
  auto-compresses objects between 1,000 and 50,000,000 bytes when
  `Compress: true` is set on the cache behavior. Objects above 50 MB
  are never compressed. For objects between 50 MB and 20 GB, the
  response is streamed uncompressed. Objects above 20 GB fail with a
  502. S3 multipart uploads that produce objects > 50 MB will not
  benefit from CloudFront compression regardless of the cache policy
  setting — the compression eligibility check happens before the
  cache lookup.

- **CloudFront Functions and Lambda@Edge have fundamentally different
  caching interaction models.** CloudFront Functions run at the viewer
  edge in a sub-millisecond VM; they execute on every request and do
  NOT see cached responses — they run before the cache lookup.
  Lambda@Edge `origin-response` and `viewer-response` functions run
  AFTER the cache lookup and can modify the cached response. A common
  mistake is using a CloudFront Function to add headers that should
  influence caching (e.g., `Vary`) — the function runs too early in
  the request lifecycle for the header to affect the cache key. Use a
  cache policy or origin-response Lambda@Edge for header-based cache
  key variation.


---

## Recent AWS features (2024-2026) (moved from SKILL.md)

- **CloudFront Functions vs Lambda@Edge execution model (2024-2025):**
  CloudFront Functions run before cache lookup in a sub-millisecond VM
  at every edge; Lambda@Edge `origin-response`/`viewer-response` run
  after cache lookup. Functions cannot influence the cache key; use a
  cache policy or Lambda@Edge for header-based cache variation.
- **CloudFront KeyValueStore for Lambda@Edge (2024 GA):** Lightweight KV
  store accessible from Lambda@Edge without calling origin. Reduces origin
  calls in edge logic, improving cache hit ratio.
- **CloudFront Origin Shield enhancements (2024-2025):** Improved hit ratio
  metrics and finer-grained control. Use as second-tier cache.
- **CloudFront additional metrics (2024-2025):** Per-cache-behavior metrics
  including `OriginRequestCount`, `4xxErrorRate`, `5xxErrorRate`. Isolate
  cache issues to specific behaviors.
- **Cache policy override improvements (2024):** Better support for
  overriding origin `Cache-Control` via policy's `OriginCacheControlHeaders`.
- **CloudFront Logs to CloudWatch Logs (2024-2025):** Direct export to
  CloudWatch Logs enabling real-time analysis via Logs Insights.
- **Response Headers Policy (2024-2025):** More granular control over
  security headers (HSTS, CSP) without Lambda@Edge.
