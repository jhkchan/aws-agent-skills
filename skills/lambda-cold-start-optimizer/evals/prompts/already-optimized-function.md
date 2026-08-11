# Eval prompt: already-optimized-function

Optimise the following Lambda function's cold-start latency. Walk the
cold-start decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_LATENCY_IMPACT,
MIGRATION_STEPS).

FunctionName: fn-already-optimized-function
Runtime: nodejs20.x
MemorySize: 512 MB
Architecture: arm64
Region: us-east-1
SnapStart: N/A (non-Java runtime)
VpcConfig: none
TracingConfig: Passthrough
Package size: 4 MB
ProvisionedConcurrency: 0
SLO: p95 cold-start < 1000 ms

Metrics (last 30 days):
  - Duration avg: 45 ms, p95: 82 ms
  - InitDuration avg: 180 ms, p95: 250 ms
  - Invocations: 10,000,000/month
  - ColdStarts: ~150,000/month
  - Errors: 0

Power Tuning result:
  - Fastest: 512 MB at 45 ms avg (current IS the optimum)
  - Cheapest: 512 MB at 45 ms avg

Workload context: Webhook receiver. All SDK clients at global
scope. ARM64 enabled. No VPC. Package slim (4 MB). Cold-start
p95 (250 ms + 82 ms = 332 ms) well within 1000 ms SLO.
