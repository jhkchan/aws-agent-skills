# Eval prompt: rest-to-http-api-migration

Optimise the following API Gateway for throttle and cost. Walk the
api-type/throttle/caching/usage-plan decision framework and emit the
standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

ApiName: api-rest-to-http-api-migration
ApiType: REST (REGIONAL)
Region: us-east-1
Stage: prod
Stage throttle: rate=10000 rps, burst=5000
Caching: disabled
Usage plans: none (single internal client)
Compression: disabled
WAF: not configured
VPC endpoint: not configured (REGIONAL)

Resources/Methods:
  - GET /products → Lambda proxy integration (no mapping template)
  - GET /products/{id} → Lambda proxy integration (no mapping template)
  - POST /orders → Lambda proxy integration (no mapping template)
  - No request validation schemas
  - No client certificates
  - Authorizer: Cognito User Pool (JWT)

Metrics (last 30 days):
  - Count: 200,000,000/month
  - 4xx: 5,000,000/month (2.5%)
  - 5xx: 100,000/month (0.05%)
  - Latency avg: 120 ms, p95: 250 ms
  - IntegrationLatency avg: 95 ms

Cost data:
  - Monthly cost: $700.00 (200M × $3.50/M)

Workload context: e-commerce product catalog + order submission.
All methods use Lambda proxy integration. No mapping templates,
no request validation, no stage caching. Cognito JWT authorizer
is used (supported on HTTP API).
