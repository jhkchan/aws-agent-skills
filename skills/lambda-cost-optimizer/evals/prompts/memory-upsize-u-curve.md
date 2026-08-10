# Eval prompt: memory-upsize-u-curve

Optimise the following Lambda function for cost. Walk the memory-vs-cost
decision framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

FunctionName: fn-memory-upsize-u-curve
Runtime: nodejs20.x
MemorySize: 128 MB
Architecture: x86_64
Region: us-east-1
Pricing: on-demand (no provisioned concurrency)

Metrics (last 30 days):
  - Duration avg: 5200 ms, p95: 6100 ms
  - Invocations: 50,000,000/month
  - Errors: 12,000 (0.024%)
  - Memory utilization: avg 38 MB (30% of 128 MB)

Compute Optimizer finding: Overprovisioned (memory)
Memory recommendation options:
  - rank: 1, memorySize: 1024, projectedUtilization: within bounds
  - rank: 2, memorySize: 2048, projectedUtilization: within bounds

Power Tuning result:
  - Tested: [128, 256, 512, 1024, 2048, 3008]
  - Cheapest (cost-optimal): 1024 MB at 650 ms avg
  - Fastest: 3008 MB at 410 ms avg
  - URL: https://lambda-power-tuning.show/#example

Workload context: image thumbnail generation (CPU-bound). Node.js with
Sharp library. Steady-state 24/7.
