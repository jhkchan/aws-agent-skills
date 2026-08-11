---
description: Optimise Lambda cold-start latency through SnapStart enablement (Java), provisioned concurrency sizing, init phase optimization (lazy initialization, connection pooling), memory tuning (Power Tuning latency mode), runtime selection, deployment package trimming, and VPC cold-start diagnosis.
nl_triggers:
  - "optimise Lambda cold start"
  - "Lambda init duration"
  - "Lambda InitDuration"
  - "Lambda provisioned concurrency"
  - "Lambda SnapStart Java"
  - "Lambda lazy initialization"
  - "Lambda connection reuse"
  - "Lambda VPC cold start"
  - "Lambda hyperplane ENI"
  - "Lambda runtime selection"
  - "Lambda ARM64 Graviton"
  - "Lambda deployment package size"
  - "Lambda Layers cold start"
  - "Lambda Proguard"
  - "Lambda EFS mount latency"
  - "Lambda X-Ray overhead"
  - "Lambda Insights"
  - "Lambda runtime deprecation"
  - "reduce Lambda latency"
  - "Lambda p95 latency"
routes_to: lambda-cold-start-optimizer
---

# /aws:optimize-lambda-cold-start

Activate the `lambda-cold-start-optimizer` skill and optimize a Lambda
function's cold-start latency across seven dimensions: memory allocation,
provisioned concurrency, SnapStart, init phase, VPC cold start, runtime
selection, and deployment package size.

## What it does

Reads a function's CloudWatch metrics (Duration, InitDuration,
Invocations, ColdStarts from Lambda Insights), SnapStart config,
provisioned concurrency configs, VPC config, tracing config, and
package size, then applies the ordered optimization logic:

1. **Pre-flight** — data sufficiency gate. If InitDuration metrics are
   absent (Lambda Insights not enabled), recommends enabling Insights
   first. If the function is dormant, emits OPTIMIZED.
2. **SnapStart (Java only)** — if Runtime = java21+ and SnapStart NOT
   enabled and InitDuration p95 > 1 s, enable SnapStart (eliminates
   90% of init phase via snapshot restore).
3. **Provisioned concurrency** — for sync APIs (API Gateway, ALB) where
   cold-start p95 exceeds SLO and traffic is steady. Sizes to p50-p75
   of ConcurrentExecutions.
4. **Init phase optimization** — move SDK clients, DB connections to
   global scope. Lazy-init pattern with connection validity check.
5. **VPC cold start** — verify hyperplane ENI health. VPC cold start is
   solved since 2019 (<100 ms overhead). Diagnose ENI/subnet/SG if
   latency persists.
6. **Runtime selection** — recommend upgrades for deprecated runtimes.
   Evaluate ARM64 (Graviton) for better price-performance.
7. **Deployment package** — trim fat JARs (Proguard for Java), tree-shake
   deps (Node.js/Python), consolidate Layers.
8. **Memory tuning** — Power Tuning in latency mode (`fastest`) to find
   the memory setting with lowest average duration.
9. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
   recommendation), or OPTIMIZED (all dimensions pass, cold-start p95
   < SLO).

Emits a deterministic optimization block per function:

```text
TARGET: <function-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <memory> MB, <runtime>, <architecture>, <SnapStart>, <PC>, <package>
  Proposed: <memory> MB, <runtime>, <architecture>, <SnapStart>, <PC>, <package>
  Dimensions changed: <memory | provisioned_concurrency | snapstart | init_phase | vpc | runtime | package>
  Confidence: <HIGH/MEDIUM/LOW>
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: <ms>
  Projected cold-start p95: <ms>
  Latency reduction: <ms> (<pct>%)
  SLO: p95 < <ms>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a Lambda function's metrics and ask any of:

- "optimise this Lambda function's cold starts"
- "how do I reduce Lambda init duration?"
- "should I enable SnapStart?"
- "is provisioned concurrency worth it for this function?"
- "why is my VPC Lambda slow on cold starts?"
- "how do I fix Lambda cold-start latency?"
- "Lambda p95 latency is too high"
- "Lambda cold-start fleet optimization review"

A bare function name + any cold-start verb ("fix cold starts", "reduce
init time") also routes here via the orchestrator.

## Inputs

- Function metadata: name, runtime, MemorySize, Architecture, region,
  SnapStart config, VpcConfig, TracingConfig, package size, provisioned
  concurrency config.
- CloudWatch / Lambda Insights metrics (last 14-30 days):
  - `Duration` (Average, p95)
  - `InitDuration` (Average, p95) — cold-start init phase
  - `Invocations` (Sum)
  - `ConcurrentExecutions` (Average, p50, p75, p95, p99)
  - `ColdStarts` (from Lambda Insights)
  - `Errors` (Sum)
- Optional: Power Tuning result (latency mode — `fastest` field).
- Optional: workload context (sync vs async, SLO, runtime, dependencies,
  native libs) for architecture and SnapStart decisions.

## Outputs

- One optimization block per function.
- Confidence level with rationale (HIGH requires Power Tuning + Lambda
  Insights cross-check).
- Estimated latency impact (milliseconds + percentage), broken down by
  InitDuration and Duration.
- Specific migration steps with CLI commands (update-function-configuration,
  publish-version, update-alias, put-provisioned-concurrency-config).
- SLO compliance check (projected p95 vs SLO threshold).
- Versioned alias workflow for safe cutover (never point production at
  `$LATEST`).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for Lambda cold-start latency).
- `/aws:optimize-lambda-cost` for Lambda cost optimization (memory tuning,
  ARM64, provisioned concurrency cost analysis — the cost-focused
  counterpart).
- `/aws:troubleshoot-lambda-invocation` for Lambda functional debugging
  (invocation errors, timeouts, configuration bugs — not latency tuning).
