# Eval prompt: arm64-power-tuning-retune

Optimise the following Lambda function's memory configuration. The
function was recently migrated from x86_64 to arm64. Walk the ARM64
memory-to-CPU re-tuning framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

FunctionName: fn-arm64-power-tuning-retune
Runtime: python3.12
MemorySize: 1024 MB
Architecture: arm64
Region: us-east-1
Pricing: on-demand (no provisioned concurrency)

Metrics (last 30 days):
  - Duration avg: 420 ms, p95: 550 ms
  - Invocations: 25,000,000/month
  - Errors: 2
  - Memory utilization: avg 180 MB (17.6% of 1024 MB)
  - InitDuration: 220 ms (cold start)

Lambda Insights:
  - memory_used: avg 180 MB, peak 290 MB
  - cpu_total_time: avg 380 ms (90% of Duration — CPU-bound)

Compute Optimizer finding: Optimized (memory was right-sized for x86_64 pre-migration)

Power Tuning result (re-run after ARM64 migration):
  - Tested: [256, 512, 768, 1024, 1769, 2048]
  - Cheapest (cost-optimal): 768 MB at 430 ms avg
  - Fastest: 1769 MB at 380 ms avg
  - URL: https://lambda-power-tuning.show/#example

Workload context: data transformation (CPU-bound). Pure Python + numpy.
Migrated from x86_64 to arm64 last month. Power Tuning was re-run after
migration as required. Peak memory_used 290 MB fits within 768 MB with
~62% headroom.
