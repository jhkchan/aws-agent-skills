---
name: lambda-memory-optimizer
description: 'Optimises AWS Lambda memory configuration across six dimensions: memory-to-CPU proportional allocation (Lambda couples vCPU to memory at 1769 MB = 1 vCPU; cost DECREASES with more memory IF CPU-bound because faster execution offsets higher per-100ms rate), AWS Lambda Power Tuning methodology (open-source Step Functions state machine that empirically finds the Pareto frontier of cost-vs-latency across memory values), cost-optimal vs latency-optimal memory setting selection (the cheapest memory may not be the fastest; surface both numbers and let the operator choose), provisioned concurrency memory reservation (PC bills per GB-second of provisioned capacity regardless of invocations — memory size scales the idle bill linearly), ARM64 Graviton2 memory-to-CPU ratio differences (ARM64 has a different memory-to-vCPU curve than x86_64; re-run Power Tuning after architecture migration), EFS memory overhead (EFS mounts add ~64 MB resident memory; factor into the headroom calculation), init phase memory / cold star...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted CloudWatch metrics and Power Tuning results. Live-account optimization uses aws lambda get-function-configuration, aws cloudwatch get-metric-statistics (Duration, Invocations, memory_used via LambdaInsights, InitDuration, ConcurrentExecutions), aws lambda list-provisioned-concurrency-configs, aws lambda get-event-source-mapping, aws compute-optimizer...
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
  when_to_use: Optimising Lambda memory configuration, planning a Power Tuning sweep, selecting cost-optimal vs latency-optimal memory, sizing provisioned concurrency memory reservation, evaluating ARM64 Graviton2 memory-to-CPU ratio, accounting for EFS/container-image/Layers memory overhead, tuning SnapStart init memory, sizing /tmp storage, or running a Lambda memory FinOps review.
  when_not_to_use: EC2 instance rightsizing (use ec2-rightsizing-optimizer), EBS volume cost (use ebs-volume-optimizer), S3 storage cost (use s3-lifecycle-optimizer), Lambda invocation/duration/cold-start troubleshooting (use lambda-invocation-troubleshooter or lambda-cold-start-optimizer), or full Lambda cost optimization across non-memory dimensions (use lambda-cost-optimizer). This skill focuses on the memory-allocation decision specifically.
  activation_triggers: optimise Lambda memory, Lambda memory tuning, Lambda Power Tuning, Lambda cost-optimal memory, Lambda latency-optimal memory, Lambda U-curve, Lambda memory CPU-bound, Lambda memory I/O-bound, Lambda memory Pareto frontier, Lambda memory Compute Optimizer, Lambda provisioned concurrency memory, Lambda ARM64 Graviton2 memory, Lambda SnapStart init memory, Lambda EFS memory overhead, Lambda container image memory, Lambda Layers memory, Lambda /tmp storage allocation, Lambda memory FinOps, Lambda memory-to-CPU ratio
  invocation_schema: 'Input: either (a) a function identifier + live-account context, (b) a Power Tuning result document, OR (c) CloudWatch Lambda Insights metrics (Duration, Invocations, memory_used, InitDuration) with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS block per function, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline finding classification):\nFunctionName: order-enrichment-api\nRuntime: python3.12\nMemorySize: 128 MB\nArchitecture: x86_64\nRegion: us-east-1\nPricing: on-demand (no provisioned concurrency)\nMetrics (last 30 days):\n  - Duration avg: 5000 ms, p95: 6200 ms\n  - Invocations: 47,000,000/month\n  - Errors: 45 (0.000096%)\n  - Memory utilization: avg 38 MB (30% of 128 MB)\n  - InitDuration: 1800 ms (cold start)\nLambda Insights:\n  - memory_used: avg 38 MB, peak 52 MB\n  - cpu_total_time: 4800 ms (96% of Duration)\nCompute Optimizer finding: Overprovisioned (memory)\nPower Tuning result:\n  - Tested: [128, 256, 512, 1024, 2048, 3008]\n  - Cheapest (cost-optimal): 512 MB at 950 ms\n  - Fastest: 3008 MB at 410 ms\n  - URL: https://lambda-power-tuning.show/#example\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Lambda, memory optimization, memory configuration, Power Tuning, Pareto frontier, cost-optimal memory, latency-optimal memory, CPU-bound, I/O-bound, U-curve, provisioned concurrency, ARM64, Graviton2, memory-to-CPU ratio, SnapStart, cold start, init phase, EFS, container image, Lambda Layers, /tmp storage, CloudWatch Duration, Lambda Insights, FinOps, Compute Optimizer
  tags: lambda, compute, serverless, cost-optimization, finops, memory-tuning, power-tuning
---

# Lambda Memory Optimizer

## What this skill does


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why the U-curve is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a function |
| Pre-flight data gate | CloudWatch metrics, Power Tuning, Insights | Before any recommendation |
| Step 0 non-obvious behaviours | CPU coupling, ARM64 ratio, SnapStart, EFS | Edge cases |
| Step 1 Memory size (U-curve) | Power Tuning, cost-vs-latency tradeoff | The headline savings dimension |
| Step 2 Provisioned concurrency memory | PC idle bill scales with memory | Latency-sensitive APIs |
| Step 3 Init-phase memory | Cold start, SnapStart, lazy init | Slow init functions |
| Step 4 EFS / container / Layers overhead | Resident memory add-ons | Heavy dependency functions |
| Step 5 /tmp storage allocation | Decouple /tmp from memory budget | Functions with local scratch |
| Step 6 ARM64 memory-to-CPU ratio | Graviton2 re-tuning after migration | Architecture changes |
| Step 7 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, version publish, alias | Before any apply CLI |

## Quick start

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


## Mindset


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Power Tuning `cheapest` differs from current MemorySize by ≥ 1 step AND projected compute saving > 0 | **FURTHER_OPTIMIZATION_AVAILABLE** (memory) | Step 1 — set MemorySize to Power Tuning optimum |
| Power Tuning `cheapest` == current BUT `fastest` is materially faster AND operator prioritises latency | **FURTHER_OPTIMIZATION_AVAILABLE** (memory — latency) | Step 1 — set MemorySize to `fastest`; surface cost-neutral or cost-increasing delta |
| Provisioned concurrency configured AND MemorySize > Power Tuning `cheapest` (oversized memory inflating PC idle bill) | **FURTHER_OPTIMIZATION_AVAILABLE** (PC memory) | Step 2 — right-size memory first, then re-evaluate PC |
| InitDuration > 1 s on cold starts AND no SnapStart AND runtime is Java | **FURTHER_OPTIMIZATION_AVAILABLE** (init) | Step 3 — enable SnapStart, lazy init, connection reuse |
| EFS mounted AND resident memory > 64 MB baseline AND MemorySize at minimum | **FURTHER_OPTIMIZATION_AVAILABLE** (EFS) | Step 4 — increase MemorySize to accommodate EFS baseline OR remove EFS |
| Container image deployment AND MemorySize < 256 MB | **FURTHER_OPTIMIZATION_AVAILABLE** (container) | Step 4 — increase to 256 MB minimum |
| /tmp allocation > 512 MB AND MemorySize at minimum (function using memory as /tmp overflow) | **FURTHER_OPTIMIZATION_AVAILABLE** (/tmp) | Step 5 — decouple /tmp via `--ephemeral-storage` |
| Architecture = x86_64 AND runtime is ARM-compatible | **FURTHER_OPTIMIZATION_AVAILABLE** (architecture) | Step 6 — migrate to arm64 AND re-run Power Tuning |
| Compute Optimizer finding `Optimized` + Power Tuning confirms current memory + arm64 + no init waste | **OPTIMIZED** | None — continue monitoring |
| Duration/Invocations metrics absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |
| All dimensions verified AND a change was applied and confirmed this session | **OPTIMIZED** | Emit post-state verification |

## Pre-flight: data gate (run before any optimization decision)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.



Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


## Process — Memory optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


### Step 1: Memory size (the U-curve)

Memory size is the primary lever because of the U-curve: as memory
increases, CPU increases proportionally, and CPU-bound workloads see
disproportionate duration reduction.


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


**Decision gate after Power Tuning:**

| Power Tuning result vs current MemorySize | Verdict | Action |
|---|---|---|
| `cheapest` < current AND projected saving > 0 | **FURTHER_OPTIMIZATION_AVAILABLE** (downsize) | Set MemorySize to `cheapest`. Verify duration stays within SLO. |
| `cheapest` > current AND projected saving > 0 | **FURTHER_OPTIMIZATION_AVAILABLE** (upsize) | Set MemorySize to `cheapest`. Function was CPU-bound. |
| `cheapest` == current BUT `fastest` is materially faster | **FURTHER_OPTIMIZATION_AVAILABLE** (latency) | Surface the latency improvement; let operator choose. May be cost-increasing. |
| `cheapest` == current AND `fastest` == current | No memory finding | Proceed to other dimensions. |


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


### Step 2: Provisioned concurrency memory footprint


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


**Decision tree:**
```
Is provisioned concurrency configured?
├── NO → PC memory check passes.
└── YES → Is MemorySize > Power Tuning `cheapest`?
    ├── NO → Memory already right-sized; PC idle is justified.
    └── YES → **FURTHER_OPTIMIZATION_AVAILABLE** (PC memory)
              Right-size memory FIRST, then re-evaluate PC count.
```


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


### Step 3: Init-phase memory (cold start)

Init-phase memory is the memory consumed during the function's
initialization (before the handler runs). High init memory causes slow
cold starts and, in extreme cases, OOM during init.

**Init-waste checklist:**

| Symptom | Fix |
|---|---|
| InitDuration > 1 s (cold start) | Move init OUTSIDE the handler. Reuse HTTP clients, DB connections. |
| InitDuration > 3 s on Java | Enable SnapStart, publish a version. |
| InitDuration spikes after Layers added | Audit Layers — each is a separate zip extraction. Reduce layer count. |
| InitDuration spikes after dependency update | Trim unused deps. Use `pip install --no-deps`. |
| OOM during init (rare) | Increase MemorySize to accommodate peak init allocation. |


Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.


### Step 4: EFS, container image, and Layers memory overhead

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


### Step 5: /tmp storage allocation

Since 2022, `/tmp` storage is configured independently of MemorySize
via `--ephemeral-storage` (up to 10 GB). Bills separately at
$0.0000000625/MB-second.

**Decision tree:**
```
Is the function using memory as /tmp overflow (high MemorySize, low
runtime memory_used)?
├── NO → /tmp check passes.
└── YES → **FURTHER_OPTIMIZATION_AVAILABLE** (/tmp)
          Decouple: reduce MemorySize to runtime needs, allocate /tmp
          via --ephemeral-storage.
```


Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.


### Step 6: ARM64 (Graviton2) memory-to-CPU ratio

ARM64 has a different memory-to-vCPU ratio than x86_64. After migrating
architecture, the U-curve minimum shifts.


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.



Moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md) — load on demand.



Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


### Step 7: Impact estimation

Compute the monthly savings for each recommendation:


Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


### Step 8: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND function is on arm64 AND no init waste AND no
  /tmp-memory coupling → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (Duration absent, window < 14 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

Moved verbatim to [references/lambda-memory-worked-examples.md](references/lambda-memory-worked-examples.md) — load on demand.



Moved verbatim to [references/lambda-memory-worked-examples.md](references/lambda-memory-worked-examples.md) — load on demand.


Full worked examples (memory upsize, memory downsize, PC memory
cascading, ARM64 re-tuning, already-optimized, end-to-end walkthrough)
are in `references/lambda-memory-worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT substitute markdown headings, camelCase, or bold
variants.

```text
TARGET: <function-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
POWER_TUNING_RESULTS:
  | Memory   | Avg Duration | p99 Duration | $/Invocation | Tag            |
  |----------|-------------|-------------|-------------|----------------|
  | <MB>     | <ms>        | <ms>        | $<amount>   | current        |
  | <MB>     | <ms>        | <ms>        | $<amount>   | cost-optimal   |
  | <MB>     | <ms>        | <ms>        | $<amount>   | latency-optimal|
COST_COMPARISON:
  Current:  <MB> at <ms> avg → $<amount>/invocation × <N>/month = $<amount>/month
  Proposed: <MB> at <ms> avg → $<amount>/invocation × <N>/month = $<amount>/month
  Saving:   $<amount>/month (<pct>%)
  Latency:  p99 drops from <ms> to <ms> (<pct>% reduction)
RECOMMENDATION:
  Current: <memory> MB at <avg duration> ms, <architecture>, <concurrency>, <init>
  Proposed: <memory> MB at <projected duration> ms, <architecture>, <concurrency>, <init>
  Dimensions changed: <memory | pc_memory | init | efs_container_layers | tmp | architecture>
  Dimensions checked: <list ALL six, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show compute + requests + PC subtotals
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
  Latency delta: <p99 duration change> ms (<percentage>%)
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00` AND no latency improvement.** If every
   dimension nets zero cost delta AND zero latency delta, the verdict
   MUST be `OPTIMIZED`. A cost-neutral latency improvement is surfaced
   in `Latency delta`, NOT as a dollar saving.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend a memory change without citing Power Tuning or
   Compute Optimizer evidence.** The U-curve is workload-specific;
   guessing from "128 MB is cheapest" produces false positives on
   CPU-bound workloads.

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all six dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER present a cost-increasing memory upsize as "cost savings."**
   Surface the latency improvement explicitly. If the upsize increases
   cost, set `Monthly saving: $0.00` (or negative) and surface the
   latency delta. Verdict is `FURTHER_OPTIMIZATION_AVAILABLE` ONLY if
   the operator explicitly prioritises latency over cost.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

8. **NEVER omit the POWER_TUNING_RESULTS table from a
   FURTHER_OPTIMIZATION_AVAILABLE verdict.** The table must show at least
   the current memory, the cost-optimal memory, and the latency-optimal
   memory with concrete $/invocation and p99 latency values.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.
Additional full worked examples are in
`references/lambda-memory-worked-examples.md`.

```text
TARGET: order-enrichment-api (arn:aws:lambda:us-east-1:123456789012:function:order-enrichment-api)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Python function at 128 MB averaging 5000 ms is CPU-bound
  (cpu_total_time / Duration = 0.96). Power Tuning U-curve shows
  cost-optimal at 256 MB where duration drops to 1100 ms — the per-
  invocation cost drops 54.7% because the duration reduction more than
  offsets the higher per-GB-second rate. Invocations are 47M/month so
  the saving compounds. Latency-optimal at 3008 MB (220 ms p99) is
  surfaced separately for operator choice.
POWER_TUNING_RESULTS:
  | Memory   | Avg Duration | p99 Duration | $/Invocation | Tag            |
  |----------|-------------|-------------|-------------|----------------|
  | 128 MB   | 5000 ms     | 6200 ms     | $0.0000106  | current        |
  | 256 MB   | 1100 ms     | 1400 ms     | $0.0000048  | cost-optimal   |
  | 512 MB   | 650 ms      | 800 ms      | $0.0000056  |                |
  | 1024 MB  | 400 ms      | 500 ms      | $0.0000069  |                |
  | 2048 MB  | 280 ms      | 350 ms      | $0.0000095  |                |
  | 3008 MB  | 220 ms      | 280 ms      | $0.0000112  | latency-optimal|
COST_COMPARISON:
  Current:  128 MB at 5000 ms → $0.0000106/inv × 47M/month = $499.14/month
  Proposed: 256 MB at 1100 ms → $0.0000048/inv × 47M/month = $224.66/month
  Saving:   $274.48/month (54.9%) — cost-optimal at 256 MB
  Latency:  p99 drops from 6200 ms to 1400 ms (77% reduction)
RECOMMENDATION:
  Current: 128 MB at 5000 ms avg, x86_64, on-demand, InitDuration 1800 ms
  Proposed: 256 MB at 1100 ms avg, x86_64, on-demand, InitDuration 1800 ms
  Dimensions changed: memory (Step 1)
  Dimensions checked: memory → (upsize to cost-optimal)  pc_memory ✓ (no PC)
    init ✓ (no SnapStart for Python)  efs_container_layers ✓ (zip, no EFS)
    tmp ✓ (no /tmp overflow)  architecture ✓ (x86_64, ARM eval deferred)
  Confidence: HIGH — Power Tuning measured the U-curve empirically across
    6 memory values; cpu_total_time / Duration = 0.96 confirms CPU-bound.
ESTIMATED_SAVINGS:
  Current monthly: $499.14
    compute: 47M × 5.0 × 0.125 × $0.0000166667 = $489.74
    requests: 47M × $0.0000002 = $9.40
    PC: $0 (on-demand)
  Projected monthly: $224.66
    compute: 47M × 1.1 × 0.25 × $0.0000166667 = $215.26
    requests: 47M × $0.0000002 = $9.40
    PC: $0 (on-demand)
  Monthly saving: $274.48   ($499.14 − $224.66 = $274.48 ✓)
  Annual saving: $3,293.76
  Latency delta: p99 drops from 6200 ms to 1400 ms (77% reduction)
MIGRATION_STEPS:
  1. Run Power Tuning to confirm the U-curve:
     aws stepfunctions start-execution \
       --state-machine-arn arn:aws:states:us-east-1:123456789012:stateMachine:powerTuning \
       --input '{"lambda":{"resource":"arn:aws:lambda:us-east-1:123456789012:function:order-enrichment-api","num":5},"power":{"values":[128,256,512,1024,2048,3008]}}'
  2. Update memory to 256 MB (cost-optimal):
     aws lambda update-function-configuration \
       --function-name order-enrichment-api --memory-size 256 --region us-east-1
  3. Publish a version and test via staging alias:
     aws lambda publish-version --function-name order-enrichment-api
     aws lambda update-alias --function-name order-enrichment-api \
       --name staging --function-version 2
  4. Monitor Duration and Errors for 7 days post-change:
     aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
       --metric-name Duration --dimensions Name=FunctionName,Value=order-enrichment-api \
       --start-time $(date -u -v-7d +%Y-%m-%dT%H:%M:%S) \
       --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 86400 --statistics Average
CONFIRM: About to update-function-configuration on order-enrichment-api
  (128 MB → 256 MB). Monthly saving $274.48 (54.9%); p99 latency
  improvement 77%. Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All six dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?
- [ ] If `Monthly saving == $0.00`, is there a non-zero `Latency delta`?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing OR latency-improving recommendation. |
| `OPTIMIZED` | Either (a) all dimensions pass (memory at Power Tuning optimum, on arm64, no init waste, no /tmp-memory coupling), OR (b) a change was applied and verified this session. |
| `NEED_MORE_INFO` | Data gate failed: metrics absent, window < 14 days, Compute Optimizer stale with no CloudWatch fallback. |
| `BLOCKED` | Hard precondition prevents evaluation: function State != Active, IAM denies lambda:GetFunction. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 AND Latency delta is
zero for every dimension, verdict MUST be `OPTIMIZED`, never
`FURTHER_OPTIMIZATION_AVAILABLE`. Exception: a latency improvement
without cost change is surfaced in `Latency delta`, not as dollar
savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend a memory change without Power Tuning or Compute
   Optimizer evidence.** The U-curve is workload-specific; guessing
   from "128 MB is cheapest" produces false positives on CPU-bound
   workloads.

2. **NEVER recommend a memory upsize as "cost savings" without
   verifying that the duration reduction offsets the higher per-GB-
   second rate.** A memory upsize that increases total cost is a
   latency improvement, not a cost saving. Surface both numbers.

3. **NEVER recommend ARM64 migration without verifying the runtime and
   dependencies are ARM-compatible.** An ARM migration that breaks at
   runtime is worse than no migration. Re-run Power Tuning after
   migration — the U-curve shifts.

4. **NEVER increase MemorySize to accommodate /tmp overflow without
   considering ephemeral storage.** Decoupling /tmp via
   `--ephemeral-storage` is usually cheaper than increasing MemorySize.

5. **NEVER enable SnapStart without publishing a version and pointing
   an alias at it.** SnapStart applies to published versions only;
   `$LATEST` does not benefit from SnapStart.

Extended anti-patterns in `references/lambda-memory-worked-examples.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Publish a version before changing the alias.** Never point
  production at `$LATEST`.
- **Test the new memory setting before cutover.** Validate via staging
  alias or weighted routing.
- **Verify ARM64 compatibility before architecture migration.** Native
  dependencies may fail at runtime. Re-run Power Tuning after migration.
- **SnapStart requires versioned aliases.** Ensure alias points at a
  version before enabling. Java-only.
- **Memory reduction increases OOM risk.** Verify `memory_used` peak
  (Lambda Insights) is below 80% of the proposed MemorySize.
- **PC memory reduction is immediate.** Function must handle the new
  memory without OOM or timeout.
- **EFS removal may break the function.** Verify no code paths reference
  the mount point before removing.
- **Power Tuning invokes the function repeatedly.** Ensure function is
  idempotent and downstream tolerates test load.
- **Bulk-operation limit:** Process at most 5 functions per batch. Sort
  by estimated savings, verify each batch before proceeding. Abort if
  any function shows increased errors or duration post-change.

## Recent AWS features (2024-2026)

Moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md) — load on demand.


## References

- `references/lambda-memory-and-power-tuning.md` — pricing tables,
  memory-to-CPU mapping, Power Tuning deployment guide, ARM64 vs x86_64
  memory-to-CPU ratio comparison, EFS/container/Layers overhead baselines,
  ephemeral storage pricing, SnapStart runtime support matrix, regional
  pricing multipliers.
- `references/lambda-memory-worked-examples.md` — full worked examples
  (memory upsize for CPU-bound, memory downsize for I/O-bound, PC memory
  cascading, ARM64 re-tuning, /tmp decoupling, already-optimized, NEED_
  MORE_INFO, end-to-end walkthrough, extended NEVER list, edge cases).


## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 gotchas, data-quality short-circuits, U-curve and PC pricing math, overhead baselines, recent AWS features
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — data-gate CLI sources, SnapStart enablement, /tmp decoupling, arm64 re-tuning commands
- [references/lambda-memory-worked-examples.md](references/lambda-memory-worked-examples.md) — full worked examples plus the canonical output template and output-order decision tree
- [references/lambda-memory-and-power-tuning.md](references/lambda-memory-and-power-tuning.md) — pricing tables, Power Tuning deployment guide, memory-to-CPU mapping

## Domain

AWS CloudOps / Lambda Serverless Memory Optimization & FinOps.

## AWS documentation

- **AWS Lambda Developer Guide** — https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- **AWS Lambda pricing** — https://aws.amazon.com/lambda/pricing/
- **AWS Lambda memory and CPU** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html
- **Lambda SnapStart** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-snapstart.html
- **Lambda provisioned concurrency** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html
- **Lambda ephemeral storage** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-ephemeral-storage.html
- **Lambda Layers** — https://docs.aws.amazon.com/lambda/latest/dg/chapter-layers.html
- **AWS Lambda Power Tuning (open source)** — https://github.com/alexcasalboni/aws-lambda-power-tuning
- **AWS Compute Optimizer — Lambda** — https://docs.aws.amazon.com/compute-optimizer/latest/ug/lambda.html
- **CloudWatch Lambda Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights.html
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
