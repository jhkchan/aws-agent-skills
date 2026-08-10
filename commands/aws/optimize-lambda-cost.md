---
description: Optimise Lambda function cost through memory tuning (Power Tuning U-curve), provisioned concurrency right-sizing, duration reduction (SnapStart, lazy init), invocation-frequency analysis (ESM batch tuning), and architecture migration (ARM64 Graviton2, Fargate, Step Functions) with monthly savings estimates.
nl_triggers:
  - "optimise Lambda cost"
  - "Lambda memory tuning"
  - "Lambda Power Tuning"
  - "Lambda Compute Optimizer recommendations"
  - "Lambda provisioned concurrency"
  - "Lambda duration optimization"
  - "Lambda cold start"
  - "Lambda SnapStart Java"
  - "Lambda batch size SQS"
  - "Lambda ARM64 Graviton2"
  - "Lambda Layers shared code"
  - "Lambda invocation frequency"
  - "Lambda FinOps savings"
  - "Lambda to Fargate migration"
  - "Lambda monthly savings estimate"
  - "reduce Lambda bill"
  - "serverless cost review"
  - "Lambda function too slow"
routes_to: lambda-cost-optimizer
---

# /aws:optimize-lambda-cost

Activate the `lambda-cost-optimizer` skill and optimize a Lambda function's
cost configuration across six dimensions: memory, concurrency, duration,
invocation frequency, architecture, and workload placement.

## What it does

Reads a function's CloudWatch metrics (Duration, Invocations,
ConcurrentExecutions, Errors), Compute Optimizer Lambda findings, Power
Tuning results, event source mapping configs, and provisioned concurrency
configs, then applies the ordered optimization logic:

1. **Pre-flight** — data sufficiency gate. If Duration/Invocations metrics
   are absent, emits NEED_MORE_INFO. If the function is dormant (0
   invocations), emits ALREADY_OPTIMAL.
2. **Memory tuning** — use AWS Lambda Power Tuning to empirically find the
   U-curve cost-optimal memory setting. The optimal memory may be HIGHER
   than current (CPU-bound workloads) or LOWER (I/O-bound workloads).
3. **Provisioned concurrency right-sizing** — break-even math for on-demand
   vs provisioned. Remove provisioned concurrency for sporadic traffic;
   size to p75-p90 for steady latency-sensitive APIs.
4. **Duration optimization** — SnapStart for Java (eliminates cold-start
   init), lazy initialization, connection reuse, package size reduction.
5. **Invocation frequency analysis** — SQS/Kinesis/DynamoDB Streams batch
   size and batch window tuning to reduce invocation count.
6. **Architecture migration** — ARM64 (Graviton2) is ~20% cheaper for
   supported runtimes. Fargate for >15-minute workloads. Step Functions
   for orchestration-heavy chains.
7. **Impact estimation** — monthly + annual savings, assumptions documented.
8. **Verdict** — OPPORTUNITY_FOUND (any dimension has a recommendation),
   OPTIMIZED (applied and verified this session), or ALREADY_OPTIMAL.

Emits a deterministic optimization block per function:

```text
TARGET: <function-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <memory> MB at <avg duration> ms, <architecture>, <concurrency>
  Proposed: <memory> MB at <projected duration> ms, <architecture>, <concurrency>
  Dimensions changed: <memory | concurrency | duration | frequency | architecture>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a Lambda function's metrics and ask any of:

- "optimise this Lambda function's cost"
- "should I increase Lambda memory?"
- "is provisioned concurrency worth it for this function?"
- "should I migrate this Lambda to ARM64?"
- "how do I reduce Lambda cold starts?"
- "is this Compute Optimizer Lambda finding actionable?"
- "should I increase SQS batch size for this consumer?"
- "Lambda fleet cost optimization review"

A bare function name + any optimization verb ("optimize this function",
"cost review") also routes here via the orchestrator.

## Inputs

- Function metadata: name, runtime, MemorySize, Architecture, region,
  pricing model (on-demand / provisioned concurrency).
- CloudWatch metrics (last 14-30 days):
  - `Duration` (Average, p95, Maximum)
  - `Invocations` (Sum)
  - `ConcurrentExecutions` (Average, p50, p95, p99)
  - `Errors` (Sum)
  - `InitDuration` (cold-start component, requires Lambda Insights)
  - `memory_used` (Lambda Insights — memory-utilization headroom)
- Optional: Compute Optimizer Lambda finding document (finding,
  findingReasonCodes, memoryRecommendationOptions).
- Optional: Power Tuning result (tested memory values, cheapest, fastest,
  visualization URL).
- Optional: Event Source Mapping config (EventSourceArn, BatchSize,
  MaximumBatchingWindowInSeconds, FunctionResponseTypes).
- Optional: Provisioned Concurrency config (provisionedConcurrentExecutions).
- Optional: workload context (runtime, dependencies, native libs, latency
  SLO) for ARM64 compatibility and placement decisions.

## Outputs

- One optimization block per function.
- Confidence level with rationale (HIGH requires Power Tuning + Compute
  Optimizer cross-check + clear thresholds).
- Estimated monthly and annual savings, broken down by dimension.
- Specific migration steps with CLI commands (update-function-configuration,
  publish-version, update-alias, delete-provisioned-concurrency-config,
  update-event-source-mapping).
- Latency impact surfaced alongside cost (a memory upsize may be cost-
  neutral but latency-improving).
- Versioned alias workflow for safe cutover (never point production at
  $LATEST).

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for Lambda serverless cost).
- `/aws:optimize-ec2-rightsizing` for EC2 instance rightsizing (the
  compute counterpart for non-serverless workloads).
- `/aws:troubleshoot-lambda-invocation` for Lambda functional debugging
  (invocation errors, timeouts, configuration bugs — not cost optimization).
