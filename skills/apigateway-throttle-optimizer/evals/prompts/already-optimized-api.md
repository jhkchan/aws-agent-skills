# Eval prompt: already-optimized-api

Optimise the following API Gateway for throttle and cost. Walk the
api-type/throttle/caching/usage-plan/payload decision framework and
emit the standard optimization block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

ApiName: api-already-optimized-api
ApiType: HTTP (REGIONAL)
Region: us-east-1
Stage: prod
Stage throttle: rate=5000 rps, burst=2000
Caching: CloudFront (1.3 GB, TTL 3600s, 60% hit ratio)
Usage plans: 3 tiers (Free: 5rps, Pro: 50rps, Enterprise: 500rps)
Compression: enabled (CloudFront gzip, minimumCompressionSize=1024)

Resources/Methods:
  - GET /config → Lambda proxy (idempotent, cached at CloudFront, 1h TTL)
  - GET /users/{id} → Lambda proxy (idempotent, cached at CloudFront)
  - POST /events → Lambda proxy (NOT cached)

Metrics (last 30 days):
  - Count: 80,000,000/month
  - 4xx: 800,000/month (1%)
  - 5xx: 40,000/month (0.05%)
  - Latency avg: 45 ms, p95: 100 ms
  - IntegrationLatency avg: 30 ms (low because 60% of calls cached)

Cache analysis:
  - CloudFront cache hit ratio: 60%
  - Backend Lambda calls: 32M/month (40% of 80M)
  - Cache cost: $18.98/month (1.3 GB × $0.02 × 730)

Client breakdown:
  - Free tier clients: 20 (5 rps each, 1M/month quota)
  - Pro tier clients: 10 (50 rps each, 10M/month quota)
  - Enterprise clients: 2 (500 rps each, unlimited)

Cost data:
  - API Gateway: $80.00 (80M × $1.00/M HTTP API)
  - CloudFront: $18.98 (cache) + $30.00 (transfer)
  - Data transfer: $216.00 (avg 30 KB compressed × 80M)
  - Total: $344.98/month

Workload context: configuration and user lookup API. Already on
HTTP API (cheapest), CloudFront caching is effective (60% hit
ratio), usage plans prevent noisy neighbors, compression is
enabled. No further optimization expected.
