# API Gateway Throttle Optimizer — Worked Examples

Full worked examples for each optimization pattern, including REST-to-
HTTP migration, cache enablement, usage plan setup, payload compression,
already-optimal, NEED_MORE_INFO, and an end-to-end walkthrough. Also
includes error handling and extended anti-patterns.

## Example 1: REST-to-HTTP migration (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: api-rest-to-http-api-migration
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: REST API used purely as Lambda proxy — no mapping templates, no
  request validation, no stage caching, no client certificates. Cognito JWT
  authorizer is supported on HTTP API. HTTP API charges $1.00/M vs REST
  $3.50/M (71% reduction). No REST-only features block migration.
RECOMMENDATION:
  Current: REST (REGIONAL), rate=10000/burst=5000, no cache, no usage plans, no compression
  Proposed: HTTP API, rate=10000/burst=5000, no cache, no usage plans, no compression
  Dimensions changed: api-type (Step 1)
  Dimensions checked: api-type → (REST to HTTP)  throttle ✓ (10000 rps adequate)
    usage-plans ✓ (single internal client)  caching ✓ (disabled, but HTTP API does not support caching — evaluate CloudFront separately)
    payload ✓ (no payload data reported)  waf ✓ (not configured)  vpc-endpoint ✓ (REGIONAL, not private)
  Confidence: HIGH — CloudWatch Count 200M/month directly measured;
    resource inventory confirms no REST-only features; Cognito JWT
    authorizer fully supported on HTTP API.
ESTIMATED_SAVINGS:
  Current monthly: $700.00
    requests: 200M / 1M × $3.50 = $700.00
  Projected monthly: $200.00
    requests: 200M / 1M × $1.00 = $200.00
  Monthly saving: $500.00
    ($700.00 − $200.00 = $500.00 ✓)
  Annual saving: $6,000.00
MIGRATION_STEPS:
  1. Create HTTP API with the same routes:
     aws apigatewayv2 create-api --name api-http --protocol-type HTTP --target <lambda-arn>
  2. Configure Cognito JWT authorizer on the HTTP API.
  3. Deploy the HTTP API and create a stage:
     aws apigatewayv2 create-stage --api-id <http-api-id> --stage-name prod
  4. Route a percentage of traffic to the HTTP API via weighted DNS or a load test.
  5. Monitor Count, 4xx, 5xx for 7 days post-cutover.
  6. Decommission the REST API after verification:
     aws apigateway delete-rest-api --rest-api-id <rest-api-id>
CONFIRM: About to create a new HTTP API and migrate traffic from
  api-rest-to-http-api-migration. Monthly saving $500.00 (71% reduction).
  REST API will be decommissioned after 7-day verification. Proceed?
  (yes/no)
```

## Example 2: Cache enablement (FURTHER_OPTIMIZATION_AVAILABLE)

```text
TARGET: api-stage-cache-enablement
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: REST API with 70% idempotent GETs (catalog endpoints changing
  hourly) and caching disabled. Backend IntegrationLatency is 95 ms avg.
  Enabling stage-level caching with TTL=3600s projects a 60% cache hit
  ratio for GET endpoints, eliminating 42M backend Lambda calls/month.
RECOMMENDATION:
  Current: REST, rate=5000/burst=2000, no cache, no compression
  Proposed: REST, rate=5000/burst=2000, stage cache (1.3 GB, TTL=3600s), no compression
  Dimensions changed: caching (Step 4)
  Dimensions checked: api-type ✓ (REST needed for caching)  throttle ✓ (5000 rps adequate)
    usage-plans ✓ (single client)  caching → (enable stage cache)
    payload ✓ (not reported)  waf ✓ (not configured)  vpc-endpoint ✓ (not private)
  Confidence: HIGH — CloudWatch Count and IntegrationLatency measured
    over 30 days; 70% idempotent GET ratio confirmed from request
    breakdown; catalog changes hourly matching TTL=3600.
ESTIMATED_SAVINGS:
  Current monthly: $780.00
    API Gateway: 100M / 1M × $3.50 = $350.00
    Lambda backend: 100M × $0.0000043 = $430.00
  Projected monthly: $621.30
    API Gateway: $350.00 (unchanged)
    Lambda backend: 58M × $0.0000043 = $249.40 (42M cached)
    Cache: 1.3 GB × $0.03/hr × 730 = $28.47
      (Wait — 1.3 GB at $0.03/hr = $21.90/month)
    Cache: $21.90
    Total: $350.00 + $249.40 + $21.90 = $621.30
  Monthly saving: $158.70
    ($780.00 − $621.30 = $158.70 ✓)
  Annual saving: $1,904.40
MIGRATION_STEPS:
  1. Enable stage caching on GET /catalog and GET /catalog/{id} only:
     aws apigateway update-stage --rest-api-id <api-id> --stage-name prod
       --patch-operations op=replace,path=/caching/enabled,value=true
       op=replace,path=/caching/sizeInGB,value=1.3
       op=replace,path=/caching/ttlInSeconds,value=3600
  2. Set per-method cache override on POST /search to disabled (not cacheable).
  3. Monitor CacheHitCount and CacheMissCount for 7 days.
  4. Verify ApproximateAgeOfOldestMessage stays within SLO.
CONFIRM: About to enable stage caching on api-stage-cache-enablement
  (1.3 GB cache, TTL 3600s, GET only). Monthly saving $158.70 (20%
  total reduction, mostly from Lambda backend). Proceed? (yes/no)
```

## Example 3: Already-optimal (OPTIMIZED)

```text
TARGET: api-already-optimized-api
VERDICT: OPTIMIZED
REASON: HTTP API with all seven dimensions at healthy configuration:
  HTTP API ($1.00/M, cheapest), CloudFront caching at 60% hit ratio,
  3-tier usage plans preventing noisy neighbors, gzip compression enabled,
  throttle adequate (5000 rps). No dimension has a savings-bearing
  recommendation.
RECOMMENDATION:
  Current: HTTP API, rate=5000/burst=2000, CloudFront cache (60% hit), 3-tier usage plans, gzip enabled
  Proposed: no change
  Dimensions checked: api-type ✓  throttle ✓  usage-plans ✓  caching ✓  payload ✓  waf ✓  vpc-endpoint ✓
  Confidence: HIGH — all metrics within healthy ranges over 30-day window.
ESTIMATED_SAVINGS:
  Current monthly: $344.98
  Projected monthly: $344.98
  Monthly saving: $0.00
  Annual saving: $0.00
MIGRATION_STEPS:
  1. No action required. Continue monitoring.
CONFIRM: N/A — no state-changing operation.
```

## Example 4: NEED_MORE_INFO (insufficient data)

```text
TARGET: api-new-deployment
VERDICT: NEED_MORE_INFO
REASON: API was deployed 5 days ago. CloudWatch metrics window is < 14 days
  minimum. Count has not yet accumulated enough data to assess caching or
  throttle optimization. Re-evaluate after 14 days of observation.
RECOMMENDATION:
  Current: insufficient data
  Proposed: re-evaluate after 14-day observation window
  Dimensions checked: (not evaluated — data gate failed)
  Confidence: LOW — insufficient observation period.
ESTIMATED_SAVINGS:
  Current monthly: unknown
  Projected monthly: unknown
  Monthly saving: unknown
MIGRATION_STEPS:
  1. Wait 14 days, then re-run optimization analysis.
  2. Ensure CloudWatch detailed metrics are enabled for the API stage.
CONFIRM: N/A — no state-changing operation.
```

## End-to-end walkthrough: multi-dimension optimization

A REST API with both REST-to-HTTP migration potential AND cacheable
endpoints:

```
API: product-catalog-api (REST, 200M req/month)
  Lambda proxy only (no REST-only features)
  70% GETs to catalog (hourly change)
  Caching disabled

Step 1 (api-type): no REST-only features → migrate to HTTP API
  Saving: 200M × ($3.50 − $1.00) / 1M = $500/month

Step 4 (caching): HTTP API doesn't support caching → use CloudFront
  CloudFront cache (1h TTL): 60% hit on 140M GETs = 84M cached
  Lambda saving: 84M × $0.0000043 = $361.20/month
  CloudFront cost: ~$20/month

Combined:
  Current: $700 (API) + $860 (Lambda) = $1,560/month
  Projected: $200 (HTTP API) + $499 (Lambda, 116M uncached) + $20 (CF)
           = $719/month
  Monthly saving: $841.00 (54% reduction)
```

Both dimensions stack because they address different cost sources (API
request cost vs backend compute cost). Apply both in the same
MIGRATION_STEPS.

## Error handling and edge cases

### CLI / data-source failure handling

| Failure | Cause | Recovery |
|---|---|---|
| `get-rest-apis` returns empty | No REST APIs in region | Check `get-apis` for HTTP APIs |
| CloudWatch Count absent | API not deployed or no traffic | Verify stage deployment |
| Stage throttle not set | Inherits account-level default | Note in recommendation |
| WAF Web ACL ARN not found | WAF not attached to API Gateway | Note as "WAF not configured" |

### Migration edge cases

- **Cognito JWT authorizer on HTTP API:** Fully supported but requires
  different configuration (authorizer config differs between REST/HTTP).
- **Custom domain names:** REST and HTTP APIs have separate custom domain
  configurations. Migration requires updating the domain base path mapping.
- **Canary deployments:** REST API supports canary stage settings; HTTP
  API has a simpler deployment model. Plan the cutover strategy before
  migration.
- **API keys:** REST and HTTP APIs use different API key mechanisms.
  Usage plans on HTTP API require API Gateway v2 CLI commands.

### Throttle edge cases

- **Lambda reserved concurrency vs API throttle:** If Lambda reserved
  concurrency < API stage throttle rate, API Gateway returns 502 (not
  429). Align API throttle to Lambda reserved concurrency.
- **429 vs 502 distinction:** 429 = API Gateway throttle (too many
  requests). 502 = backend unavailable (Lambda cold start, concurrency
  exhausted). Both reduce throughput but have different root causes.

### Extended NEVER list

6. NEVER set stage throttle rate higher than backend max concurrency.
   This causes 502 errors, not 429, at peak.
7. NEVER assume cache hit ratio without measuring. Deploy cache, then
   observe CacheHitCount/CacheMissCount for 7 days before sizing.
8. NEVER delete the REST API before verifying the HTTP API replacement.
   Keep both active during the transition period.
9. NEVER recommend HTTP API caching. It does not exist. Use CloudFront
   or backend caching.
10. NEVER recommend compression on responses < 1 KB. The overhead of
    gzip headers exceeds the compression benefit.

# Output format and templates moved from SKILL.md

## Output format — template block

```text
TARGET: <api-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <api type>, <throttle>, <cache>, <usage plans>, <payload strategy>
  Proposed: <api type>, <throttle>, <cache>, <usage plans>, <payload strategy>
  Dimensions changed: <api-type | throttle | usage-plans | caching | payload | waf | vpc-endpoint>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show request + overhead breakdown
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <api-name> in <region>.
  Proceed? (yes/no)"
```


