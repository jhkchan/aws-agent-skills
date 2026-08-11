---
name: apigateway-throttle-optimizer
description: >-
  Optimises AWS API Gateway throttle and cost across seven dimensions: API
  type selection (REST $3.50/M vs HTTP $1.00/M requests), stage and method-
  level rate/burst throttle tuning, usage plans with API keys for per-
  client throttling, response caching (TTL tuning to eliminate 50-80% of
  integration calls), payload compression (gzip) and field filtering,
  WAF integration cost analysis, and private API VPC endpoint cost.
  Reads CloudWatch metrics (Count, 4xx, 5xx, Latency,
  IntegrationLatency) and projects monthly savings. Emits OPTIMIZED or
  FURTHER_OPTIMIZATION_AVAILABLE with an API-specific recommendation.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline recommendation classification works from pasted
  CloudWatch metrics. Live-account optimization uses aws apigateway
  get-rest-apis, get-stages, get-usage-plans, get-resources, aws
  cloudwatch get-metric-statistics (Count, 4xx, 5xx, Latency,
  IntegrationLatency), aws ce get-cost-and-usage (AWS CLI v2, SSO or
  key-based credentials). Pricing references us-east-1 published rates as
  of 2026; re-state regional rates from the reference matrix for other
  regions.
keywords:
  - API Gateway
  - throttle optimization
  - cost optimization
  - REST API
  - HTTP API
  - rate limit
  - burst limit
  - usage plan
  - API key
  - caching
  - stage throttle
  - method throttle
  - WAF
  - VPC endpoint
  - payload compression
  - gzip
  - data transfer
  - reserved concurrency
  - FinOps
  - AppIntegration
tags:
  - apigateway
  - api
  - app-integration
  - cost-optimization
  - finops
  - throttle
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: >-
    Optimising API Gateway throttle settings, reducing per-request cost
    via REST-to-HTTP API migration, enabling response caching for repeated
    calls, setting up per-client throttling via usage plans, reducing
    payload size via compression, or reviewing WAF/VPC endpoint overhead.
  when_not_to_use: >-
    Lambda function cost behind the API (use lambda-cost-optimizer), Cloud-
    Front distribution cost (use cloudfront-optimizer), or functional API
    Gateway troubleshooting (5xx errors, deployment failures, CORS — use
    the API Gateway troubleshooter). This skill focuses on throttle and
    cost-driven optimization decisions, not functional debugging.
  activation_triggers:
    - optimise API Gateway throttle
    - API Gateway cost optimization
    - REST to HTTP API migration
    - API Gateway caching
    - API Gateway usage plan
    - API Gateway rate limit
    - API Gateway burst limit
    - API Gateway per-client throttle
    - API Gateway payload compression
    - API Gateway WAF cost
    - API Gateway VPC endpoint cost
    - API Gateway FinOps savings
    - reduce API Gateway bill
    - API throttle review
  invocation_schema: >-
    Input: either (a) a REST/HTTP API identifier + live-account context,
    (b) a pasted set of CloudWatch API Gateway metrics with at least 14
    days of observation, OR (c) an API configuration document (API type,
    stage throttle, usage plans, caching, method-level settings).
    Output: a deterministic
    TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS
    block per API, where VERDICT is one of OPTIMIZED,
    FURTHER_OPTIMIZATION_AVAILABLE.
  invocation_example: >-
    # Minimal valid input (offline metric classification):
    ApiName: product-catalog-api
    ApiType: REST (REGIONAL)
    Region: us-east-1
    Stage: prod
    Stage throttle: rate=10000 rps, burst=5000
    Caching: disabled
    Usage plans: none (account-level throttle only)
    Metrics (last 30 days):
      - Count: 200,000,000/month
      - 4xx: 5,000,000/month (2.5%)
      - 5xx: 100,000/month (0.05%)
      - Latency avg: 120 ms, p95: 250 ms
      - IntegrationLatency avg: 95 ms
    Workload: product catalog lookup (read-only, idempotent).
    Emit the standard optimization block (TARGET, VERDICT, REASON,
    RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).
---

# API Gateway Throttle Optimizer

## What this skill does

Translates an API Gateway's configuration and traffic patterns into a
concrete throttle and cost-optimization recommendation with a dollar-
denominated savings estimate. The verdict is the highest-leverage action
across seven dimensions — API type selection, throttle tuning, usage
plans, response caching, payload optimization, WAF/VPC endpoint overhead,
and data transfer — applied in priority order. Always pairs the
recommendation with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Five headline rules and the cost formula | First read |
| Mindset | Why API type is the #1 cost lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying an API |
| Pre-flight data gate | CloudWatch metrics, stage config | Before any recommendation |
| Step 0 non-obvious behaviours | REST vs HTTP feature gaps, WAF, caching | Edge cases |
| Step 1 API type selection | REST to HTTP migration (3x cheaper) | The headline savings dimension |
| Step 2 Throttle tuning | Rate/burst, method vs stage level | Noisy-neighbor protection |
| Step 3 Usage plans + API keys | Per-client rate limiting | Multi-client APIs |
| Step 4 Response caching | TTL tuning, cache hit ratio | Repeated-call workloads |
| Step 5 Payload optimization | Compression, field filtering | Large-payload APIs |
| Step 6 WAF / VPC endpoint cost | Overhead analysis | Private/protected APIs |
| Step 7 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, deployment safety | Before any apply CLI |

## Quick start

- **API type is the #1 cost lever.** REST API charges $3.50/M requests;
  HTTP API charges $1.00/M requests (us-east-1). If the workload is
  proxy-only (Lambda proxy, HTTP proxy, VPC Link), HTTP API is 3.5x
  cheaper. REST API is only needed for request validation, mapping
  templates, API Gateway features not in HTTP API.
- **Cost formula (memorise this):**
  `monthly_cost = (monthly_requests / 1,000,000) × $api_type_rate`
  where REST = $3.50/M and HTTP = $1.00/M (us-east-1).
- **Caching eliminates 50-80% of integration calls.** Response caching
  ($0.02/hour per GB) intercepts repeated identical requests at the API
  Gateway layer. The backend (Lambda, ECS) never sees cached requests —
  no compute cost for those calls.
- **Usage plans prevent noisy-neighbor throttling.** Without per-client
  usage plans, a single aggressive client can consume the entire account-
  level throttle quota. Usage plans + API keys enforce per-client rate
  limits.
- **WAF adds $5/rule/month + $1/M requests inspected.** For low-traffic
  APIs, WAF cost can exceed API Gateway cost. Evaluate WAF necessity per
  stage.

## Mindset

API Gateway cost optimization is primarily an API-type and caching
exercise, not a throttle-tuning exercise. The goal is to route each
request through the cheapest path (HTTP API > REST API), cache responses
at the edge (eliminate backend calls), and enforce per-client rate
limits (prevent cost runaway from a single client) — not to maximize
throttle limits.

Four principles guide every recommendation:

- **API type is the biggest lever.** Moving from REST to HTTP API saves
  71% on per-request cost ($3.50 → $1.00 per million). This is a
  re-deployment, not a configuration change, but the savings compound.
- **Caching is the second lever.** A read-heavy API with cacheable
  responses (product catalog, configuration, static lookups) can
  eliminate 50-80% of backend integration calls. Cache cost ($0.02/hr
  per GB) is trivial compared to the backend compute it replaces.
- **Throttle limits are a protection mechanism, not a cost lever.**
  Tighter throttles reduce cost ONLY if they prevent runaway traffic;
  looser throttles increase availability but do not change per-request
  cost. Usage plans are the key throttle optimization.
- **Payload size affects data transfer cost.** APIs returning large JSON
  payloads (> 100 KB) incur data transfer cost. Compression (gzip)
  reduces transfer volume 5-10x.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| REST API AND no REST-only features used (no mapping templates, no request validation, no method-level auth) AND proxy-only integration | **FURTHER_OPTIMIZATION_AVAILABLE** (type) | Step 1 — migrate to HTTP API (71% request cost reduction) |
| Caching disabled AND > 50% of requests are idempotent GETs with repeating params AND backend IntegrationLatency > 50 ms | **FURTHER_OPTIMIZATION_AVAILABLE** (caching) | Step 4 — enable stage-level caching with TTL |
| No usage plans AND > 3 distinct clients AND 4xx throttle errors > 1% of Count | **FURTHER_OPTIMIZATION_AVAILABLE** (usage plans) | Step 3 — create per-client usage plans with API keys |
| Payload avg > 100 KB AND compression disabled | **FURTHER_OPTIMIZATION_AVAILABLE** (payload) | Step 5 — enable gzip compression, filter response fields |
| WAF enabled AND request volume < 10M/month AND no compliance requirement | **FURTHER_OPTIMIZATION_AVAILABLE** (WAF) | Step 6 — evaluate WAF cost vs benefit |
| Private API via VPC endpoint AND < 1M requests/month | **FURTHER_OPTIMIZATION_AVAILABLE** (VPC endpoint) | Step 6 — evaluate VPC endpoint cost vs public API + auth |
| Account-level throttle only AND single client consuming > 80% of capacity | **FURTHER_OPTIMIZATION_AVAILABLE** (throttle) | Step 2 — set per-client throttle via usage plan |
| All dimensions verified AND no further savings-bearing action | **OPTIMIZED** | Continue monitoring |
| Metrics absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/apigateway-pricing-and-throttle-reference.md`.

**Required data sources** (summarized — see reference for full CLI):
1. API configuration: `aws apigateway get-rest-apis` / `get-apis` (HTTP)
2. Stage configuration: `aws apigateway get-stages` (throttle, cache)
3. Usage plans: `aws apigateway get-usage-plans`
4. Resources/methods: `aws apigateway get-resources` (auth, integration
   type, method-level throttle)
5. CloudWatch metrics (14-30 day): `aws cloudwatch get-metric-statistics`
6. Cost data: `aws ce get-cost-and-usage` filtered by Service=APIGateway

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `Count` metric absent (API never called) | **NEED_MORE_INFO**. Verify stage deployment; skip until traffic exists. |
| `Count` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "dormant API." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `IntegrationLatency` absent | Fall back to `Latency` only; mark caching recommendation MEDIUM confidence. |
| Stage not deployed (no deployment) | Surface as BLOCKED — API has no active deployment. |
| Cannot distinguish REST vs HTTP from API config | Use `get-rest-apis` (REST) vs `get-apis` (HTTP) — they are separate API surfaces. |

When CloudWatch and Cost Explorer disagree, CloudWatch Count is the
source of truth (Cost Explorer may aggregate across APIs without
per-API tags).

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **REST and HTTP APIs are different services.** REST API uses
  `get-rest-apis` / `update-stage`; HTTP API uses `get-apis` /
  `update-api`. They have different feature sets, pricing, and CLI
  commands. Migration is a re-deployment, not a config change.
- **HTTP API does NOT support: mapping templates, request validation,
  API Gateway CORS (must be handled at integration), client certificates,
  WAF (added 2024 but only for HTTP API in select regions), method-level
  request/response models.** If any of these are in use, REST is
  required — do not recommend migration.
- **Caching is REST-only (stage level).** HTTP API does not support
  response caching natively (as of 2026). Cache at CloudFront or the
  backend instead.
- **Cache TTL is per-method, but cache capacity is per-stage.** A 0.5 GB
  cache at $0.02/hr serves ~5000 unique cache keys (avg 100 KB response).
  Size the cache for the working set, not the total key count.
- **Usage plans require API keys.** API keys are sent as `x-api-key`
  header. Clients MUST include this header — adding usage plans to an
  existing API requires a client-side change.
- **WAF on API Gateway costs per-rule AND per-request.** $5/rule/month +
  $1/M requests inspected. At low traffic, the per-rule cost dominates;
  at high traffic, the per-request cost dominates.
- **Private API (VPC endpoint) charges $0.01/hour + $0.01/GB.** For low-
  traffic private APIs, the hourly cost ($7.30/month) can exceed the API
  request cost.
- **Data transfer out (DTO) is billed on response payload.** API
  Gateway does not compress responses by default. A 500 KB JSON response
  to 1M clients = 500 GB DTO ($0.09/GB = $45/month in transfer alone).
- **Account-level throttle applies to ALL APIs in the region.** Setting
  a high account-level throttle does not help if one API consumes all
  capacity. Usage plans are the per-client mechanism.
- **Lambda reserved concurrency caps API throughput.** If the backend is
  Lambda with reserved concurrency = 100, API Gateway returns 502 (not
  429) when concurrency is exhausted. The API throttle should be lower
  than Lambda reserved concurrency.
- **Stage throttle overrides account-level.** Method-level throttle
  overrides stage-level. The most specific throttle wins.

### Step 1: API type selection (REST to HTTP migration)

REST API ($3.50/M) vs HTTP API ($1.00/M). For proxy-only workloads
(Lambda proxy integration, HTTP proxy, VPC Link), HTTP API is 3.5x
cheaper and simpler.

**Migration checklist:**

| REST feature in use? | Blocks HTTP API migration? |
|---|---|
| Lambda proxy integration | NO — fully supported on HTTP API |
| HTTP proxy integration | NO — fully supported |
| VPC Link integration | NO — supported on HTTP API |
| Mapping templates (Velocity) | YES — HTTP API has no mapping templates |
| Request validation (schema) | YES — HTTP API has no request validation |
| Method-level authorization (Lambda authorizer) | Partially — HTTP API supports JWT authorizers but not custom Lambda authorizers (added 2025 in select regions) |
| API Gateway-managed CORS | YES — HTTP API has built-in CORS config, different model |
| Client certificates to backend | YES — HTTP API does not support mutual TLS to backend (as of 2026) |
| Stage-level caching | YES — HTTP API has no response caching |
| WAF Web ACL attachment | Partially — HTTP API WAF support added 2024, REST API fully supported |

**Decision gate:**

| REST features in use | Can migrate to HTTP? | Verdict |
|---|---|---|
| Lambda proxy only | YES | **FURTHER_OPTIMIZATION_AVAILABLE** |
| Proxy + request validation | NO (validation is REST-only) | Not recommended; stay on REST |
| Proxy + mapping templates | NO | Not recommended; stay on REST |
| Proxy + stage caching | Evaluate: cache savings vs type savings | Run Step 4 first, then re-evaluate |

**Savings math:**
```
monthly_saving = (monthly_requests / 1M) × ($3.50 − $1.00)
              = (monthly_requests / 1M) × $2.50

Example: 200M requests/month → 200 × $2.50 = $500/month
```

### Step 2: Throttle tuning (rate and burst limits)

Throttle tuning is primarily about availability protection, not cost.
The one cost impact: tighter throttles prevent cost runaway from
unauthorized traffic spikes.

**Stage-level vs method-level:**

| Throttle level | Scope | When to use |
|---|---|---|
| Account-level (default) | All APIs in region | Last-resort cap |
| Stage-level | All methods in a stage | Per-environment protection |
| Method-level | Single method | Per-endpoint tuning (e.g., expensive POST vs cheap GET) |

**Setting throttle to match backend capacity:**
```
max_rate = backend_max_concurrent / avg_integration_latency_s

Example: Lambda reserved concurrency = 200, avg latency = 0.1s
  max_rate = 200 / 0.1 = 2000 rps
  Set stage throttle: rate=2000, burst=1000
```

```bash
aws apigateway update-stage \
  --rest-api-id <api-id> \
  --stage-name prod \
  --patch-operations op=replace,path=/throttle/rateLimit,value=2000 op=replace,path=/throttle/burstLimit,value=1000
```

### Step 3: Usage plans + API keys (per-client throttling)

Usage plans enforce per-client rate and burst limits. Without them, a
single client can consume the entire stage/account throttle quota.

**Decision gate:**

| Condition | Verdict | Action |
|---|---|---|
| > 3 distinct clients AND no usage plans | **FURTHER_OPTIMIZATION_AVAILABLE** | Create usage plan per client tier |
| 1 client (internal service) | No finding | Usage plan adds overhead without benefit |
| Usage plans exist AND 4xx throttle rate < 0.1% | No finding | Per-client throttling is effective |

**Usage plan tiers (example):**

| Tier | Rate | Burst | Quota | Target |
|---|---|---|---|---|
| Free | 5 rps | 10 | 1M/month | Trial users |
| Pro | 50 rps | 100 | 50M/month | Paid customers |
| Enterprise | 500 rps | 1000 | Unlimited | Enterprise contracts |

```bash
aws apigateway create-usage-plan-key \
  --usage-plan-id <plan-id> \
  --key-id <api-key-id> \
  --key-type API_KEY
```

### Step 4: Response caching (TTL tuning)

Response caching is the single most effective cost reducer for read-
heavy APIs. Cache intercepts identical requests at the API Gateway layer;
the backend never sees cached requests.

**REST-only feature.** HTTP API does not support response caching (as
of 2026).

**Cache cost vs benefit:**
```
cache_cost = cache_size_GB × $0.02 × 730 hours/month

Example: 1.3 GB cache = $18.98/month

backend_saving = cached_requests × backend_cost_per_request
Example: 100M cached requests × $0.0000043 (Lambda avg) = $430/month

Net monthly saving: $430 − $18.98 = $411.02/month
```

**Decision gate:**

| Condition | Verdict | Action |
|---|---|---|
| Caching disabled AND > 50% idempotent GETs AND IntegrationLatency > 50 ms | **FURTHER_OPTIMIZATION_AVAILABLE** | Enable stage-level caching |
| Caching enabled AND cache hit rate < 20% | **FURTHER_OPTIMIZATION_AVAILABLE** | Increase TTL or reduce cache scope to high-hit methods |
| Caching enabled AND cache hit rate > 50% | No finding | Cache is effective |

**TTL tuning:**
- Default TTL: 300 seconds. Start here for most read APIs.
- Product catalog (changes hourly): TTL 3600 (1 hour).
- Configuration API (changes daily): TTL 86400 (1 day).
- User-specific data: TTL 0 (no cache) or use cache key variation.

```bash
aws apigateway update-stage \
  --rest-api-id <api-id> \
  --stage-name prod \
  --patch-operations op=replace,path=/caching/enabled,value=true \
                    op=replace,path=/caching/cacheClusterStatus,value=AVAILABLE \
                    op=replace,path=/caching/sizeInGB,value=1.3 \
                    op=replace,path=/caching/ttlInSeconds,value=300
```

### Step 5: Payload optimization (compression and field filtering)

Large payloads increase data transfer cost and latency. API Gateway does
NOT compress responses by default; the backend or CloudFront must handle
gzip.

**Compression math:**
```
uncompressed_transfer = requests × avg_payload_KB / 1024
compressed_transfer = uncompressed_transfer × 0.3 (typical gzip ratio for JSON)

Example: 100M requests × 200 KB = 19,531 GB uncompressed
  Compressed (30%): 5,859 GB
  DTO saving: 13,672 GB × $0.09/GB = $1,230.48/month
```

**Decision gate:**

| Condition | Verdict | Action |
|---|---|---|
| Avg payload > 100 KB AND compression disabled | **FURTHER_OPTIMIZATION_AVAILABLE** | Enable gzip at backend or CloudFront |
| Response includes unused fields (over-fetching) | **FURTHER_OPTIMIZATION_AVAILABLE** | Implement field filtering (GraphQL or sparse fieldsets) |
| Avg payload < 10 KB | No finding | Compression overhead not justified |

**Enable gzip on REST API (backend must send Content-Encoding: gzip):**
```bash
aws apigateway update-rest-api \
  --rest-api-id <api-id> \
  --patch-operations op=add,path=/minimumCompressionSize,value=1024
```

### Step 6: WAF and VPC endpoint cost analysis

**WAF on API Gateway:**
```
waf_cost = (rules × $5/month) + (requests_inspected / 1M × $1)

Example: 5 rules, 100M requests/month
  Rule cost: 5 × $5 = $25/month
  Request cost: 100 × $1 = $100/month
  Total: $125/month
```

**Private API via VPC endpoint:**
```
vpc_endpoint_cost = ($0.01 × 730 hours) + (data_transfer_GB × $0.01)

Example: $7.30/month + 10 GB × $0.01 = $7.40/month
```

**Decision gate:**

| Condition | Verdict | Action |
|---|---|---|
| WAF enabled AND < 10M requests/month AND no compliance mandate | **FURTHER_OPTIMIZATION_AVAILABLE** | Evaluate WAF cost vs security benefit |
| Private API via VPC endpoint AND < 1M requests/month | **FURTHER_OPTIMIZATION_AVAILABLE** | Evaluate public API + IAM/Cognito auth as alternative |
| WAF enabled AND > 100M requests/month AND compliance required | No finding | WAF is justified |

### Step 7: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (monthly_requests / 1M) × $api_type_rate
  + cache_cost (if enabled)
  + waf_cost (if enabled)
  + vpc_endpoint_cost (if private API)
  + data_transfer_cost (payload_GB × $0.09/GB)

projected_monthly_cost =
  (projected_requests / 1M) × $projected_api_type_rate
  + projected_cache_cost
  + projected_waf_cost
  + projected_vpc_endpoint_cost
  + projected_data_transfer_cost

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: monthly request count, API type (current and
proposed), cache hit ratio, payload size, pricing region.

### Step 8: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND API is optimally configured → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (with post-
  state verification note).
- Data insufficient (metrics absent, window < 14 days) →
  **NEED_MORE_INFO**.

## Output format

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

Full worked examples in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <api-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <api type>, <throttle>, <cache>, <usage plans>, <payload>
  Proposed: <api type>, <throttle>, <cache>, <usage plans>, <payload>
  Dimensions changed: <api-type | throttle | usage-plans | caching | payload | waf | vpc-endpoint>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show breakdown subtotals
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00`.** If every dimension nets zero cost delta,
   the verdict MUST be `OPTIMIZED`.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "corrected:") in
   the output. Finalize the math before emitting.

4. **NEVER recommend REST-to-HTTP migration without verifying no REST-
   only features are in use.** Mapping templates, request validation,
   and stage caching are REST-only. The REASON MUST name the feature
   check.

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER recommend response caching on an HTTP API.** HTTP API does
   not support response caching (as of 2026). Recommend CloudFront or
   backend caching instead.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

```text
TARGET: product-catalog-api
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: REST API used purely as a Lambda proxy (no mapping templates, no
  request validation, no stage caching). HTTP API supports Lambda proxy
  integration at $1.00/M vs REST $3.50/M (71% reduction). Additionally,
  caching is disabled but 70% of requests are idempotent GETs to a
  catalog that changes hourly — caching would eliminate 50% of backend
  calls. No REST-only features block migration.
RECOMMENDATION:
  Current: REST (REGIONAL), rate=10000/burst=5000, no cache, no usage plans, no compression
  Proposed: HTTP API, rate=10000/burst=5000, CloudFront cache (1h TTL), no usage plans, gzip
  Dimensions changed: api-type (Step 1) + caching (Step 4, via CloudFront) + payload (Step 5)
  Dimensions checked: api-type → (REST to HTTP)  throttle ✓ (10000 rps adequate)
    usage-plans ✓ (single internal client)  caching → (enable CloudFront cache)
    payload → (enable gzip)  waf ✓ (not configured)  vpc-endpoint ✓ (regional, not private)
  Confidence: HIGH — CloudWatch Count 200M/month directly measured; no
    REST-only features found in resource/method inventory; catalog GETs
    are idempotent with hourly change frequency.
ESTIMATED_SAVINGS:
  Current monthly: $700.00
    requests: 200M / 1M × $3.50 = $700.00
  Projected monthly: $260.00
    requests: 200M / 1M × $1.00 = $200.00
    CloudFront cache: $18.98 (1.3 GB cache, 50% hit ratio saves 100M Lambda calls)
    gzip: cost-neutral at API Gateway level; saves $1,230/mo DTO (credited at CloudFront)
  Monthly saving: $440.00
    ($700.00 − $260.00 = $440.00 ✓)
  Annual saving: $5,280.00
MIGRATION_STEPS:
  1. Create HTTP API with Lambda proxy integration:
     aws apigatewayv2 create-api --name product-catalog-http --protocol-type HTTP --target <lambda-arn>
  2. Create a CloudFront distribution with the HTTP API as origin, cache TTL 3600s.
  3. Configure CloudFront compression = true (gzip).
  4. Deploy the new HTTP API and route traffic via CloudFront.
  5. Monitor Count, 4xx, 5xx, Latency for 7 days post-cutover.
  6. Decommission the REST API after verification.
CONFIRM: About to create a new HTTP API (product-catalog-http) and
  CloudFront distribution for product-catalog-api. Monthly saving $440.00
  (63% reduction). REST API will be decommissioned after 7-day
  verification. Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] REST-to-HTTP migration verified no REST-only features in use?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | All dimensions pass (optimal API type, throttle right-sized, caching effective, usage plans in place). |
| `NEED_MORE_INFO` | Data gate failed: metrics absent or window < 14 days. |
| `BLOCKED` | Hard precondition prevents evaluation: API not deployed, IAM denies apigateway:GET. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: a throttle improvement that prevents cost runaway (usage plan
on an unthrottled multi-client API) is surfaced in REASON as a risk
mitigation, not as dollar savings.

## Configuration dependency graph

```
API type (REST / HTTP)
 ├─ determines: per-request cost ($3.50/M REST vs $1.00/M HTTP)
 ├─ determines: feature set (REST: caching, validation, templates; HTTP: proxy-only)
 └─ affects: which optimization dimensions are available (cache is REST-only)

Stage throttle (rate + burst)
 ├─ protects: backend from traffic spikes
 ├─ interacts with: account-level throttle (more specific wins)
 └── if too high: backend overload (502 errors)

Usage plans (per-client throttle)
 ├─ requires: API keys (x-api-key header)
 ├─ prevents: noisy-neighbor throttling across clients
 └── if absent: single client can monopolize stage throttle

Response caching (REST-only, stage-level)
 ├─ eliminates: 50-80% of backend integration calls
 ├─ TTL determines: cache freshness vs hit ratio tradeoff
 └── cache size: must match working set (unique cache keys × avg response size)

WAF Web ACL
 ├─ adds: $5/rule/month + $1/M requests inspected
 └── at low traffic: rule cost dominates; at high traffic: request cost dominates

VPC endpoint (private API)
 ├─ adds: $0.01/hour + $0.01/GB
 └── for low-traffic APIs: hourly cost may exceed request cost
```

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend REST-to-HTTP migration without verifying no REST-only
   features are in use.** Mapping templates, request validation, stage
   caching, and custom Lambda authorizers are REST-only. The REASON MUST
   name the feature check.

2. **NEVER recommend response caching on an HTTP API.** HTTP API does
   not support response caching (as of 2026). Recommend CloudFront or
   backend caching instead.

3. **NEVER enable caching without verifying the working set fits in the
   cache.** If unique cache keys exceed cache capacity, the cache
   thrashes and hit rate drops below 10%. Size the cache for the working
   set.

4. **NEVER add usage plans without warning the operator that clients MUST
   include the `x-api-key` header.** Adding usage plans to an existing
   API requires a client-side change. Missing API key results in 403
   Forbidden.

5. **NEVER set stage throttle higher than the backend's max concurrency.**
   If Lambda reserved concurrency is 100 and stage throttle allows 5000
   rps, API Gateway returns 502 (backend overload) at peak. Align
   throttle to backend capacity.

Extended anti-patterns in `references/worked-examples.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval.
- **REST-to-HTTP migration requires a new API deployment.** Create HTTP
  API alongside REST, route traffic, verify, then decommission REST.
- **Caching changes affect all methods in the stage.** Test on staging
  first; verify cache hit rate and response freshness.
- **Usage plan deployment requires client coordination.** Clients must
  add the `x-api-key` header; notify before enforcing.
- **Throttle decreases may reject valid traffic.** Verify the new rate
  covers peak observed traffic with headroom.
- **WAF removal reduces security posture.** Only recommend evaluation,
  not automatic removal.
- **Bulk-operation limit:** Process at most 5 APIs per batch. Abort if
  any API shows increased 5xx errors post-change.

## Recent AWS features (2024-2026)

- **HTTP API WAF support (2024-2025):** WAF Web ACL can now be attached
  to HTTP APIs (previously REST-only). Region availability expanding.
- **HTTP API custom authorizers (2025):** Lambda authorizer support added
  to HTTP API in select regions, reducing the feature gap with REST.
- **API Gateway data export (2024):** Access logs can be exported to
  CloudWatch Logs, S3, Kinesis for per-request analysis.
- **Stage variables enhancement (2024):** Stage variables now support
  canary deployment configurations, enabling gradual API-type migration
  (route 10% traffic to HTTP API, 90% to REST).
- **CloudFront compression for API Gateway origins (2024):** CloudFront
  can compress API Gateway responses (gzip/Brotli), reducing DTO cost
  for HTTP API workloads that lack native compression.

## References

- `references/apigateway-pricing-and-throttle-reference.md` — pricing
  tables for REST/HTTP APIs, cache sizing, WAF/VPC endpoint cost,
  throttle limit ranges, regional pricing multipliers, cost calculation
  worked examples, CLI quick reference.
- `references/worked-examples.md` — full worked examples (REST-to-HTTP
  migration, cache enablement, usage plan setup, payload compression,
  already-optimal, NEED_MORE_INFO) plus error handling, CLI failure
  recovery, and extended NEVER list.

## Domain

AWS CloudOps / API Gateway Throttle & Cost Optimization, AppIntegration
family.

## AWS documentation

- **Amazon API Gateway Developer Guide** — https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html
- **API Gateway pricing** — https://aws.amazon.com/api-gateway/pricing/
- **API Gateway quotas** — https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-limits.html
- **API Gateway REST vs HTTP API** — https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-vs-rest.html
- **API Gateway caching** — https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-caching.html
- **API Gateway usage plans** — https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html
- **API Gateway throttling** — https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html
- **API Gateway payload compression** — https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-enable-compression.html
- **WAF + API Gateway** — https://docs.aws.amazon.com/waf/latest/developerguide/apigateway-as-source.html
- **AWS CLI API Gateway reference** — https://docs.aws.amazon.com/cli/latest/reference/apigateway/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
