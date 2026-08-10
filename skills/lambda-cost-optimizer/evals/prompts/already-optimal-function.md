# Eval prompt: already-optimal-function

Optimise the following Lambda function for cost. Walk all optimization
dimensions (memory, concurrency, duration, frequency, architecture,
placement) and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

FunctionName: fn-already-optimal-function
Runtime: nodejs20.x
MemorySize: 512 MB
Architecture: arm64
Region: us-east-1
Pricing: on-demand (no provisioned concurrency)

Metrics (last 30 days):
  - Duration avg: 45 ms, p95: 82 ms
  - Invocations: 10,000,000/month
  - Errors: 3 (0.00003%)
  - Memory utilization: avg 180 MB (35% of 512 MB)

Compute Optimizer finding: Optimized

Power Tuning result:
  - Cheapest (cost-optimal): 512 MB at 45 ms avg
  - Current memory IS the Power Tuning optimum

Workload context: webhook receiver via API Gateway. Simple JSON
validation and S3 put. Already on arm64. On-demand (no provisioned
concurrency). Duration well within 200 ms p95 SLO.
