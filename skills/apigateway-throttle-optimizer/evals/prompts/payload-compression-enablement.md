# Eval prompt: payload-compression-enablement

Optimise the following API Gateway for throttle and cost. Walk the
payload/caching/throttle decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

ApiName: api-payload-compression-enablement
ApiType: REST (REGIONAL)
Region: us-east-1
Stage: prod
Stage throttle: rate=3000 rps, burst=1500
Caching: disabled
Usage plans: 1 usage plan (single client)
Compression: disabled (minimumCompressionSize not set)

Resources/Methods:
  - GET /reports/full → Lambda proxy (returns full report JSON, avg 250 KB)
  - GET /reports/summary → Lambda proxy (returns summary JSON, avg 50 KB)
  - GET /exports/{id} → Lambda proxy (returns export data, avg 180 KB)

Metrics (last 30 days):
  - Count: 50,000,000/month
  - 4xx: 500,000/month (1%)
  - 5xx: 25,000/month (0.05%)
  - Latency avg: 200 ms, p95: 400 ms
  - IntegrationLatency avg: 150 ms

Payload analysis:
  - Avg response size: 180 KB
  - GET /reports/full: 20M req/month × 250 KB avg
  - GET /reports/summary: 10M req/month × 50 KB avg
  - GET /exports/{id}: 20M req/month × 180 KB avg
  - Total data transfer: ~8.79 TB/month outbound

Cost data:
  - API Gateway: $175.00 (50M × $3.50/M)
  - Data transfer out: $791.10 (8,790 GB × $0.09/GB)
  - Total: $966.10/month

Workload context: reporting API serving large JSON exports.
Responses include many nested fields. Clients typically only use
30% of returned fields. Lambda proxy integration with no mapping
templates.
