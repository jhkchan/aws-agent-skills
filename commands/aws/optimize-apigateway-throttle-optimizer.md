---
description: >-
  Optimise API Gateway throttle and cost through REST-to-HTTP API migration
  (3.5x cheaper), response caching (eliminate 50-80% of integration calls),
  per-client usage plans, payload compression, WAF/VPC endpoint cost
  analysis, and throttle right-sizing with monthly savings estimates.
nl_triggers:
  - "optimise API Gateway throttle"
  - "API Gateway cost optimization"
  - "REST to HTTP API migration"
  - "API Gateway caching"
  - "API Gateway usage plan"
  - "API Gateway rate limit"
  - "API Gateway burst limit"
  - "API Gateway per-client throttle"
  - "API Gateway payload compression"
  - "API Gateway WAF cost"
  - "API Gateway VPC endpoint cost"
  - "API Gateway FinOps savings"
  - "reduce API Gateway bill"
  - "API throttle review"
routes_to: apigateway-throttle-optimizer
---

# /aws:optimize-apigateway-throttle-optimizer

Activate the `apigateway-throttle-optimizer` skill and optimize an API
Gateway's throttle and cost configuration across seven dimensions: API
type selection, throttle tuning, usage plans, response caching, payload
optimization, WAF/VPC endpoint overhead, and data transfer.

## What it does

Reads an API's CloudWatch metrics (Count, 4xx, 5xx, Latency,
IntegrationLatency), API configuration (REST vs HTTP, stage throttle,
caching, usage plans, resources/methods), WAF/VPC endpoint settings,
and payload characteristics, then applies the ordered optimization
logic:

1. **Pre-flight** — data sufficiency gate. If metrics are absent or
   window < 14 days, emits NEED_MORE_INFO. If API is dormant (0
   requests), emits OPTIMIZED.
2. **API type selection** — REST-to-HTTP migration if no REST-only
   features are in use (71% request cost reduction: $3.50/M to $1.00/M).
3. **Throttle tuning** — rate/burst right-sizing to backend capacity.
   Method-level overrides for expensive endpoints.
4. **Usage plans + API keys** — per-client rate limiting to prevent
   noisy-neighbor throttling.
5. **Response caching** — stage-level caching (REST) or CloudFront cache
   (HTTP) for idempotent GET workloads (50-80% backend call reduction).
6. **Payload optimization** — gzip compression and field filtering for
   large-payload APIs.
7. **WAF / VPC endpoint cost** — overhead analysis for low-traffic APIs
   where per-rule or per-hour costs dominate.
8. **Impact estimation** — monthly + annual savings, assumptions
   documented.
9. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
   recommendation) or OPTIMIZED (all dimensions pass).

Emits a deterministic optimization block per API:

```text
TARGET: <api-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <api type>, <throttle>, <cache>, <usage plans>, <payload>
  Proposed: <api type>, <throttle>, <cache>, <usage plans>, <payload>
  Dimensions changed: <api-type | throttle | usage-plans | caching | payload>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste an API's metrics and ask any of:

- "optimise this API Gateway's cost"
- "should I migrate REST to HTTP API?"
- "should I enable API Gateway caching?"
- "how do I set up per-client throttling?"
- "is my API Gateway throttle too high?"
- "should I compress API Gateway responses?"
- "is WAF costing too much for this API?"
- "API Gateway cost optimization review"

A bare API name + any optimization verb ("optimize this API", "cost
review") also routes here via the orchestrator.

## Inputs

- API metadata: name, API type (REST / HTTP), region, stage, stage
  throttle (rate, burst).
- CloudWatch metrics (last 14-30 days):
  - `Count` (Sum)
  - `4xx` (Sum)
  - `5xx` (Sum)
  - `Latency` (Average, p95)
  - `IntegrationLatency` (Average)
- API configuration: resources/methods, integration type, authorizers,
  mapping templates, request validation, client certificates.
- Stage configuration: caching (enabled, size, TTL), usage plans, API
  keys.
- Payload characteristics: avg response size, compression status, DTO
  volume.
- Optional: WAF Web ACL configuration, VPC endpoint settings, Lambda
  reserved concurrency (backend capacity alignment).
- Workload context: API type requirements (ordering, validation, auth),
  client count, traffic patterns.

## Outputs

- One optimization block per API.
- Confidence level with rationale.
- Estimated monthly and annual savings, broken down by dimension.
- Specific migration steps with CLI commands (apigatewayv2 create-api,
  update-stage, create-usage-plan, update-rest-api).
- Throttle impact surfaced alongside cost (usage plan may prevent cost
  runaway without direct dollar savings).
- Side-by-side migration plan for REST-to-HTTP (never delete REST API
  before verifying HTTP replacement).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for API Gateway cost).
- `/aws:optimize-sqs-throughput-optimizer` for SQS queue throughput and
  cost optimization (the AppIntegration family counterpart for SQS).
- `/aws:optimize-lambda-cost` for the Lambda backend cost behind the API
  (caching reduces Lambda invocations — coordinate both optimizations).
