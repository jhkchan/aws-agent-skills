---
name: lambda-cold-start-optimizer
description: 'Optimises AWS Lambda cold-start latency across seven dimensions: memory allocation vs initialization time (Power Tuning latency-optimal memory), provisioned concurrency (allocation sizing and autoscaling for latency-critical paths), SnapStart (Java only — init snapshot eliminates 1-3 s of init), init phase optimization (lazy initialization, global-scope connection pooling), VPC cold start penalty (hyperplane ENI elimination since 2019), runtime selection (compiled vs interpreted, ARM64 Graviton), and deployment package size reduction (Layers, Proguarded JARs, slim ZIPs). Covers EFS mount latency, runtime deprecation impact, X-Ray overhead, and CloudWatch Lambda Insights init-duration telemetry. Emits OPTIMIZED when cold-start p95 < SLO and all init-phase levers applied, or FURTHER_OPTIMIZATION_AVAILABLE with the highest-leverage remaining lever.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted CloudWatch metrics and Lambda Insights traces. Live-account optimization uses aws lambda list-functions, aws lambda get-function-configuration, aws lambda get-function-event-invoke-config, aws lambda list-provisioned-concurrency-configs, aws lambda get-event-source-mapping, aws cloudwatch get-metric-statistics (Duration, InitDuration, Invocations...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Reducing Lambda cold-start latency, sizing provisioned concurrency for latency-sensitive APIs, enabling SnapStart for Java functions, optimizing the init phase (lazy initialization, connection reuse), evaluating VPC cold-start impact, selecting a runtime for fast startup, trimming deployment package size, diagnosing EFS mount latency, assessing X-Ray tracing overhead, or reading Lambda Insights init-duration telemetry.
  when_not_to_use: Lambda cost optimization without a latency focus (use lambda-cost-optimizer), Lambda functional debugging (invocation errors, timeouts, configuration bugs — use the Lambda troubleshooter), or API Gateway latency optimization (use the API Gateway optimizer). This skill targets cold-start and init-phase latency, not dollar cost or functional correctness.
  activation_triggers: optimise Lambda cold start, Lambda init duration, Lambda InitDuration, Lambda provisioned concurrency, Lambda SnapStart Java, Lambda lazy initialization, Lambda connection reuse, Lambda VPC cold start, Lambda hyperplane ENI, Lambda runtime selection, Lambda ARM64 Graviton, Lambda deployment package size, Lambda Layers cold start, Lambda Proguard, Lambda EFS mount latency, Lambda X-Ray overhead, Lambda Insights, Lambda runtime deprecation, reduce Lambda latency, Lambda p95 latency
  invocation_schema: 'Input: either (a) a function identifier + live-account context, (b) a Lambda Insights metrics export (Duration, InitDuration, Invocations, ColdStarts), OR (c) function metadata (Runtime, MemorySize, Architecture, VpcConfig, SnapStart config, ProvisionedConcurrency config, TracingConfig, package size). Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_LATENCY_IMPACT/MIGRATION_STEPS block per function, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline classification):\nFunctionName: order-api-prod\nRuntime: java21\nMemorySize: 512 MB\nArchitecture: x86_64\nRegion: us-east-1\nSnapStart: NOT_ENABLED\nVpcConfig: subnet-aaa, subnet-bbb (VPC attached)\nTracingConfig: Active\nPackage size: 52 MB (fat JAR, untrimmed)\nProvisionedConcurrency: 0\nMetrics (last 30 days):\n  - Duration avg: 1800 ms, p95: 2400 ms\n  - InitDuration avg: 3200 ms (cold start), p95: 4100 ms\n  - Invocations: 8,000,000/month\n  - ColdStarts: ~120,000/month (1.5% of invocations)\n  - Errors: 0\nSLO: p95 end-to-end < 1000 ms\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_LATENCY_IMPACT, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Lambda, cold start, initialization time, InitDuration, provisioned concurrency, SnapStart, Java, power tuning, memory allocation, lazy initialization, connection pooling, VPC, hyperplane ENI, runtime selection, ARM64, Graviton, deployment package, Lambda Layers, Proguard, EFS mount, X-Ray overhead, Lambda Insights, runtime deprecation, latency optimization
  tags: lambda, compute, serverless, performance, cold-start, latency, snapstart, provisioned-concurrency
---

# Lambda Cold Start Optimizer

## What this skill does

Translates a Lambda function's cold-start posture into a concrete
latency-optimization recommendation with a millisecond-denominated
estimated latency impact. The verdict is the highest-leverage action
across seven dimensions — memory allocation, provisioned concurrency,
SnapStart, init phase optimization, VPC cold start, runtime selection,
and deployment package size — applied in priority order. Always pairs
the recommendation with exact CLI commands (or Power Tuning invocation).

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cold-start formula | First read |
| Mindset | Why SnapStart + provisioned concurrency are the heavy levers | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a function |
| Pre-flight data gate | CloudWatch metrics, Lambda Insights | Before any recommendation |
| Step 0 non-obvious behaviours | VPC hyperplane ENI, SnapStart Java-only, X-Ray overhead | Edge cases |
| Step 1 Memory allocation | Power Tuning for latency-optimal memory | The CPU-bound dimension |
| Step 2 Provisioned concurrency | Allocation, scheduling, autoscaling | Latency-sensitive APIs |
| Step 3 SnapStart (Java) | Init snapshot, versioned alias requirement | Java functions |
| Step 4 Init phase optimization | Lazy init, connection pooling, global scope | All runtimes |
| Step 5 VPC cold start | Hyperplane ENI elimination, when VPC still hurts | VPC-attached functions |
| Step 6 Runtime selection | Compiled vs interpreted, ARM64 Graviton | Architecture decisions |
| Step 7 Package size | Layers, Proguarded JARs, slim ZIPs | Large deployment packages |
| Step 8 Impact estimation | Latency math and worked examples | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, version publish, alias | Before any apply CLI |

## Quick start

- **SnapStart is the heaviest single lever for Java.** It eliminates
  the entire init phase (1-3 s for typical Spring/Java workloads) by
  restoring a pre-initialized snapshot. One-line config change, no code
  modification for most workloads. Available ONLY for Java (java21 and
  later supported runtimes).
- **Provisioned concurrency eliminates cold starts entirely — at a
  price.** It pre-initializes execution environments and keeps them
  warm. Use it ONLY for latency-critical paths (sync APIs, interactive
  endpoints) where a cold start violates the SLO. It charges for idle
  time; the cost-vs-latency trade-off must be explicit.
- **VPC cold start is largely solved (since 2019).** Hyperplane ENIs
  eliminated the 5-10 s VPC cold-start penalty. VPC-attached functions
  now see <100 ms overhead on cold starts. If a function still shows
  high VPC cold-start latency, check for ENI throttling or stale
  configuration, not the VPC itself.
- **The init phase is where most cold-start time lives.** Move SDK
  clients, DB connections, and heavy imports to global scope (outside
  the handler). Lambda reuses execution environments across invocations;
  global-scope init runs once per warm container, not per invocation.

## Mindset

Cold-start optimization is a latency-vs-cost decision, not a pure
utilization exercise. The goal is the memory/concurrency/runtime/package
configuration that minimizes cold-start InitDuration AND steady-state
Duration while preserving the cost envelope — not the absolute minimum
init time at any cost.

Five-principle deep dive moved to `references/advanced-patterns.md` —
see "Mindset — five principles".

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Runtime = Java AND SnapStart NOT enabled AND InitDuration p95 > 1 s | **FURTHER_OPTIMIZATION_AVAILABLE** (SnapStart) | Step 3 — enable SnapStart, publish version |
| Latency-sensitive API (sync) AND cold-start p95 > SLO AND no provisioned concurrency | **FURTHER_OPTIMIZATION_AVAILABLE** (provisioned concurrency) | Step 2 — add provisioned concurrency sized to baseline |
| Memory < 1769 MB AND Duration scales with memory (CPU-bound) AND InitDuration > 500 ms | **FURTHER_OPTIMIZATION_AVAILABLE** (memory) | Step 1 — increase memory to Power Tuning latency optimum |
| SDK clients / DB connections initialized inside handler (per-invocation) | **FURTHER_OPTIMIZATION_AVAILABLE** (init phase) | Step 4 — move to global scope |
| Package size > 20 MB AND runtime = Java AND no Proguard/SnapStart | **FURTHER_OPTIMIZATION_AVAILABLE** (package) | Step 7 — trim fat JAR, enable Proguard |
| Architecture = x86_64 AND runtime is ARM-compatible AND latency-sensitive | **FURTHER_OPTIMIZATION_AVAILABLE** (architecture) | Step 6 — migrate to arm64 for better price-performance |
| Runtime is deprecated (e.g., nodejs16, java8) AND function is latency-sensitive | **FURTHER_OPTIMIZATION_AVAILABLE** (runtime) | Step 6 — upgrade to current runtime |
| TracingConfig = Active AND X-Ray overhead > 50 ms per invocation | **FURTHER_OPTIMIZATION_AVAILABLE** (tracing) | Step 0 — evaluate sampling rate |
| All dimensions verified AND cold-start p95 < SLO AND SnapStart enabled (Java) | **OPTIMIZED** | Emit post-state verification |
| InitDuration metrics absent (Lambda Insights not enabled) | **FURTHER_OPTIMIZATION_AVAILABLE** (observability) | Enable Lambda Insights for init-duration visibility |
| Observation window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Required data-source CLI listing moved to `references/diagnostic-commands.md`.
Full sequences: `references/cold-start-metrics-and-power-tuning.md`.

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `InitDuration` absent (Lambda Insights not enabled) | Enable Lambda Insights. Fall back to `Duration` spikes; mark confidence MEDIUM. |
| `Invocations` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "dormant function." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| Cold-start count absent | Estimate from ConcurrentExecutions + traffic-pattern analysis. Mark confidence MEDIUM. |
| Function `State != Active` | Skip optimization; surface as BLOCKED. |
| Runtime = java8 (legacy) | SnapStart not supported. Recommend runtime upgrade first (Step 6). |

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

Full gotcha catalog moved to `references/advanced-patterns.md` —
see "Step 0: Non-obvious behaviours".

### Step 1: Memory allocation vs initialization time

Latency-vs-memory curve, Power Tuning detail, and cost-latency note moved to
`references/advanced-patterns.md` (Step 1 deep dive).

**Decision gate after Power Tuning (latency mode):**

| Power Tuning `fastest` vs current MemorySize | Verdict | Action |
|---|---|---|
| `fastest` at higher memory AND InitDuration reduction > 500 ms | **FURTHER_OPTIMIZATION_AVAILABLE** (memory upsize) | Set MemorySize to `fastest`. Verify cost envelope. |
| `fastest` == current | No memory finding | Proceed to other dimensions. |
| `fastest` at lower memory (rare for cold start) | No finding — current is already latency-optimal | Proceed. |

### Step 2: Provisioned concurrency (allocation, scheduling, autoscaling)

Sizing CLI and scheduling detail moved to `references/worked-examples.md` and
`references/advanced-patterns.md` (Step 2 deep dive).

**When provisioned concurrency is justified:**

| Condition | Recommendation |
|---|---|
| Sync API (API Gateway, ALB, Function URL) AND cold-start p95 > SLO | Provisioned concurrency sized to p50-p75 of ConcurrentExecutions |
| Interactive endpoint (user-facing, <1 s SLO) AND cold starts visible | Provisioned concurrency with autoscaling |
| Async event-driven (SQS, Kinesis, EventBridge) | Do NOT use provisioned concurrency. Cold starts are absorbed by the queue/stream. |
| Batch job (rare invocations) | Do NOT use provisioned concurrency. Use on-demand. |

### Step 3: SnapStart (Java only — initialization snapshot)

SnapStart is the single highest-impact optimization for Java Lambda
functions. It takes a snapshot of the initialized JVM and restores it on
cold start, eliminating 1-3 s of JVM + framework init.

**Eligibility:**
- Runtime: java21 (or later supported Java runtimes). SnapStart is
  supported on Corretto distributions.
- NOT available for: Node.js, Python, Go, Ruby, .NET.
- NOT available for: container-image functions (zip-only).

Enablement CLI, expected-impact table, and caveats moved to
`references/advanced-patterns.md` (Step 3 deep dive).

### Step 4: Init phase optimization (lazy initialization, connection pooling)

Global-scope code pattern moved to `references/worked-examples.md`; runtime
connection-reuse table moved to `references/advanced-patterns.md`.

**Init-phase checklist:**

| Symptom | Fix |
|---|---|
| InitDuration > 500 ms (non-Java) | Move SDK clients, DB connections to global scope |
| InitDuration > 1 s (Java, no SnapStart) | Enable SnapStart (Step 3) |
| InitDuration spikes after deploy | Check for new heavy dependencies in import chain |
| DB connection per invocation | Use global connection pool with validity check |
| HTTP client per invocation | Use global HTTP client with keep-alive |

### Step 5: VPC cold start penalty (hyperplane ENI elimination)

VPC deep dive (key fact, failure modes, diagnostic CLI, thresholds) moved to
`references/advanced-patterns.md` + `references/diagnostic-commands.md`.

### Step 6: Runtime selection (compiled vs interpreted, ARM64 Graviton)

Init-speed-by-runtime table and ARM64 note moved to
`references/advanced-patterns.md` (Step 6 deep dive).

**Recommendation framework:**

| Current runtime | Recommendation |
|---|---|
| Java (no SnapStart) | Enable SnapStart (Step 3). If still slow, evaluate migration. |
| Java (SnapStart, still slow) | Init phase optimization (Step 4) + memory tuning (Step 1). |
| nodejs16 (deprecated) | Upgrade to nodejs20+. Deprecated runtimes miss optimizations. |
| java8 (deprecated) | Upgrade to java21. java8 does not support SnapStart. |
| python3.7 (deprecated) | Upgrade to python3.12. |

### Step 7: Deployment package size reduction

Package size correlates with init time. Lambda downloads, extracts, and
loads the deployment package on every cold start. Larger packages mean
longer init.

**Package size thresholds:**

| Package size | Impact | Recommendation |
|---|---|---|
| <5 MB | Negligible init overhead | No action |
| 5-20 MB | Moderate init overhead | Evaluate dependency trimming |
| 20-50 MB | Significant init overhead (100-500 ms) | Trim aggressively |
| >50 MB | Severe init overhead (500+ ms) | Refactor: Proguard, Layers, or container image |

Proguard/JAR trimming, Node/Python trimming, and layer caution moved to
`references/advanced-patterns.md` (Step 7 deep dive).

### Step 8: Impact estimation

Compute the latency impact for each recommendation:

```
current_cold_start_p95 = InitDuration_p95 + Duration_p95
projected_cold_start_p95 = projected_InitDuration_p95 + projected_Duration_p95
latency_reduction_ms = current_cold_start_p95 - projected_cold_start_p95
latency_reduction_pct = (latency_reduction_ms / current_cold_start_p95) × 100
```

Always state assumptions: cold-start frequency (invocations per day
that are cold starts), InitDuration at current and projected memory
(from Power Tuning), SLO threshold, and whether SnapStart is enabled.

## Configuration dependency graph

```
                     ┌─────────────────┐
                     │ Runtime = Java? │
                     └────────┬────────┘
                              │
                   ┌──────────┴──────────┐
                   YES                   NO
                   │                     │
            ┌──────▼──────┐      ┌───────▼───────┐
            │ Enable      │      │ Init phase    │
            │ SnapStart   │      │ optimization  │
            │ (Step 3)    │      │ (Step 4)      │
            └──────┬──────┘      └───────┬───────┘
                   │                     │
                   └──────────┬──────────┘
                              │
                     ┌────────▼────────┐
                     │ Cold-start p95  │
                     │ > SLO?          │
                     └────────┬────────┘
                              │
                   ┌──────────┴──────────┐
                   YES                   NO
                   │                     │
            ┌──────▼──────┐      ┌───────▼───────┐
            │ Add prov.   │      │ Check memory  │
            │ concurrency │      │ + package +   │
            │ (Step 2)    │      │ runtime (1,7) │
            └─────────────┘      └───────────────┘
```

Decision order: SnapStart (if Java) → init phase optimization →
provisioned concurrency (if latency-critical) → memory tuning →
runtime/package optimization.

## Output format

```text
TARGET: <function-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <memory> MB, <runtime>, <architecture>, <SnapStart>, <provisioned concurrency>, <package size>
  Proposed: <memory> MB, <runtime>, <architecture>, <SnapStart>, <provisioned concurrency>, <package size>
  Dimensions changed: <memory | provisioned_concurrency | snapstart | init_phase | vpc | runtime | package>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_LATENCY_IMPACT:
  Current cold-start p95: <ms> (InitDuration: <ms> + Duration: <ms>)
  Projected cold-start p95: <ms>
  Latency reduction: <ms> (<pct>%)
  SLO: p95 < <ms>
  Cold-start frequency: ~<count>/day (<pct>% of invocations)
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <function-name> in <region>.
  Proceed? (yes/no)"
```

Full worked examples are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Self-check EVERY emitted block
against these rules before returning the response. Do NOT substitute
markdown headings, camelCase, or bold variants for the literal labels.

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Latency reduction: 0 ms`.** If every dimension nets zero latency
   delta, the verdict MUST be `OPTIMIZED`. A cost-only improvement is
   surfaced in REASON as a cost note, NOT as latency savings.

2. **NEVER show latency math that does not balance.**
   `Current cold-start p95 − Projected cold-start p95` MUST equal
   `Latency reduction`, rounded to whole milliseconds.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend SnapStart for non-Java runtimes.** SnapStart is
   Java-only. Recommending it for Node.js, Python, or Go is a
   misclassification.

5. **NEVER recommend SnapStart without warning about the versioned-alias
   requirement.** SnapStart requires published versions; `$LATEST` does
   not support it. The MIGRATION_STEPS MUST include `publish-version`.

6. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

7. **NEVER attribute cold-start latency to VPC without verifying ENI
   health.** Since 2019, hyperplane ENIs reduced VPC cold start to
   <100 ms. If VPC latency is diagnosed, cite the specific ENI/subnet/SG
   evidence.

8. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: order-api-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Java 21 function with InitDuration p95 of 3200 ms and SnapStart
  NOT enabled. Enabling SnapStart eliminates 90% of init phase (snapshot
  restore drops InitDuration from 3200 ms to ~200 ms). Function is a
  sync API with cold-start p95 exceeding the 1000 ms SLO.
RECOMMENDATION:
  Current: 512 MB, java21, x86_64, SnapStart OFF, no PC, 52 MB
  Proposed: 512 MB, java21, x86_64, SnapStart ON, no PC, 52 MB
  Dimensions changed: snapstart (Step 3)
  Dimensions checked: memory ✓  provisioned_concurrency ✓  snapstart → (enable)
    init_phase ✓  vpc ✓  runtime ✓  package ✓
  Confidence: HIGH — SnapStart supported on java21; no container-image.
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

**Self-check before emit:**
- [ ] `Current cold-start p95 − Projected cold-start p95 == Latency reduction`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] SnapStart recommendation includes `publish-version` step?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, latency-reducing recommendation. |
| `OPTIMIZED` | All dimensions pass (SnapStart enabled for Java, init optimized, cold-start p95 < SLO, no remaining levers). |
| `NEED_MORE_INFO` | Data gate failed: InitDuration metrics absent, window < 14 days, or Lambda Insights not enabled with no fallback. |
| `BLOCKED` | Hard precondition prevents evaluation: function State != Active, IAM denies lambda:GetFunction, runtime deprecated and blocks all optimizations. |

**Zero-latency-impact rule:** If latency reduction == 0 ms for every
dimension, verdict MUST be `OPTIMIZED`, never
`FURTHER_OPTIMIZATION_AVAILABLE`. Exception: a cost-only improvement
(without latency change) is surfaced in REASON as a cost note, not as
latency savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend SnapStart for non-Java runtimes.** SnapStart is
   Java-only (java21+). Recommending it for Node.js, Python, Go, or
   Ruby is a fundamental misclassification.

2. **NEVER enable provisioned concurrency without verifying that the
   function is latency-critical (sync API, interactive endpoint).**
   Provisioned concurrency for async/event-driven workloads is pure
   waste — cold starts are absorbed by the queue or stream.

3. **NEVER attribute cold-start latency to VPC without verifying ENI
   health.** Since 2019, hyperplane ENIs reduced VPC cold start to
   <100 ms. Diagnosing "VPC cold start" without checking ENI/subnet/SG
   is a false positive.

4. **NEVER recommend a memory increase for cold-start optimization
   without citing Power Tuning latency data.** Memory increases cost;
   the latency improvement must be measured, not assumed.

5. **NEVER enable SnapStart without warning about the versioned-alias
   requirement and network-connection reset.** SnapStart requires
   published versions and resets TCP connections on restore. Missing
   these caveats causes production failures.

Extended anti-patterns in `references/error-handling-and-edge-cases.md`.

## Expert heuristic

Full heuristic text moved to `references/advanced-patterns.md` —
see "Expert heuristic".

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval.
- **Publish a version before enabling SnapStart.** SnapStart applies to
  published versions, not `$LATEST`.
- **Test SnapStart before cutover.** Network connections reset on
  restore; verify DB reconnection logic.
- **Verify provisioned concurrency cost envelope.** Idle charges must be
  justified by the latency SLO.
- **Test memory changes via staging alias.** Higher memory increases
  cost; verify latency improvement justifies.
- **SnapStart + DB connections.** Ensure connection validity checks
  (lazy reconnect) are in place.
- **Provisioned concurrency removal causes cold starts.** Verify SLO
  tolerates cold starts.
- **Power Tuning invokes the function.** Ensure idempotency.
- **Bulk-operation limit:** 5 functions per batch, sorted by estimated
  latency impact.

## Recent AWS features (2024-2026)

Feature list moved to `references/advanced-patterns.md` —
see "Recent AWS features (2024-2026)".

## References

- `references/cold-start-metrics-and-power-tuning.md` — Power Tuning
  deployment (latency mode), Lambda Insights metrics, memory-to-CPU
  mapping, SnapStart CLI sequences, ARM64 matrix, package thresholds.
- `references/worked-examples.md` — SnapStart enablement, provisioned
  concurrency sizing, init phase refactor, memory tuning, already-
  optimal, NEED_MORE_INFO, end-to-end walkthrough.

## References (load on demand)

- [advanced-patterns.md](references/advanced-patterns.md) — mindset principles,
  Step 0 gotchas, per-step deep dives (memory curve, SnapStart, VPC, runtime,
  package), expert heuristic, recent AWS features.
- [diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight
  data-gate CLI listing, VPC/ENI and subnet diagnostics.

## Domain

AWS CloudOps / Lambda Serverless Cold-Start Latency Optimization.

## AWS documentation

- **AWS Lambda Developer Guide** — https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- **Lambda SnapStart** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-snapstart.html
- **Lambda provisioned concurrency** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html
- **Lambda VPC networking** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-vpc.html
- **Lambda memory configuration** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html
- **Lambda runtime deprecation** — https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
- **CloudWatch Lambda Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights.html
- **AWS Lambda Power Tuning (OSS)** — https://github.com/alexcasalboni/aws-lambda-power-tuning
- **AWS CLI Lambda reference** — https://docs.aws.amazon.com/cli/latest/reference/lambda/
- **Well-Architected — Performance Efficiency** — https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html
