# Eval prompt: insights-vs-metric-filter

Optimise the following CloudWatch Logs log group for cost. Walk the
Logs Insights vs metric filter decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

LogGroupName: /app/insights-vs-metric-filter
RetentionInDays: 14
Region: us-east-1
StoredBytes: 392 GB

Metrics (last 30 days):
  - IncomingBytes avg: 28 GB/day
  - IncomingLogEvents avg: 8,000,000/day

Logs Insights usage (from CloudTrail StartQuery events):
  - Queries/month: 450
  - Average GB scanned per query: 120 GB
  - Query patterns:
    1. count ERROR messages per minute (200 queries/month)
    2. count TIMEOUT messages per 5 min (100 queries/month)
    3. count Exception by service (80 queries/month)
    4. avg response_time by endpoint (40 queries/month)
    5. count 5xx status codes (30 queries/month)

Cost Explorer (last month):
  - Logs Insights charges: $270.00 (450 × 120 GB × $0.005)
  - Logs ingestion: $420.00
  - Logs storage: $11.76
  - Total: $701.76/month

Workload context: microservice application logs. All 5 query patterns
are simple count/avg aggregations expressible as metric filters. No
complex multi-line queries.
