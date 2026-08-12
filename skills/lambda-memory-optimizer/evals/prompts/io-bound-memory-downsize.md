# Eval prompt: io-bound-memory-downsize

Optimise the following Lambda function's memory configuration. Walk the
memory-vs-cost U-curve decision framework and emit the standard
optimization block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_SAVINGS, MIGRATION_STEPS).

FunctionName: fn-io-bound-memory-downsize
Runtime: nodejs20.x
MemorySize: 2048 MB
Architecture: x86_64
Region: us-east-1
Pricing: on-demand (no provisioned concurrency)

Metrics (last 30 days):
  - Duration avg: 80 ms, p95: 120 ms
  - Invocations: 30,000,000/month
  - Errors: 0
  - Memory utilization: avg 75 MB (3.7% of 2048 MB)
  - InitDuration: 450 ms (cold start)

Lambda Insights:
  - memory_used: avg 75 MB, peak 95 MB
  - cpu_total_time: avg 12 ms (15% of Duration — I/O-bound)

Compute Optimizer finding: Overprovisioned (memory)
Memory recommendation options:
  - rank: 1, memorySize: 256, projectedUtilization: within bounds

Power Tuning result:
  - Tested: [128, 256, 512, 1024, 2048]
  - Cheapest (cost-optimal): 256 MB at 85 ms avg
  - Fastest: 256 MB at 85 ms avg (I/O-bound — flat U-curve)
  - URL: https://lambda-power-tuning.show/#example

Workload context: HTTP proxy to downstream REST API. Waits on network
I/O for 85% of duration. No CPU-intensive work. Node.js 20.x with
axios. Steady-state 24/7 via API Gateway.
