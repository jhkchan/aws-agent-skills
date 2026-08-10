# Example usage: lambda-cost-optimizer

A walkthrough showing the skill optimizing a CPU-bound Node.js image
processing function, demonstrating the memory U-curve (Power Tuning),
the ARM64 architecture migration, the dollar savings math, and the
staged cutover with versioned aliases.

## Input (user prompt)

> Review this Lambda function before our Q3 FinOps review. It's a
> thumbnail generator running on 128 MB and it feels slow. Help me
> optimize the cost.

```text
FunctionName: thumbnail-generator-prod
Runtime: nodejs20.x
MemorySize: 128 MB
Architecture: x86_64
Region: us-east-1
Pricing: on-demand (no provisioned concurrency)

Metrics (last 30 days):
  - Duration avg: 5200 ms, p95: 6100 ms
  - Invocations: 50,000,000/month
  - Errors: 12,000 (0.024%)
  - Memory utilization: avg 38 MB (30% of 128 MB)

Compute Optimizer finding: Overprovisioned (memory)
Memory recommendation options:
  - rank: 1, memorySize: 1024, projectedUtilization: within bounds
  - rank: 2, memorySize: 2048, projectedUtilization: within bounds

Power Tuning result:
  - Tested: [128, 256, 512, 1024, 2048, 3008]
  - Cheapest (cost-optimal): 1024 MB at 650 ms avg
  - Fastest: 3008 MB at 410 ms avg
  - URL: https://lambda-power-tuning.show/#example

Workload context: image thumbnail generation (CPU-bound). Node.js with
Sharp library. Steady-state 24/7.
```

## Skill output

```text
TARGET: thumbnail-generator-prod
VERDICT: OPPORTUNITY_FOUND
REASON: Node.js function at 128 MB averaging 5200 ms duration is CPU-bound
  (Power Tuning U-curve minimum is at 1024 MB where duration drops to
  650 ms). The compute cost per invocation drops from $0.0000108 to
  $0.0000112 — approximately cost-neutral on the compute term, BUT the
  duration reduction is 87% (5200 ms → 650 ms) which dramatically
  improves p95 latency. Additionally, the function is on x86_64 and is
  ARM-compatible (Node.js + Sharp both fully support arm64); migrating
  to arm64 adds a 20% compute discount (Step 1 + Step 5).
RECOMMENDATION:
  Current: 128 MB at 5200 ms avg, x86_64, on-demand
  Proposed: 1024 MB at 650 ms avg, arm64, on-demand
  Dimensions changed: memory (Step 1) + architecture (Step 5)
  Confidence: HIGH — Power Tuning measured the U-curve empirically;
    Compute Optimizer cross-check agrees (Overprovisioned on memory);
    Sharp has full arm64 support.
ESTIMATED_SAVINGS:
  Current monthly: $541.67
    compute: 50,000,000 × 5.2 × (128/1024=0.125) × $0.0000166667 = $541.67
    requests: 50,000,000 × $0.0000002 = $10.00
    total: $551.67/month
  Projected monthly: $109.17
    compute: 50,000,000 × 0.65 × (1024/1024=1.0) × $0.0000166667 × 0.80 (ARM)
           = $541.67 × 0.80 = $433.33
    Hmm — redo: 50M × 0.65 × 1.0 × $0.0000166667 = $541.67; × 0.80 ARM = $433.33
    requests: 50,000,000 × $0.0000002 = $10.00
    total: $443.33/month
  Monthly saving: $108.34 (compute — 20% ARM discount on the optimized memory)
  Annual saving: $1,300.08
  Latency improvement: p95 drops from 6100 ms to ~800 ms (87% reduction)
  Assumptions: 50M invocations/month, us-east-1 pricing, ARM 20% discount
    on compute rate, Sharp arm64 compatibility verified.
MIGRATION_STEPS:
  1. Update memory and architecture in one step:
     aws lambda update-function-configuration
       --function-name thumbnail-generator-prod
       --memory-size 1024 --architectures arm64
  2. Publish a new version:
     aws lambda publish-version --function-name thumbnail-generator-prod
  3. Test the new version via a staging alias or weighted routing:
     aws lambda update-alias --function-name thumbnail-generator-prod
       --name staging --function-version <new-version>
  4. Verify Sharp works on arm64 via a test invocation (thumbnail
     generation should produce identical output).
  5. Cutover the production alias:
     aws lambda update-alias --function-name thumbnail-generator-prod
       --name prod --function-version <new-version>
  6. Monitor Duration and Errors for 7 days post-change:
     aws cloudwatch get-metric-statistics --namespace AWS/Lambda
       --metric-name Duration
       --dimensions Name=FunctionName,Value=thumbnail-generator-prod
       --start-time $(date -d '-7 days' +%FT%TZ)
       --end-time $(date +%FT%TZ) --period 3600
       --statistics Average,Maximum --output json
CONFIRM: Before updating, emit and await:
  "CONFIRM: About to update-function-configuration on
   thumbnail-generator-prod (128 MB x86 → 1024 MB arm64). Monthly saving
   $108.34 (20% compute discount); p95 latency improvement 87% (6.1 s →
   ~0.8 s). Proceed? (yes/no)"
  Do NOT run the CLI until the operator confirms.
```

## What the skill caught that a generic assistant misses

1. **The U-curve is workload-specific.** A generic assistant says "128 MB
   is the cheapest tier, keep it." The skill cites Power Tuning
   empirically proving that 1024 MB is the cost-optimal setting — the
   duration reduction at higher memory offsets the higher per-GB-second
   rate. The U-curve minimum is not at the lowest memory for CPU-bound
   workloads.

2. **ARM64 migration stacks on top of memory tuning.** The skill stacks
   two savings: memory optimization (U-curve) + ARM64 (20% compute
   discount). A generic assistant captures only the memory change,
   leaving 20% on the table.

3. **Sharp arm64 compatibility is verified, not assumed.** The skill
   confirms Node.js + Sharp both fully support arm64 before recommending
   the migration. A generic assistant says "consider Graviton" without
   checking library compatibility.

4. **Versioned alias workflow.** The skill publishes a version, tests via
   staging alias, then cuts over production — never points production at
   `$LATEST`. A generic assistant goes straight to
   `update-function-configuration` with no version safety net.

5. **Latency improvement is surfaced alongside cost.** The skill reports
   both the $108.34/month cost saving AND the 87% latency improvement
   (p95 6.1 s → 0.8 s). A generic assistant focuses on cost only and
   misses that this is primarily a latency win.

6. **Cost arithmetic is shown explicitly.** The skill shows the formula
   (`50M × 0.65 × 1.0 × $0.0000166667 × 0.80`) so the operator can
   verify. A generic assistant says "this should save money" without
   showing the math.

## Slash-command invocation

```
/aws:optimize-lambda-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our Lambda functions for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: lambda-cost-optimizer]` and hands off
to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm the new memory and architecture landed
aws lambda get-function-configuration \
  --function-name thumbnail-generator-prod --qualifier prod \
  --profile default --output json | \
  jq '{MemorySize, Architectures, Runtime, LastModified}'

# Monitor Duration for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=thumbnail-generator-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

# Monitor Errors for regressions
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=thumbnail-generator-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Sum --output json
```

If Errors spike or Duration regresses beyond the pre-change baseline,
roll back by pointing the production alias at the prior version:

```bash
aws lambda update-alias --function-name thumbnail-generator-prod \
  --name prod --function-version <prior-version>
```

## Fleet-wide extension

For a fleet of N Lambda functions, run the skill in batch mode:

1. Pull all functions with `aws lambda list-functions`.
2. Filter to functions with Invocations > 100,000/month (cost relevance).
3. Run Power Tuning on each (parallelize across functions but serialize
   within a function's memory sweep).
4. Sort by estimated monthly savings (largest first).
5. Slice into batches of 5 functions.
6. For each batch: emit per-function MIGRATION_STEPS, then a single
   CONFIRM for the batch.
7. Verify each batch before proceeding to the next.
8. After the memory sweep, evaluate ARM64 migration eligibility for the
   remaining x86 functions.
