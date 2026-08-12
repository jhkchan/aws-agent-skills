---
description: Optimise Lambda memory configuration through Power Tuning (U-curve cost-vs-latency analysis), provisioned concurrency memory right-sizing (PC idle bill scales with memory), init-phase memory (SnapStart, lazy init), EFS/container-image/Layers overhead accounting, /tmp storage decoupling, and ARM64 Graviton2 memory-to-CPU ratio re-tuning — with monthly savings estimates.
nl_triggers:
  - "optimise Lambda memory"
  - "Lambda memory tuning"
  - "Lambda Power Tuning"
  - "Lambda cost-optimal memory"
  - "Lambda latency-optimal memory"
  - "Lambda U-curve"
  - "Lambda memory CPU-bound"
  - "Lambda memory I/O-bound"
  - "Lambda memory Pareto frontier"
  - "Lambda memory Compute Optimizer"
  - "Lambda provisioned concurrency memory"
  - "Lambda ARM64 Graviton2 memory"
  - "Lambda SnapStart init memory"
  - "Lambda EFS memory overhead"
  - "Lambda container image memory"
  - "Lambda Layers memory"
  - "Lambda /tmp storage allocation"
  - "Lambda memory FinOps"
  - "Lambda memory-to-CPU ratio"
  - "Lambda memory right-sizing"
routes_to: lambda-memory-optimizer
---

# /aws:optimize-lambda-memory

Activate the `lambda-memory-optimizer` skill and optimize a Lambda
function's memory configuration across six dimensions: memory size (U-
curve), provisioned concurrency memory footprint, init-phase memory,
EFS/container/Layers overhead, /tmp storage, and ARM64 memory-to-CPU
ratio.

## What it does

Reads a function's CloudWatch metrics (Duration, Invocations,
memory_used via Lambda Insights, InitDuration, cpu_total_time), Compute
Optimizer Lambda findings, Power Tuning results, provisioned
concurrency configs, and deployment configuration (EFS, container
image, Layers, /tmp), then applies the ordered optimization logic:

1. **Pre-flight** — data sufficiency gate. If Duration/Invocations
   metrics are absent, emits NEED_MORE_INFO. If the function is dormant
   (0 invocations), emits OPTIMIZED.
2. **Memory size (U-curve)** — use AWS Lambda Power Tuning to
   empirically find the cost-optimal AND latency-optimal memory setting.
   The cost minimum may be HIGHER (CPU-bound) or LOWER (I/O-bound) than
   current.
3. **Provisioned concurrency memory cascade** — PC bills per GB-second
   of provisioned capacity. Memory right-sizing cascades into PC idle
   savings without changing PC count.
4. **Init-phase memory** — SnapStart for Java (eliminates cold-start
   init), lazy initialization, connection reuse, package size reduction.
5. **EFS / container / Layers overhead** — account for resident memory
   add-ons; recommend removal where unnecessary; ensure minimum viable
   MemorySize for container-image functions (256 MB).
6. **/tmp storage decoupling** — decouple /tmp from MemorySize via
   `--ephemeral-storage` (up to 10 GB, bills separately).
7. **ARM64 re-tuning** — after architecture migration, re-run Power
   Tuning; the U-curve minimum shifts on Graviton2.
8. **Impact estimation** — monthly + annual savings, latency delta,
   assumptions documented.
9. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
   recommendation), OPTIMIZED (applied and verified this session, or
   all dimensions pass), or NEED_MORE_INFO.

Emits a deterministic optimization block per function:

```text
TARGET: <function-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <memory> MB at <avg duration> ms, <architecture>, <concurrency>, <init>
  Proposed: <memory> MB at <projected duration> ms, <architecture>, <concurrency>, <init>
  Dimensions changed: <memory | pc_memory | init | efs_container_layers | tmp | architecture>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Latency delta: <p95 duration change> ms (<percentage>%)
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a Lambda function's metrics and ask any of:

- "optimise this Lambda function's memory"
- "should I increase Lambda memory?"
- "is the current Lambda memory setting cost-optimal?"
- "Lambda Power Tuning sweep"
- "should I migrate this Lambda to ARM64?"
- "is provisioned concurrency memory oversized?"
- "should I decouple /tmp from Lambda memory?"
- "Lambda memory fleet review"

A bare function name + any memory verb ("right-size memory", "memory
tuning") also routes here via the orchestrator.

## Inputs

- Function metadata: name, runtime, MemorySize, Architecture, region,
  pricing model (on-demand / provisioned concurrency).
- CloudWatch metrics (last 14-30 days):
  - `Duration` (Average, p95, Maximum)
  - `Invocations` (Sum)
  - `InitDuration` (cold-start component)
  - `ConcurrentExecutions` (Average, p50, p95, p99)
- Lambda Insights metrics:
  - `memory_used` (Average, Maximum — runtime memory headroom)
  - `cpu_total_time` (Average — CPU-bound vs I/O-bound classification)
- Optional: Compute Optimizer Lambda finding document.
- Optional: Power Tuning result (tested memory values, cheapest,
  fastest, visualization URL).
- Optional: Provisioned Concurrency config.
- Optional: deployment configuration (EFS mount, container image size,
  Layers count, /tmp allocation).
- Optional: workload context (runtime, dependencies, latency SLO).

## Outputs

- One optimization block per function.
- Confidence level with rationale (HIGH requires Power Tuning +
  Compute Optimizer cross-check + Lambda Insights headroom verification).
- Estimated monthly and annual savings, broken down by dimension.
- Cost-vs-latency tradeoff surfaced (cheapest vs fastest memory).
- Specific migration steps with CLI commands (update-function-
  configuration, publish-version, update-alias, update-event-source-
  mapping).
- Latency impact surfaced alongside cost (a memory change may be cost-
  neutral but latency-improving).
- Versioned alias workflow for safe cutover (never point production at
  $LATEST).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for Lambda memory configuration).
- `/aws:optimize-lambda-cost` for full Lambda cost optimization across
  all dimensions (memory, concurrency, duration, frequency,
  architecture, placement). This skill is the memory-focused subset.
- `/aws:troubleshoot-lambda-invocation` for Lambda functional debugging
  (invocation errors, timeouts, configuration bugs — not memory cost
  optimization).
