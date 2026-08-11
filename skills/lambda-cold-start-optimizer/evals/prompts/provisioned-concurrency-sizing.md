# Eval prompt: provisioned-concurrency-sizing

Optimise the following Lambda function's cold-start latency. Walk the
cold-start decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_LATENCY_IMPACT,
MIGRATION_STEPS).

FunctionName: fn-provisioned-concurrency-sizing
Runtime: nodejs20.x
MemorySize: 1024 MB
Architecture: arm64
Region: us-east-1
SnapStart: N/A (non-Java runtime)
VpcConfig: none
TracingConfig: Passthrough
Package size: 12 MB
ProvisionedConcurrency: 0
SLO: p95 cold-start < 500 ms

Metrics (last 30 days):
  - Duration avg: 120 ms, p95: 180 ms
  - InitDuration avg: 800 ms, p95: 2800 ms
  - Invocations: 20,000,000/month
  - ColdStarts: ~300,000/month (1.5% of invocations)
  - ConcurrentExecutions: avg 15, p50 12, p75 20, p95 35, p99 50
  - Errors: 5

Workload context: Node.js API Gateway endpoint (sync, user-facing).
Steady traffic 24/7. Init already optimized (global-scope clients).
ARM64 already enabled.
