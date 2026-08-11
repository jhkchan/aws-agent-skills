# Eval prompt: memory-tuning-for-cold-start

Optimise the following Lambda function's cold-start latency. Walk the
cold-start decision framework and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_LATENCY_IMPACT,
MIGRATION_STEPS).

FunctionName: fn-memory-tuning-for-cold-start
Runtime: python3.12
MemorySize: 128 MB
Architecture: x86_64
Region: us-east-1
SnapStart: N/A (non-Java runtime)
VpcConfig: none
TracingConfig: Passthrough
Package size: 15 MB
ProvisionedConcurrency: 0
SLO: p95 cold-start < 2000 ms

Metrics (last 30 days):
  - Duration avg: 3200 ms, p95: 4100 ms
  - InitDuration avg: 900 ms, p95: 1200 ms
  - Invocations: 3,000,000/month
  - ColdStarts: ~45,000/month
  - Errors: 0

Power Tuning result (latency mode):
  - Tested: [128, 256, 512, 1024, 2048]
  - Fastest: 1024 MB — InitDuration 300 ms, Duration 800 ms
  - Current (128 MB): InitDuration 900 ms, Duration 3200 ms

Workload context: Python data enrichment pipeline (CPU-bound).
Processes JSON payloads with heavy regex and computation. Init
already at global scope. No VPC.
