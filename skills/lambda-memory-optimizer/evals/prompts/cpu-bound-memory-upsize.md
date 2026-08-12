# Eval prompt: cpu-bound-memory-upsize

Optimise the following Lambda function's memory configuration. Walk the
memory-vs-cost U-curve decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

FunctionName: fn-cpu-bound-memory-upsize
Runtime: python3.12
MemorySize: 128 MB
Architecture: x86_64
Region: us-east-1
Pricing: on-demand (no provisioned concurrency)

Metrics (last 30 days):
  - Duration avg: 5000 ms, p95: 6200 ms
  - Invocations: 47,000,000/month
  - Errors: 45 (0.000096%)
  - Memory utilization: avg 38 MB (30% of 128 MB)
  - InitDuration: 200 ms (cold start, negligible)

Lambda Insights:
  - memory_used: avg 38 MB, peak 52 MB
  - cpu_total_time: avg 4800 ms (96% of Duration — CPU-bound)

Compute Optimizer finding: Overprovisioned (memory)
Memory recommendation options:
  - rank: 1, memorySize: 512, projectedUtilization: within bounds
  - rank: 2, memorySize: 1024, projectedUtilization: within bounds

Power Tuning result:
  - Tested: [128, 256, 512, 1024, 2048, 3008]
  - Cheapest (cost-optimal): 512 MB at 950 ms avg
  - Fastest: 3008 MB at 410 ms avg
  - URL: https://lambda-power-tuning.show/#example

Workload context: image enrichment (CPU-bound). Python with Pillow
library. Steady-state 24/7 via API Gateway.
