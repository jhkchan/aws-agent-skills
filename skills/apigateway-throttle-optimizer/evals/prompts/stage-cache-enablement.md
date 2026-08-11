# Eval prompt: stage-cache-enablement

Optimise the following API Gateway for throttle and cost. Walk the
api-type/throttle/caching decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

ApiName: api-stage-cache-enablement
ApiType: REST (REGIONAL)
Region: us-east-1
Stage: prod
Stage throttle: rate=5000 rps, burst=2000
Caching: disabled
Usage plans: none (single client)
Compression: disabled

Resources/Methods:
  - GET /catalog → Lambda proxy (product lookup, changes hourly)
  - GET /catalog/{id} → Lambda proxy (product detail, changes hourly)
  - POST /search → Lambda proxy (dynamic search, NOT cacheable)

Metrics (last 30 days):
  - Count: 100,000,000/month
  - 4xx: 2,000,000/month (2%)
  - 5xx: 50,000/month (0.05%)
  - Latency avg: 110 ms, p95: 200 ms
  - IntegrationLatency avg: 95 ms

Request breakdown:
  - GET /catalog: 40M/month (idempotent, hourly change)
  - GET /catalog/{id}: 30M/month (idempotent, hourly change)
  - POST /search: 30M/month (dynamic, NOT cacheable)
  - Idempotent GET ratio: 70%

Cost data:
  - Monthly cost: $350.00 (100M × $3.50/M)
  - Backend Lambda cost: $430.00 (100M invocations × ~95ms)

Workload context: product catalog API. GET endpoints return data
that changes hourly. POST search is dynamic and not cacheable.
No mapping templates or REST-only features beyond caching.
