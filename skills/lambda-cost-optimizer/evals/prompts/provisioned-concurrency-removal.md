# Eval prompt: provisioned-concurrency-removal

Optimise the following Lambda function for cost. Walk the provisioned
concurrency right-sizing decision tree and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

FunctionName: fn-provisioned-concurrency-removal
Runtime: python3.12
MemorySize: 1024 MB
Architecture: x86_64
Region: us-east-1
Pricing: provisioned concurrency (10 concurrent executions)

Metrics (last 30 days):
  - Duration avg: 2400 ms, p95: 2800 ms
  - Invocations: 25,920/month (avg 0.6/min)
  - ConcurrentExecutions: avg 0.4, p50 0, p95 2, p99 3
  - Errors: 0
  - Memory utilization: avg 340 MB (33% of 1024 MB)

Provisioned concurrency config:
  - provisionedConcurrentExecutions: 10
  - allocatedProvisionedConcurrentExecutions: 10

Compute Optimizer finding: NotOptimized (insufficient data for
concurrency recommendation)

Workload context: batch report generator triggered by manual API calls.
Sporadic usage (a few reports per day). Latency is not customer-facing
(internal batch job).
