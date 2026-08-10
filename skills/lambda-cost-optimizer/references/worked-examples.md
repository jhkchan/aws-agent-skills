# Worked Examples — Lambda Cost Optimizer

Full worked examples covering memory upsizing, ARM64 migration, provisioned
concurrency removal, already-optimal functions, NEED_MORE_INFO, and an
end-to-end optimisation walkthrough. Loaded on demand — kept out of the
main SKILL.md body so the procedure stays scannable.

## Worked example — memory upsize (U-curve optimum higher than current)

```text
TARGET: order-processor-prod
VERDICT: OPPORTUNITY_FOUND
REASON: Node.js function at 128 MB averaging 5200 ms duration is CPU-bound
  (Power Tuning shows U-curve minimum at 1024 MB where duration drops to
  650 ms). The compute cost per invocation drops 20% AND latency improves
  87% — a win on both cost and performance. Invocations are 50M/month,
  so the per-invocation saving compounds.
RECOMMENDATION:
  Current: 128 MB at 5200 ms avg, x86_64, on-demand
  Proposed: 1024 MB at 650 ms avg, x86_64, on-demand
  Dimensions changed: memory (Step 1)
  Confidence: HIGH — Power Tuning measured the U-curve empirically;
    Compute Optimizer cross-check agrees (Overprovisioned on memory,
    recommends 1024 MB).
ESTIMATED_SAVINGS:
  Current monthly: $551.67
    compute: 50,000,000 × 5.2 × (128/1024) × $0.0000166667 = $541.67
    requests: 50,000,000 × $0.0000002 = $10.00
  Projected monthly: $551.67
    compute: 50,000,000 × 0.65 × (1024/1024) × $0.0000166667 = $541.67
    requests: 50,000,000 × $0.0000002 = $10.00
  Monthly saving: $0.00 (cost-neutral — U-curve minimum cost equals current cost)
  BUT: duration drops from 5.2 s to 0.65 s → latency SLO improvement.
  For a cost-only case, see the ARM64 example below.
MIGRATION_STEPS:
  1. Run Power Tuning to confirm the U-curve:
     aws stepfunctions start-execution --state-machine-arn <arn> --input '{...}'
  2. Update the function memory:
     aws lambda update-function-configuration
       --function-name order-processor-prod --memory-size 1024
  3. Publish a version and test via the alias:
     aws lambda publish-version --function-name order-processor-prod
  4. Monitor Duration for 7 days post-change.
CONFIRM: Before updating memory, emit and await:
  "CONFIRM: About to update-function-configuration on order-processor-prod
   (128 MB → 1024 MB). Cost neutral but drops p95 latency from 6.1 s to ~0.8 s.
   Proceed? (yes/no)"
```

**Key nuance:** the cost-optimal memory setting may not be cheaper in pure
dollars — it may be the same cost but dramatically faster. Surface BOTH the
cost delta and the performance delta so the operator can decide based on
their priority.

## Worked example — memory + ARM64 (positive cost saving)

```text
TARGET: image-resizer-prod
VERDICT: OPPORTUNITY_FOUND
REASON: Python image-processing function at 256 MB averaging 3200 ms is
  both sub-optimal on memory (Power Tuning optimum at 2048 MB where
  duration drops to 480 ms) AND on architecture (x86_64 → arm64 is 20%
  cheaper). Combined saving: 4% on compute, 85% latency improvement.
RECOMMENDATION:
  Current: 256 MB at 3200 ms avg, x86_64, on-demand
  Proposed: 2048 MB at 480 ms avg, arm64, on-demand
  Dimensions changed: memory (Step 1) + architecture (Step 5)
  Confidence: HIGH — Power Tuning confirms memory optimum; Pillow
    (image library) has arm64 wheels; Compute Optimizer agrees.
ESTIMATED_SAVINGS:
  Current monthly: $270.67
    compute: 20M × 3.2 × 0.25 × $0.0000166667 = $266.67
    requests: 20M × $0.0000002 = $4.00
  Projected monthly: $260.00
    compute: 20M × 0.48 × 2.0 × $0.0000166667 × 0.80 (ARM) = $256.00
    requests: 20M × $0.0000002 = $4.00
  Monthly saving: $10.67 (4% on compute)
  Annual saving: $128.00
  Latency improvement: 85% (3.2 s → 0.48 s)
MIGRATION_STEPS:
  1. Update architecture to arm64 and memory to 2048:
     aws lambda update-function-configuration
       --function-name image-resizer-prod
       --memory-size 2048 --architectures arm64
  2. Publish and test:
     aws lambda publish-version --function-name image-resizer-prod
  3. Verify Pillow works on arm64 via a test invocation.
  4. Monitor Duration and Errors for 7 days post-change.
CONFIRM: Before updating, emit and await:
  "CONFIRM: About to update-function-configuration on image-resizer-prod
   (256 MB x86 → 2048 MB arm64). Cost saving $10.67/mo (4%); latency
   improvement 85% (3.2 s → 0.48 s). Proceed? (yes/no)"
```

## Worked example — provisioned concurrency removal (sporadic traffic)

```text
TARGET: report-generator-fn
VERDICT: OPPORTUNITY_FOUND
REASON: Function has 5 provisioned concurrency configured but receives
  < 1 invocation/minute on average (sporadic batch report requests).
  99.4% of provisioned execution time is idle. Removing provisioned
  concurrency eliminates $209.51/month of idle compute.
RECOMMENDATION:
  Current: 1024 MB, 5 provisioned concurrency, ~0.6 invocations/min
  Proposed: 1024 MB, on-demand (no provisioned concurrency)
  Dimensions changed: concurrency (Step 2)
  Confidence: HIGH — 30-day ConcurrentExecutions shows p99 = 2, mean =
    0.6; provisioned (5) is 2.5× over p99. Cold starts acceptable for
    batch reports (latency not customer-facing).
ESTIMATED_SAVINGS:
  Current monthly: $210.38
    provisioned compute: 5 × 1 GB × 730h × 3600s × $0.000015 = $196.20
    provisioned requests: 25,920 invocations × $0.00005 = $1.30
    on-demand overflow: negligible
    total: ~$210.38/month
  Projected monthly: $0.87
    on-demand compute: 25,920 × 2.0s × 1.0 GB × $0.0000166667 = $0.86
    on-demand requests: 25,920 × $0.0000002 = $0.005
  Monthly saving: $209.51
  Annual saving: $2,514.12
MIGRATION_STEPS:
  1. Remove provisioned concurrency:
     aws lambda delete-provisioned-concurrency-config
       --function-name report-generator-fn --qualifier prod
  2. Verify cold starts are acceptable (first invocation of each report
     may take 1-2 s extra).
  3. Monitor Invocations and Duration for 7 days post-change.
CONFIRM: Before removing, emit and await:
  "CONFIRM: About to delete-provisioned-concurrency-config on
   report-generator-fn (alias prod). Cold starts on sporadic invocations
   (~2 s init). Saving $209.51/mo. Proceed? (yes/no)"
```

## Worked example — already optimal

```text
TARGET: webhook-receiver-prod
VERDICT: ALREADY_OPTIMAL
REASON: Node.js function at 512 MB averaging 180 ms duration with 10M
  invocations/month is at Power Tuning U-curve minimum, already on arm64,
  on-demand (no provisioned concurrency idle), no ESM (API Gateway
  trigger), duration well within SLO. No optimization dimension has a
  positive saving.
RECOMMENDATION:
  Current: 512 MB at 180 ms, arm64, on-demand — no change
  Dimensions checked: memory ✓, concurrency ✓, duration ✓, architecture ✓
  Confidence: HIGH — Power Tuning run 2026-07-15 confirms 512 MB optimum;
    Compute Optimizer finding Optimized; no duration waste.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Re-evaluate if invocation pattern changes or at
    quarterly FinOps review.
```

## Worked example — NEED_MORE_INFO (metrics absent)

```text
TARGET: legacy-processor-fn
VERDICT: NEED_MORE_INFO
REASON: Duration and Invocations metrics are absent for the requested
  30-day window. The function may be dormant, misconfigured, or the IAM
  role may deny cloudwatch:GetMetricStatistics. Cannot make a cost
  optimization recommendation without baseline metrics.
RECOMMENDATION:
  Current: 256 MB at unknown duration — pending data
  Proposed: pending data
  Confidence: LOW — no metrics to evaluate.
ESTIMATED_SAVINGS:
  Monthly: $0 (cannot quantify without baseline)
MIGRATION_STEPS:
  1. Verify the function is wired to a trigger and receiving invocations:
     aws lambda list-event-source-mappings --function-name legacy-processor-fn
  2. Verify IAM permissions for CloudWatch:
     aws iam get-role-policy --role-name <role> --policy-name <policy>
  3. Wait 14-30 days for representative observation.
  4. Re-evaluate with Duration + Invocations data.
  Do NOT optimize based on assumed metrics.
```

## End-to-end optimisation walkthrough ($500/month function)

This example walks through the complete workflow: analyse metrics,
identify waste via the decision tree, run Power Tuning, calculate
savings, and provide migration steps.

**Function profile:**
- Function: `order-enrichment-api`
- Runtime: Python 3.12
- Memory: 128 MB
- Architecture: x86_64
- Trigger: API Gateway (latency-sensitive)
- Duration: 5000 ms avg, 6200 ms p95
- Invocations: 47,000,000/month
- Errors: 0.01% (within SLO)
- Region: us-east-1, On-Demand pricing

**Step 1 — Analyse current cost:**
```
Current compute: 47M × 5.0 s × (128/1024) GB × $0.0000166667
                = $489.58/month
Current requests: 47M × $0.0000002 = $9.40/month
Current total: $498.98/month ($5,987.76/year)
```

**Step 2 — Route through the memory decision tree:**
- Invocations > 1M/day? YES (47M/month = 1.57M/day) → high-impact candidate.
- Duration > 3 s AND Memory < 512 MB? YES (5.0 s, 128 MB) → CPU-bound at
  low memory. Expect Power Tuning to recommend an upsize.

**Step 3 — Run Power Tuning:**
Results across [128, 256, 512, 1024, 2048, 3008] MB:
- 128 MB: 5000 ms, $0.00001042/invocation
- 256 MB: 2800 ms, $0.00001167/invocation
- 512 MB: 950 ms, $0.00000792/invocation — U-curve minimum (cheapest)
- 1024 MB: 520 ms, $0.00000867/invocation
- 2048 MB: 380 ms, $0.00001267/invocation
- 3008 MB: 350 ms, $0.00001751/invocation

`cheapest` = 512 MB at $0.00000792/invocation.

**Step 4 — Cross-check ARM64 compatibility:**
Python 3.12 with pure-Python dependencies (requests, psycopg2-binary with
arm64 wheels) → ARM64 is LOW risk. Apply simultaneously with memory change.

**Step 5 — Calculate projected cost:**
```
Projected compute (512 MB, 950 ms, ARM64):
  47M × 0.95 s × (512/1024) GB × $0.0000166667 × 0.80 (ARM 20% off)
  = $297.67/month

Projected requests: 47M × $0.0000002 = $9.40/month (unchanged)
Projected total: $307.07/month ($3,684.84/year)
```

**Step 6 — Savings summary:**
```
Monthly saving: $498.98 - $307.07 = $191.91 (38.5%)
Annual saving: $2,302.92
Latency improvement: p95 drops from 6200 ms to ~1100 ms (82% reduction)
```

**Step 7 — Emit the output block:**
```text
TARGET: order-enrichment-api
VERDICT: OPPORTUNITY_FOUND
REASON: Python function at 128 MB averaging 5000 ms is CPU-bound (Power
  Tuning U-curve minimum at 512 MB where duration drops to 950 ms).
  Combined with ARM64 migration, compute cost drops 38.5%. The function
  is invoked 47M times/month, so the per-invocation saving compounds to
  $191.91/month. p95 latency also drops 82% (6200 ms to ~1100 ms).
RECOMMENDATION:
  Current: 128 MB at 5000 ms avg, x86_64, on-demand
  Proposed: 512 MB at 950 ms avg, arm64, on-demand
  Dimensions changed: memory (Step 1) + architecture (Step 5)
  Confidence: HIGH — Power Tuning measured the U-curve empirically;
    Python 3.12 fully supports arm64; all dependencies have arm64 wheels.
ESTIMATED_SAVINGS:
  Current monthly: $498.98
    compute: 47,000,000 x 5.0 x 0.125 x $0.0000166667 = $489.58
    requests: 47,000,000 x $0.0000002 = $9.40
  Projected monthly: $307.07
    compute: 47,000,000 x 0.95 x 0.5 x $0.0000166667 x 0.80 = $297.67
    requests: 47,000,000 x $0.0000002 = $9.40
  Monthly saving: $191.91 (38.5%)
  Annual saving: $2,302.92
MIGRATION_STEPS:
  1. Run Power Tuning to confirm the U-curve:
     aws stepfunctions start-execution --state-machine-arn <arn>
       --input '{"lambda":{...},"power":{"values":[128,256,512,1024,2048,3008]}}'
  2. Verify ARM64 dependency compatibility:
     pip install --platform aarch64 --only-binary=:all: requests psycopg2-binary
  3. Update memory and architecture together:
     aws lambda update-function-configuration
       --function-name order-enrichment-api
       --memory-size 512 --architectures arm64
  4. Publish a version and test via staging alias.
  5. Verify p95 latency and error rate for 7 days via CloudWatch.
  6. Cutover production alias.
CONFIRM: About to update-function-configuration on order-enrichment-api
  (128 MB x86 to 512 MB arm64). Monthly saving $191.91 (38.5%); p95 latency
  improvement 82%. Proceed? (yes/no)
```
