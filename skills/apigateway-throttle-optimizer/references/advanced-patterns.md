# Advanced patterns - API Gateway Throttle Optimizer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

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


## Step 0: Non-obvious behaviours that change the recommendation

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


