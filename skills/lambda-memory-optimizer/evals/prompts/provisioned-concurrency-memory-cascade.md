# Eval prompt: provisioned-concurrency-memory-cascade

Optimise the following Lambda function's memory configuration. Walk the
memory-vs-cost U-curve AND the provisioned-concurrency memory-cascade
decision framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

FunctionName: fn-provisioned-concurrency-memory-cascade
Runtime: python3.12
MemorySize: 2048 MB
Architecture: x86_64
Region: us-east-1
Pricing: provisioned concurrency (10 concurrent executions)

Metrics (last 30 days):
  - Duration avg: 350 ms, p95: 450 ms
  - Invocations: 50,000,000/month
  - Errors: 12
  - Memory utilization: avg 240 MB (11.7% of 2048 MB)
  - ConcurrentExecutions: avg 6, p50 5, p95 9, p99 10

Lambda Insights:
  - memory_used: avg 240 MB, peak 380 MB
  - cpu_total_time: avg 95 ms (27% of Duration — I/O-bound)

Provisioned concurrency config:
  - provisionedConcurrentExecutions: 10
  - allocatedProvisionedConcurrentExecutions: 10

Compute Optimizer finding: Overprovisioned (memory)
Memory recommendation options:
  - rank: 1, memorySize: 512, projectedUtilization: within bounds

Power Tuning result:
  - Tested: [256, 512, 1024, 2048, 3008]
  - Cheapest (cost-optimal): 512 MB at 360 ms avg
  - Fastest: 512 MB at 360 ms avg (I/O-bound — flat U-curve above 512 MB)
  - URL: https://lambda-power-tuning.show/#example

Workload context: HTTP API handler. I/O-bound (DB query + S3 PUT).
Latency-sensitive (customer-facing). Steady traffic justifies PC.
Peak memory_used 380 MB fits within 512 MB with ~25% headroom.
