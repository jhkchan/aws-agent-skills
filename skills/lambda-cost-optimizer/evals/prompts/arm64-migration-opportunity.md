# Eval prompt: arm64-migration-opportunity

Optimise the following Lambda function for cost. Walk the architecture
migration decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

FunctionName: fn-arm64-migration-opportunity
Runtime: python3.12
MemorySize: 2048 MB
Architecture: x86_64
Region: us-east-1
Pricing: on-demand (no provisioned concurrency)

Metrics (last 30 days):
  - Duration avg: 480 ms, p95: 620 ms
  - Invocations: 20,000,000/month
  - Errors: 45 (0.000225%)
  - Memory utilization: avg 680 MB (33% of 2048 MB)

Compute Optimizer finding: Optimized (memory is right-sized)

Power Tuning result:
  - Cheapest (cost-optimal): 2048 MB at 480 ms avg
  - Current memory IS the Power Tuning optimum

Workload context: image processing (resize, format conversion) using
Pillow (PIL). Pillow has aarch64 wheels available on PyPI. No native C
extensions beyond Pillow. No JNI. Pure Python + Pillow only.
