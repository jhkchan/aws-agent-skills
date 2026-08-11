# Worked Examples

Full worked examples for the Lambda Cold Start Optimizer skill. Each
example demonstrates a distinct optimization pattern with verified
latency math, CLI commands, and rationale.

## Example 1: SnapStart enablement (Java)

```text
TARGET: order-api-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Java 21 function with InitDuration p95 of 3200 ms and SnapStart
  NOT enabled. Enabling SnapStart eliminates 90% of init phase (snapshot
  restore drops InitDuration from 3200 ms to ~200 ms). Sync API with
  cold-start p95 exceeding the 1000 ms SLO.
RECOMMENDATION:
  Current: 512 MB, java21, x86_64, SnapStart OFF, no PC, 48 MB
  Proposed: 512 MB, java21, x86_64, SnapStart ON, no PC, 48 MB
  Dimensions changed: snapstart (Step 3)
  Dimensions checked: memory ✓  provisioned_concurrency ✓  snapstart → (enable)
    init_phase ✓  vpc ✓  runtime ✓  package ✓
  Confidence: HIGH — SnapStart supported on java21; Corretto; no container-image.
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: 5000 ms (InitDuration: 3200 ms + Duration: 1800 ms)
  Projected cold-start p95: 2000 ms (InitDuration: 200 ms + Duration: 1800 ms)
  Latency reduction: 3000 ms (60%)
  SLO: p95 < 1000 ms — pair with provisioned concurrency for full SLO.
MIGRATION_STEPS:
  1. Enable SnapStart:
     aws lambda update-function-configuration --function-name order-api-prod
       --snap-start '{"ApplyOn":"PublishedVersions"}'
  2. Publish a version: aws lambda publish-version --function-name order-api-prod
  3. Update alias: aws lambda update-alias --function-name order-api-prod
       --name prod --function-version <new-version>
  4. Verify: aws lambda get-function-configuration --function-name order-api-prod
       --qualifier <new-version> --query 'SnapStart.OptimizationStatus'
  5. Monitor InitDuration for 7 days. If SLO unmet, add provisioned concurrency.
CONFIRM: About to enable SnapStart on order-api-prod (publish version,
  update alias). Projected cold-start reduction: 3000 ms (60%). Proceed?
```

## Example 2: Provisioned concurrency sizing (sync API)

```text
TARGET: payment-gateway-api
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Node.js sync API with cold-start p95 of 2800 ms exceeding the
  500 ms SLO. No provisioned concurrency configured. Steady traffic
  (ConcurrentExecutions p50=12, p75=20). All other dimensions pass.
RECOMMENDATION:
  Current: 1024 MB, nodejs20.x, arm64, SnapStart N/A, no PC, 12 MB
  Proposed: 1024 MB, nodejs20.x, arm64, SnapStart N/A, PC=15, 12 MB
  Dimensions changed: provisioned_concurrency (Step 2)
  Dimensions checked: memory ✓  provisioned_concurrency → (add)
    snapstart N/A  init_phase ✓  vpc ✓  runtime ✓  package ✓
  Confidence: HIGH — sync API with steady traffic justifies PC.
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: 2980 ms (InitDuration: 2800 ms + Duration: 180 ms)
  Projected cold-start p95: 180 ms (no InitDuration with PC)
  Latency reduction: 2800 ms (94%)
  SLO: p95 < 500 ms — projected p95 meets SLO.
MIGRATION_STEPS:
  1. Publish a version: aws lambda publish-version --function-name payment-gateway-api
  2. Create/update alias: aws lambda update-alias --function-name payment-gateway-api
       --name prod --function-version <new-version>
  3. Add provisioned concurrency (sized to p75):
     aws lambda put-provisioned-concurrency-config --function-name payment-gateway-api
       --qualifier prod --provisioned-concurrent-executions 15
  4. Optionally set up autoscaling:
     aws application-autoscaling register-scalable-target
       --service-namespace lambda
       --resource-id function:payment-gateway-api:prod
       --scalable-dimension lambda:function:ProvisionedConcurrency
       --min-capacity 10 --max-capacity 30
  5. Monitor cold-start count for 7 days.
CONFIRM: About to add provisioned concurrency (15) to payment-gateway-api
  prod alias. Projected cold-start elimination: 94%. Proceed?
```

## Example 3: Init phase refactor (Python)

```text
TARGET: data-enrichment-service
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Python function creates boto3 clients and psycopg2 DB
  connections inside the handler per invocation, adding 200-500 ms TLS
  overhead. Moving to global scope eliminates per-invocation connection
  setup.
RECOMMENDATION:
  Current: 256 MB, python3.12, x86_64, SnapStart N/A, no PC, 8 MB
  Proposed: 256 MB, python3.12, x86_64, SnapStart N/A, no PC, 8 MB
  Dimensions changed: init_phase (Step 4)
  Dimensions checked: memory ✓  provisioned_concurrency ✓
    snapstart N/A  init_phase → (refactor)  vpc ✓  runtime ✓  package ✓
  Confidence: HIGH — code pattern confirmed (per-invocation init).
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: 1420 ms (InitDuration: 500 ms + Duration: 920 ms)
  Projected cold-start p95: 720 ms (InitDuration: 500 ms + Duration: 220 ms)
  Latency reduction: 700 ms (49%) — steady-state Duration improvement
  SLO: p95 < 500 ms — partially met; Duration drops below SLO after warm-up.
MIGRATION_STEPS:
  1. Refactor handler: move boto3 clients and DB connections to global scope.
  2. Add lazy-init pattern for DB connection with validity check:
     if _db is None or _db.closed: _db = psycopg2.connect(...)
  3. Deploy refactored code: aws lambda update-function-code ...
  4. Monitor Duration for 7 days. Expect avg to drop from 680 ms to ~200 ms.
CONFIRM: About to refactor init phase on data-enrichment-service (code
  deploy required). Projected steady-state Duration reduction: 700 ms.
  Proceed?
```

## Example 4: Already-optimized function

```text
TARGET: webhook-receiver-prod
VERDICT: OPTIMIZED
REASON: Node.js function at Power Tuning latency optimum (512 MB),
  ARM64 enabled, all SDK clients at global scope, no VPC, package slim
  (4 MB). Cold-start p95 of 332 ms well within 1000 ms SLO. Non-Java
  so SnapStart not applicable. No remaining optimization levers.
RECOMMENDATION:
  Current: 512 MB, nodejs20.x, arm64, SnapStart N/A, no PC, 4 MB
  Proposed: (no changes — all dimensions pass)
  Dimensions checked: memory ✓  provisioned_concurrency ✓
    snapstart N/A  init_phase ✓  vpc ✓  runtime ✓  package ✓
  Confidence: HIGH — all seven dimensions verified.
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: 332 ms (InitDuration: 250 ms + Duration: 82 ms)
  Projected cold-start p95: 332 ms (no changes)
  Latency reduction: 0 ms (0%)
  SLO: p95 < 1000 ms — met with 668 ms headroom.
MIGRATION_STEPS:
  (none — continue monitoring)
CONFIRM: (n/a)
```

## Example 5: Memory tuning for cold start

```text
TARGET: data-pipeline-worker
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Python function at 128 MB is CPU-bound (heavy regex and
  computation). Power Tuning shows that increasing to 1024 MB reduces
  InitDuration from 900 ms to 300 ms and Duration from 3200 ms to 800 ms
  (more vCPU at higher memory). Cold-start p95 exceeds 2000 ms SLO.
RECOMMENDATION:
  Current: 128 MB, python3.12, x86_64, SnapStart N/A, no PC, 15 MB
  Proposed: 1024 MB, python3.12, x86_64, SnapStart N/A, no PC, 15 MB
  Dimensions changed: memory (Step 1)
  Dimensions checked: memory → (upsize)  provisioned_concurrency ✓
    snapstart N/A  init_phase ✓  vpc ✓  runtime ✓  package ✓
  Confidence: HIGH — Power Tuning measured latency improvement empirically.
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: 5300 ms (InitDuration: 1200 ms + Duration: 4100 ms)
  Projected cold-start p95: 1100 ms (InitDuration: 300 ms + Duration: 800 ms)
  Latency reduction: 4200 ms (79%)
  SLO: p95 < 2000 ms — projected p95 meets SLO.
MIGRATION_STEPS:
  1. Update memory:
     aws lambda update-function-configuration --function-name data-pipeline-worker
       --memory-size 1024
  2. Publish a version: aws lambda publish-version --function-name data-pipeline-worker
  3. Monitor Duration + InitDuration for 7 days.
CONFIRM: About to update memory on data-pipeline-worker (128 MB → 1024
  MB). Projected cold-start reduction: 4200 ms (79%). Per-invocation
  cost increases. Proceed?
```

## Example 6: NEED_MORE_INFO

```text
TARGET: mystery-function-prod
VERDICT: NEED_MORE_INFO
REASON: Lambda Insights not enabled — InitDuration metric is absent.
  Cannot assess cold-start latency without init-phase telemetry.
  Observation window (7 days) is below the 14-day minimum.
RECOMMENDATION:
  Current: insufficient data
  Dimensions checked: (cannot evaluate — data gate failed)
  Confidence: LOW — no telemetry.
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: unknown
  Projected cold-start p95: unknown
  Latency reduction: unknown
  SLO: unknown
MIGRATION_STEPS:
  1. Enable Lambda Insights Layer:
     aws lambda update-function-configuration --function-name mystery-function-prod
       --layers arn:aws:lambda:us-east-1:580247275435:layer:LambdaInsightsExtension:<version>
  2. Collect 14-30 days of InitDuration metrics.
  3. Re-run cold-start optimization analysis.
CONFIRM: (n/a — read-only recommendation)
```
