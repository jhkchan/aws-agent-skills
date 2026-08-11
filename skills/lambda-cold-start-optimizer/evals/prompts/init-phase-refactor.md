# Eval prompt: init-phase-refactor

Optimise the following Lambda function's cold-start latency. Walk the
cold-start decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_LATENCY_IMPACT,
MIGRATION_STEPS).

FunctionName: fn-init-phase-refactor
Runtime: python3.12
MemorySize: 256 MB
Architecture: x86_64
Region: us-east-1
SnapStart: N/A (non-Java runtime)
VpcConfig: none
TracingConfig: Passthrough
Package size: 8 MB
ProvisionedConcurrency: 0
SLO: p95 steady-state < 500 ms

Metrics (last 30 days):
  - Duration avg: 680 ms, p95: 920 ms
  - InitDuration avg: 350 ms, p95: 500 ms
  - Invocations: 8,000,000/month
  - ColdStarts: ~120,000/month
  - Errors: 2

Code pattern (detected from description):
  - Handler creates boto3 clients per invocation
  - Handler opens psycopg2 DB connection per invocation
  - No global-scope initialization

Workload context: Python microservice behind API Gateway. Uses
RDS PostgreSQL. No connection pooling — each invocation creates
a fresh TLS connection (200-500 ms overhead).
