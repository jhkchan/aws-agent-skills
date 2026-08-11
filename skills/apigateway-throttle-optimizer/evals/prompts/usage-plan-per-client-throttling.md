# Eval prompt: usage-plan-per-client-throttling

Optimise the following API Gateway for throttle and cost. Walk the
throttle/usage-plan decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

ApiName: api-usage-plan-per-client-throttling
ApiType: REST (REGIONAL)
Region: us-east-1
Stage: prod
Stage throttle: rate=2000 rps, burst=1000 (account-level only)
Caching: disabled
Usage plans: none
Compression: disabled

Resources/Methods:
  - GET /users/{id} → Lambda proxy
  - POST /data → Lambda proxy
  - GET /reports → Lambda proxy

Metrics (last 30 days):
  - Count: 150,000,000/month
  - 4xx: 15,000,000/month (10% — mostly 429 Too Many Requests)
  - 5xx: 75,000/month (0.05%)
  - Latency avg: 80 ms, p95: 150 ms
  - IntegrationLatency avg: 65 ms

Client breakdown:
  - Mobile App (iOS): 120M requests/month (80% of traffic)
  - Web Dashboard: 15M requests/month (10%)
  - Partner Integration A: 7.5M requests/month (5%)
  - Partner Integration B: 5.25M requests/month (3.5%)
  - Internal CLI tool: 2.25M requests/month (1.5%)

429 throttle analysis:
  - Mobile App consuming 80% of 2000 rps stage throttle
  - Other clients getting 429 when mobile app spikes
  - 15M 429 errors/month = 10% of total requests

Cost data:
  - Monthly cost: $525.00 (150M × $3.50/M)

Workload context: multi-tenant SaaS API serving 5 distinct client
applications. Mobile app is the noisiest neighbor. Need per-client
rate limiting so one client cannot starve others.
