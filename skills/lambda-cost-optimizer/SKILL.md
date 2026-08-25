---
name: lambda-cost-optimizer
description: 'Optimises AWS Lambda function cost across six dimensions: memory tuning (CPU scales with memory at 1769 MB = 1 vCPU; more memory can REDUCE total cost when faster execution offsets the higher per-GB-second rate), provisioned concurrency right-sizing (on-demand vs provisioned break-even math), duration reduction (SnapStart for Java, lazy init, connection reuse, package trim), invocation-frequency analysis (SQS/Kinesis/DynamoDB Streams batch size and batch window tuning), architecture migration (ARM64 Graviton2 is 20% cheaper; Fargate for >15-min workloads; Step Functions for orchestration chains), and Lambda Layers. Uses AWS Lambda Power Tuning (open-source Step Functions) to empirically find the cost-optimal memory, reads Compute Optimizer Lambda findings, and projects monthly savings. Emits OPPORTUNITY_FOUND with specific recommendation and estimated savings, OPTIMIZED, or ALREADY_OPTIMAL. Use when reviewing Lambda spend, planning a memory tuning sweep, sizing provisioned concurrency, or a FinOps review.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted CloudWatch metrics and Compute Optimizer findings. Live-account optimization uses aws lambda list-functions, aws lambda get-function-configuration, aws cloudwatch get-metric-statistics (Duration, Invocations, Errors, Throttles, ConcurrentExecutions), aws lambda get-event-source-mapping, aws lambda list-provisioned-concurrency-configs, aws compute-optimizer...
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
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Optimising Lambda function cost, triaging Compute Optimizer Lambda findings, planning a memory tuning sweep (Power Tuning), sizing provisioned concurrency vs on-demand, reducing function duration, tuning SQS/DynamoDB/Kinesis event source mapping batch size, evaluating ARM64 (Graviton2) migration, or migrating long-running Lambda workloads to Fargate or Step Functions.
  when_not_to_use: EC2 instance rightsizing (use ec2-rightsizing-optimizer), EBS volume cost (use ebs-volume-optimizer), S3 storage cost (use s3-lifecycle-optimizer), or Lambda troubleshooting (invocation errors, timeouts, configuration bugs — use the Lambda troubleshooter). This skill focuses on cost-driven optimization decisions, not functional debugging of broken functions.
  activation_triggers: optimise Lambda cost, Lambda memory tuning, Lambda Power Tuning, Lambda Compute Optimizer recommendations, Lambda provisioned concurrency, Lambda duration optimization, Lambda cold start, Lambda SnapStart Java, Lambda batch size SQS, Lambda ARM64 Graviton2, Lambda Layers shared code, Lambda invocation frequency, Lambda FinOps savings, Lambda to Fargate migration, Lambda monthly savings estimate, reduce Lambda bill, serverless cost review
  invocation_schema: 'Input: either (a) a function identifier + live-account context, (b) a Compute Optimizer Lambda finding document, OR (c) CloudWatch Lambda Insights metrics (Duration, Invocations, Memory utilization, ConcurrentExecutions, Errors) with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS block per function, where VERDICT is one of OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL.'
  invocation_example: "# Minimal valid input (offline finding classification):\nFunctionName: order-processor-prod\nRuntime: nodejs20.x\nMemorySize: 128 MB\nArchitecture: x86_64\nRegion: us-east-1\nPricing: on-demand (no provisioned concurrency)\nMetrics (last 30 days):\n  - Duration avg: 5200 ms, p95: 6100 ms\n  - Invocations: 50,000,000/month\n  - Errors: 12,000 (0.024%)\n  - Memory utilization: avg 38 MB (30% of 128 MB)\nCompute Optimizer finding: Overprovisioned (memory)\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Lambda, memory configuration, cost optimization, Power Tuning, provisioned concurrency, on-demand, duration, cold start, SnapStart, invocation frequency, batch size, batch window, event source mapping, SQS, DynamoDB Streams, Kinesis, Lambda Layers, ARM64, Graviton2, Fargate migration, Step Functions, FinOps, Compute Optimizer, serverless
  tags: lambda, compute, serverless, cost-optimization, finops, memory-tuning, power-tuning, graviton
---

# Lambda Cost Optimizer

## What this skill does

Translates a Lambda function's runtime posture into a concrete cost-
optimization recommendation with a dollar-denominated savings estimate.
The verdict is the highest-leverage action across six dimensions — memory,
provisioned concurrency, duration, invocation frequency, architecture, and
workload placement — applied in priority order. Always pairs the
recommendation with exact CLI commands (or Power Tuning invocation).

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why memory tuning is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a function |
| Pre-flight data gate | CloudWatch metrics, Compute Optimizer | Before any recommendation |
| Step 0 non-obvious behaviours | CPU-memory coupling, SnapStart, ESM, ARM64 | Edge cases |
| Step 1 Memory configuration | Power Tuning, optimal-memory math | The headline savings dimension |
| Step 2 Provisioned concurrency | On-demand vs provisioned break-even | Latency-sensitive APIs |
| Step 3 Duration optimization | Cold start, init, connection reuse | Slow functions |
| Step 4 Invocation frequency | Batch size, batch window, long polling | High-volume consumers |
| Step 5 Architecture / placement | ARM64, Layers, Fargate, Step Functions | Cross-cutting savings |
| Step 6 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, version publish, alias | Before any apply CLI |

## Quick start

- **Memory is the #1 lever.** Lambda couples vCPU to memory (1769 MB =
  1 vCPU). More memory can REDUCE total cost when faster execution
  offsets the higher per-GB-second rate. Classic example: 128 MB at 5 s
  costs $0.000000835/invocation; 512 MB at 1 s costs $0.000000667 — 33%
  CHEAPER at the higher memory. Always run Power Tuning before assuming
  128 MB is cheapest.
- **Cost formula (memorise this):**
  `cost = (invocations × duration_s × memory_GB × $0.0000166667)
         + (invocations × $0.0000002)`
- **Provisioned concurrency pays for idle.** Use it ONLY for steady-
  traffic, latency-sensitive APIs where cold starts hurt. For batch,
  event-driven, or sporadic workloads, on-demand is cheaper.
- **Architecture is a free 20%.** ARM64 (Graviton2) is ~20% cheaper than
  x86_64 for supported runtimes. Check the runtime support matrix and
  migrate when possible.

## Mindset

Lambda cost optimization is a price-performance decision, not a pure
utilization exercise. The goal is the memory/concurrency/architecture
configuration that minimizes dollar cost while preserving latency and
error-rate SLOs — not the absolute minimum memory that runs the code.

Four-principle deep dive moved to `references/advanced-patterns.md` —
see "Mindset — four principles".

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Memory tuning U-curve minimum differs from current MemorySize by ≥ 1 step AND projected compute saving > 0 | **OPPORTUNITY_FOUND** (memory) | Step 1 — set MemorySize to Power Tuning optimum |
| Provisioned concurrency configured AND ConcurrentExecutions sustained < 30% of provisioned | **OPPORTUNITY_FOUND** (concurrency) | Step 2 — reduce or remove provisioned concurrency |
| No provisioned concurrency AND latency-sensitive API AND cold-start p95 > 1 s AND steady traffic | **OPPORTUNITY_FOUND** (concurrency — add) | Step 2 — add provisioned concurrency sized to baseline |
| Duration p95 > 2× the runtime's healthy baseline OR cold-start duration > 3 s on Java without SnapStart | **OPPORTUNITY_FOUND** (duration) | Step 3 — SnapStart, lazy init, connection reuse, package trim |
| Event source mapping batch size = 1 on SQS/Kinesis/DynamoDB Streams with high message arrival rate | **OPPORTUNITY_FOUND** (invocation frequency) | Step 4 — tune batch size + batch window |
| Architecture = x86_64 AND runtime is ARM-compatible (Node/Python/Java/.NET/Go/Ruby) | **OPPORTUNITY_FOUND** (architecture) | Step 5 — migrate to arm64 |
| Function duration p95 > 10 min sustained OR timeout set to 15 min and frequently hit | **OPPORTUNITY_FOUND** (placement) | Step 5 — migrate workload to Fargate |
| Compute Optimizer finding `Optimized` + Power Tuning confirms current memory + ARM64 already + no duration waste | **ALREADY_OPTIMAL** | None — continue monitoring |
| Duration/Invocations metrics absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |
| All dimensions verified AND a change was applied and confirmed this session | **OPTIMIZED** | Emit post-state verification |

## Pre-flight: data gate (run before any optimization decision)

Required data-source CLI listing moved to `references/diagnostic-commands.md`.
Full sequences: `references/lambda-pricing-and-power-tuning.md`.

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `Duration` metric absent (function never invoked) | **NEED_MORE_INFO**. Verify trigger wiring; skip until invocations exist. |
| `Invocations` Sum = 0 over 14 days | Emit **ALREADY_OPTIMAL** with note "dormant function." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `memory_used` (Lambda Insights) absent | Fall back to Power Tuning only; mark Memory recommendation MEDIUM confidence. |
| Compute Optimizer enrollment `Inactive` | Proceed with CloudWatch + Power Tuning directly. |
| Compute Optimizer `lastRefreshTimestamp` > 30 days old | Stale finding. Re-run `get-lambda-function-recommendations`. |
| Function `State != Active` | Skip optimization; surface as BLOCKED. |

When CloudWatch and Compute Optimizer disagree, Power Tuning is the
tiebreaker — it measures the actual U-curve.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

Full gotcha catalog (CPU-memory coupling, U-curve, SnapStart memory cost,
layer extraction cost, Power Tuning cost rules) moved to `references/advanced-patterns.md`.


### Step 1: Memory configuration (the #1 lever)

Memory is the primary cost lever because of the U-curve: as memory
increases, CPU increases proportionally, and CPU-bound workloads see
disproportionate duration reduction.

U-curve math block moved to `references/lambda-pricing-and-power-tuning.md`;
the formula also appears in Quick start above.

**Finding the U-curve minimum: AWS Lambda Power Tuning.** Open-source
Step Functions tool that empirically measures the cost-duration curve.
Deploy via SAR; run an execution; read the `cheapest` field. Full
deployment and execution CLI is in `references/lambda-pricing-and-power-tuning.md`.

**Decision gate after Power Tuning:**

| Power Tuning `cheapest` vs current MemorySize | Verdict | Action |
|---|---|---|
| `cheapest` < current AND projected saving > 0 | **OPPORTUNITY_FOUND** (downsize) | Set MemorySize to `cheapest`. Verify duration stays within SLO. |
| `cheapest` > current AND projected saving > 0 | **OPPORTUNITY_FOUND** (upsize) | Set MemorySize to `cheapest`. Function was CPU-bound. |
| `cheapest` == current | No memory finding | Proceed to other dimensions. |

### Step 2: Provisioned concurrency vs on-demand

Provisioned concurrency pre-initializes execution environments to
eliminate cold starts, but charges for idle time.

**Decision tree:**
```
Is the function latency-sensitive (API, real-time)?
├── NO → Use on-demand. Provisioned is wasted spend.
└── YES → Is cold-start duration > SLO threshold (e.g., p95 > 1 s)?
    ├── NO → Use on-demand.
    └── YES → Is traffic consistent (CV < 0.5)?
        ├── NO → Consider provisioned concurrency autoscaling.
        └── YES → Provisioned concurrency ≈ p50 of observed ConcurrentExecutions.
```

**Right-sizing check:** If provisioned > 2x p99 ConcurrentExecutions,
reduce to ~p90. If provisioned < p50 consistently, increase to ~p75-p90.

### Step 3: Duration optimization

Duration is the second multiplier in the cost formula. Reducing duration
reduces cost linearly.

**Duration-waste checklist:**

| Symptom | Fix |
|---|---|
| InitDuration > 1 s (cold start) | Move init OUTSIDE the handler. Reuse HTTP clients, DB connections. |
| InitDuration > 3 s on Java | Enable SnapStart, publish a version. |
| Duration >> expected | Profile with X-Ray; identify slowest segment. |
| Duration increased after deploy | Trim unused dependencies. Use Layers for shared code. |
| Duration spikes correlate with concurrency spikes | Downstream bottleneck; use reserved concurrency to cap. |
| Duration = Timeout frequently | Increase timeout OR migrate to Fargate (if > 15 min). |

Code-level optimization detail moved to `references/advanced-patterns.md` —
see "Step 3 deep dive".

### Step 4: Invocation frequency analysis

Invocation frequency is the multiplier on every cost term. Reducing
invocation count reduces cost linearly.

**ESM tuning:** For SQS/Kinesis/DynamoDB Streams, default batch size is
10. Increase to 100-10000 for high-throughput sources. Pair with
`MaximumBatchingWindowInSeconds=1-5`.

```bash
aws lambda update-event-source-mapping \
  --uuid <uuid> --batch-size 100 --maximum-batching-window-in-seconds 5
```

**Invocation-count saving from batch tuning:**
```
old_invocations = messages_per_hour / old_batch_size
new_invocations = messages_per_hour / new_batch_size
monthly_saving = (old_invocations - new_invocations) × 730 × $0.0000002
```

Batch-tuning example, caveat, and SQS long polling moved to
`references/advanced-patterns.md` (Step 4 deep dive).

### Step 5: Architecture and workload placement

ARM64 migration CLI moved to `references/advanced-patterns.md`; Step
Functions pricing note moved there too (Step 5 deep dive).

See `references/lambda-pricing-and-power-tuning.md` for the full runtime
ARM64 compatibility matrix.

**Fargate migration for long-running workloads:**

| Signal | Recommendation |
|---|---|
| Duration p95 > 10 min AND timeout = 15 min | Migrate to Fargate |
| Duration p95 > 5 min AND batch workload | Consider Fargate for cost predictability |
| Function orchestrates 5+ other functions | Migrate orchestration to Step Functions |

### Step 6: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (monthly_invocations × avg_duration_s × current_memory_GB × $0.0000166667)
  + (monthly_invocations × $0.0000002)

projected_monthly_cost =
  (monthly_invocations × projected_duration_s × projected_memory_GB × $0.0000166667)
  + (monthly_invocations × $0.0000002)

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: monthly invocation count, average duration at
current and projected memory (from Power Tuning), memory in GB, pricing
region, provisioned concurrency status.

### Step 7: Final verdict

- Any dimension recommends a change → **OPPORTUNITY_FOUND**.
- All dimensions pass AND function is on ARM64 AND no waste → **ALREADY_OPTIMAL**.
- Change applied and verified this session → **OPTIMIZED**.
- Data insufficient (Duration absent, window < 14 days) → **NEED_MORE_INFO**.

Never emit `OPPORTUNITY_FOUND` without first discharging every
`NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

```text
TARGET: <function-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <memory> MB at <avg duration> ms duration, <architecture>, <concurrency>
  Proposed: <memory> MB at <projected duration> ms duration, <architecture>, <concurrency>
  Dimensions changed: <memory | concurrency | duration | frequency | architecture | placement>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list (invocation count, pricing region, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <function-name> in <region>.
  Proceed? (yes/no)"
```

Full worked examples (memory upsize, ARM64 migration, provisioned
concurrency removal, already-optimal, NEED_MORE_INFO, and end-to-end
walkthrough) are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Required output structure

Every response MUST be a single block using these literal labels, in this
order. Do NOT substitute markdown headings, camelCase, or bold variants.

```text
TARGET: <function-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <memory> MB at <avg duration> ms, <architecture>, <concurrency>
  Proposed: <memory> MB at <projected duration> ms, <architecture>, <concurrency>
  Dimensions changed: <memory | concurrency | duration | frequency | architecture | placement>
  Dimensions checked: <list ALL six, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show compute + requests subtotals
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: OPPORTUNITY_FOUND` with `Monthly saving: $0.00`.**
   If every dimension nets zero cost delta, the verdict MUST be
   `ALREADY_OPTIMAL`. A cost-neutral latency improvement is surfaced in
   REASON as a latency delta, NOT as a dollar saving.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend a memory change without citing Power Tuning or
   Compute Optimizer evidence.** The REASON MUST name the evidence source.

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all six dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER present a cost-neutral or cost-increasing memory upsize as
   "cost savings."** Surface the latency improvement explicitly and set
   `Monthly saving: $0.00` with verdict `ALREADY_OPTIMAL` (or
   `OPPORTUNITY_FOUND` ONLY if a different dimension has positive saving).

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — OPPORTUNITY_FOUND with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: order-enrichment-api
VERDICT: OPPORTUNITY_FOUND
REASON: Python function at 128 MB averaging 5000 ms is CPU-bound (Power
  Tuning U-curve minimum at 512 MB where duration drops to 950 ms).
  Combined with ARM64 migration (20% compute discount), monthly compute
  drops 38.5%. Invocations are 47M/month so the per-invocation saving
  compounds.
RECOMMENDATION:
  Current: 128 MB at 5000 ms avg, x86_64, on-demand
  Proposed: 512 MB at 950 ms avg, arm64, on-demand
  Dimensions changed: memory (Step 1) + architecture (Step 5)
  Dimensions checked: memory → (upsize)  concurrency ✓ (no provisioned)
    duration ✓ (Power Tuning covers)  frequency ✓ (API Gateway, no ESM)
    architecture → (x86 to arm64)  placement ✓ (950 ms well under 15 min)
  Confidence: HIGH — Power Tuning measured the U-curve empirically;
    Python 3.12 fully supports arm64; all deps have arm64 wheels.
ESTIMATED_SAVINGS:
  Current monthly: $498.98
    compute: 47,000,000 × 5.0 × 0.125 × $0.0000166667 = $489.58
    requests: 47,000,000 × $0.0000002 = $9.40
  Projected monthly: $307.07
    compute: 47,000,000 × 0.95 × 0.5 × $0.0000166667 × 0.80 = $297.67
    requests: 47,000,000 × $0.0000002 = $9.40
  Monthly saving: $191.91
    ($498.98 − $307.07 = $191.91 ✓)
  Annual saving: $2,302.92
MIGRATION_STEPS:
  1. Run Power Tuning to confirm the U-curve:
     aws stepfunctions start-execution --state-machine-arn <arn> --input '{...}'
  2. Update memory and architecture together:
     aws lambda update-function-configuration --function-name order-enrichment-api --memory-size 512 --architectures arm64
  3. Publish a version and test via staging alias:
     aws lambda publish-version --function-name order-enrichment-api
  4. Monitor Duration and Errors for 7 days post-change.
CONFIRM: About to update-function-configuration on order-enrichment-api
  (128 MB x86 → 512 MB arm64). Monthly saving $191.91 (38.5%); p95 latency
  improvement ~82%. Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All six dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension has a concrete, savings-bearing or latency-improving recommendation. |
| `OPTIMIZED` | A change was applied and verified this session; metrics confirm the new config lands within SLO. |
| `ALREADY_OPTIMAL` | All dimensions pass (memory at Power Tuning optimum, on ARM64, concurrency right-sized, duration within SLO). |
| `NEED_MORE_INFO` | Data gate failed: metrics absent, window < 14 days, or Compute Optimizer stale with no CloudWatch fallback. |
| `BLOCKED` | Hard precondition prevents evaluation: function State != Active, IAM denies lambda:GetFunction. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `ALREADY_OPTIMAL`, never `OPPORTUNITY_FOUND`. Exception:
latency improvement without cost change is surfaced in REASON, not as
dollar savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend a memory change without Power Tuning or Compute
   Optimizer evidence.** The U-curve is workload-specific; guessing from
   "128 MB is cheapest" produces false positives on CPU-bound workloads.

2. **NEVER enable provisioned concurrency without verifying that cold-start
   latency is a customer-visible problem AND traffic is consistent enough
   to justify idle spend.** Provisioned concurrency for sporadic traffic
   is the #1 Lambda cost waste.

3. **NEVER recommend ARM64 migration without verifying the runtime and
   dependencies are ARM-compatible.** An ARM migration that breaks at
   runtime is worse than no migration.

4. **NEVER increase batch size on an Event Source Mapping without verifying
   the function handles partial batch failures correctly.** Ensure
   `FunctionResponseTypes: ["ReportBatchItemFailures"]` is set for SQS.

5. **NEVER remove provisioned concurrency from a latency-sensitive API
   without warning the operator that cold starts will return.** Removing
   saves money but degrades p99 latency.

Extended anti-patterns in `references/error-handling-and-edge-cases.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Publish a version before changing the alias.** Never point production
  at `$LATEST`.
- **Test the new memory setting before cutover.** Validate via staging
  alias or weighted routing.
- **Verify ARM64 compatibility before architecture migration.** Native
  dependencies may fail at runtime.
- **SnapStart requires versioned aliases.** Ensure alias points at a
  version before enabling.
- **ESM changes are immediate.** Function must handle the new batch size
  without OOM or timeout.
- **Provisioned concurrency removal causes cold starts.** Verify the
  latency SLO tolerates this.
- **Power Tuning invokes the function repeatedly.** Ensure function is
  idempotent and downstream tolerates test load.
- **Bulk-operation limit:** Process at most 5 functions per batch. Sort
  by estimated savings, verify each batch before proceeding. Abort if any
  function shows increased errors or duration post-change.

## Recent AWS features (2024-2026)

Feature list moved to `references/advanced-patterns.md` —
see "Recent AWS features (2024-2026)".

## References

- `references/lambda-pricing-and-power-tuning.md` — pricing tables,
  memory-to-CPU mapping, Power Tuning deployment guide, ARM64 compatibility
  matrix, ESM limits, duration baselines, regional pricing multipliers,
  cost calculation worked examples.
- `references/worked-examples.md` — full worked examples (memory upsize,
  ARM64 migration, provisioned concurrency removal, already-optimal,
  NEED_MORE_INFO, end-to-end walkthrough).
- `references/error-handling-and-edge-cases.md` — CLI/data-source failure
  handling, operational edge cases, container-image functions, extended
  NEVER list, memory decision tree, remediation guidance, production
  edge cases (provisioned concurrency waste, ARM64 incompatibility, ESM
  batch sizing).

## References (load on demand)

- [advanced-patterns.md](references/advanced-patterns.md) — mindset
  principles, Step 0 gotchas, per-step deep dives (duration, batch
  tuning, ARM64, Step Functions), recent AWS features.
- [diagnostic-commands.md](references/diagnostic-commands.md) —
  pre-flight data-gate CLI listing.

## Domain

AWS CloudOps / Lambda Serverless Cost Optimization & FinOps.

## AWS documentation

- **AWS Lambda Developer Guide** — https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- **AWS Lambda pricing** — https://aws.amazon.com/lambda/pricing/
- **AWS Lambda memory and CPU** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-memory.html
- **Lambda SnapStart** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-snapstart.html
- **Lambda provisioned concurrency** — https://docs.aws.amazon.com/lambda/latest/dg/configuration-concurrency.html
- **Lambda event source mappings** — https://docs.aws.amazon.com/lambda/latest/dg/invocation-eventsourcemapping.html
- **AWS Lambda Power Tuning (open source)** — https://github.com/alexcasalboni/aws-lambda-power-tuning
- **AWS Compute Optimizer — Lambda** — https://docs.aws.amazon.com/compute-optimizer/latest/ug/lambda.html
- **CloudWatch Lambda Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Lambda-Insights.html
- **AWS CLI Lambda reference** — https://docs.aws.amazon.com/cli/latest/reference/lambda/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
