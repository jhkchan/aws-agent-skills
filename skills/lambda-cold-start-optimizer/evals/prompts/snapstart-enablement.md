# Eval prompt: snapstart-enablement

Optimise the following Lambda function's cold-start latency. Walk the
cold-start decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_LATENCY_IMPACT,
MIGRATION_STEPS).

FunctionName: fn-snapstart-enablement
Runtime: java21
MemorySize: 512 MB
Architecture: x86_64
Region: us-east-1
SnapStart: NOT_ENABLED
VpcConfig: none
TracingConfig: Passthrough
Package size: 48 MB (fat JAR)
ProvisionedConcurrency: 0
SLO: p95 cold-start < 1000 ms

Metrics (last 30 days):
  - Duration avg: 1800 ms, p95: 2400 ms
  - InitDuration avg: 3100 ms (cold start), p95: 3200 ms
  - Invocations: 5,000,000/month
  - ColdStarts: ~75,000/month (1.5% of invocations)
  - Errors: 0

Workload context: Java 21 Spring Boot REST API behind API Gateway
(sync, user-facing). Uses standard Corretto distribution. No
container-image. DB connections initialized in global scope.
