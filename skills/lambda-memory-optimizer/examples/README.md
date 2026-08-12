# Example usage: lambda-memory-optimizer

A walkthrough showing the skill optimizing a CPU-bound Python function's
memory configuration, demonstrating the U-curve (Power Tuning), the cost-
vs-latency tradeoff (cheapest vs fastest), the ARM64 re-tuning, and the
dollar savings math with versioned alias cutover.

## Input (user prompt)

> Review this Lambda function before our Q3 FinOps review. It's an image
> enrichment function at 128 MB and it's slow. Help me find the right
> memory setting.

```text
FunctionName: image-enrichment-prod
Runtime: python3.12
MemorySize: 128 MB
Architecture: x86_64
Region: us-east-1
Pricing: on-demand (no provisioned concurrency)

Metrics (last 30 days):
  - Duration avg: 5000 ms, p95: 6200 ms
  - Invocations: 47,000,000/month
  - Errors: 45 (0.000096%)
  - Memory utilization: avg 38 MB (30% of 128 MB)
  - InitDuration: 200 ms (cold start, negligible)

Lambda Insights:
  - memory_used: avg 38 MB, peak 52 MB
  - cpu_total_time: avg 4800 ms (96% of Duration — CPU-bound)

Compute Optimizer finding: Overprovisioned (memory)
Memory recommendation options:
  - rank: 1, memorySize: 512, projectedUtilization: within bounds
  - rank: 2, memorySize: 1024, projectedUtilization: within bounds

Power Tuning result:
  - Tested: [128, 256, 512, 1024, 2048, 3008]
  - Cheapest (cost-optimal): 512 MB at 950 ms avg
  - Fastest: 3008 MB at 410 ms avg
  - URL: https://lambda-power-tuning.show/#example

Workload context: image enrichment (CPU-bound). Python with Pillow
library. Steady-state 24/7 via API Gateway.
```

## Skill output

```text
TARGET: image-enrichment-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Python function at 128 MB averaging 5000 ms is CPU-bound (Power
  Tuning U-curve minimum at 512 MB where duration drops to 950 ms).
  Cost per invocation drops 20% at the higher memory. Combined with
  ARM64 migration (20% compute discount), monthly compute drops 38.5%.
  Power Tuning also surfaces fastest at 3008 MB (410 ms) for latency-
  critical routing — operator choice.
RECOMMENDATION:
  Current: 128 MB at 5000 ms avg, x86_64, on-demand, InitDuration 200 ms
  Proposed: 512 MB at 950 ms avg, arm64, on-demand, InitDuration 200 ms
  Dimensions changed: memory (Step 1) + architecture (Step 6)
  Dimensions checked: memory → (upsize)  pc_memory ✓ (no PC)
    init ✓ (200 ms)  efs_container_layers ✓ (zip, no EFS)
    tmp ✓ (no /tmp overflow)  architecture → (x86 to arm64)
  Confidence: HIGH — Power Tuning measured the U-curve empirically;
    Compute Optimizer cross-check agrees (Overprovisioned on memory);
    Pillow has full arm64 wheel support.
ESTIMATED_SAVINGS:
  Current monthly: $498.98
    compute: 47M × 5.0 × 0.125 × $0.0000166667 = $489.58
    requests: 47M × $0.0000002 = $9.40
  Projected monthly: $307.07
    compute: 47M × 0.95 × 0.5 × $0.0000166667 × 0.80 (ARM) = $297.67
    requests: 47M × $0.0000002 = $9.40
  Monthly saving: $191.91
    ($498.98 − $307.07 = $191.91 ✓)
  Annual saving: $2,302.92
  Latency delta: p95 drops from 6200 ms to ~1100 ms (82% reduction)
  Cost-vs-latency note: fastest option (3008 MB, 410 ms) costs
    $0.0000205/invocation — 2.5x more expensive than cheapest. Cheapest
    is recommended unless p95 < 500 ms is a hard SLO.
MIGRATION_STEPS:
  1. Update memory and architecture together:
     aws lambda update-function-configuration \
       --function-name image-enrichment-prod --memory-size 512 --architectures arm64
  2. Publish a new version:
     aws lambda publish-version --function-name image-enrichment-prod
  3. Test the new version via a staging alias or weighted routing:
     aws lambda update-alias --function-name image-enrichment-prod \
       --name staging --function-version <new-version>
  4. Verify Pillow works on arm64 via a test invocation.
  5. Cutover the production alias:
     aws lambda update-alias --function-name image-enrichment-prod \
       --name prod --function-version <new-version>
  6. Monitor Duration and Errors for 7 days post-change.
CONFIRM: Before updating, emit and await:
  "CONFIRM: About to update-function-configuration on image-enrichment-prod
   (128 MB x86 → 512 MB arm64). Monthly saving $191.91 (38.5%); p95 latency
   improvement 82% (6.2 s → ~1.1 s). Proceed? (yes/no)"
  Do NOT run the CLI until the operator confirms.
```

## What the skill caught that a generic assistant misses

1. **The U-curve is workload-specific.** A generic assistant says "128
   MB is the cheapest tier, keep it." The skill cites Power Tuning
   empirically proving that 512 MB is the cost-optimal setting — the
   duration reduction at higher memory offsets the higher per-GB-second
   rate. The cost minimum is NOT at the lowest memory for CPU-bound
   workloads.

2. **Cost-optimal vs latency-optimal is surfaced explicitly.** The
   skill presents both `cheapest` (512 MB, 950 ms, $0.0000083) and
   `fastest` (3008 MB, 410 ms, $0.0000205). A generic assistant
   recommends one without surfacing the tradeoff. The operator chooses
   based on FinOps vs UX priority.

3. **ARM64 migration stacks on top of memory tuning.** The skill stacks
   two savings: memory optimization (U-curve) + ARM64 (20% compute
   discount). A generic assistant captures only the memory change,
   leaving 20% on the table.

4. **Pillow arm64 compatibility is verified, not assumed.** The skill
   confirms Pillow has arm64 wheels before recommending the migration.
   A generic assistant says "consider Graviton" without checking
   library compatibility.

5. **Versioned alias workflow.** The skill publishes a version, tests
   via staging alias, then cuts over production — never points
   production at `$LATEST`. A generic assistant goes straight to
   `update-function-configuration` with no version safety net.

6. **CPU-bound classification from Lambda Insights.** The skill uses
   `cpu_total_time / Duration = 96%` to classify the function as CPU-
   bound, which explains why the U-curve has a step-function at higher
   memory. A generic assistant never classifies the workload.

## Slash-command invocation

```
/aws:optimize-lambda-memory
```

Or via the orchestrator:

```
/aws:pipeline
You: "tune our Lambda memory configurations for the Q3 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: lambda-memory-optimizer]` and hands
off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm the new memory and architecture landed
aws lambda get-function-configuration \
  --function-name image-enrichment-prod --qualifier prod \
  --profile default --output json | \
  jq '{MemorySize, Architectures, Runtime, LastModified}'

# Monitor Duration for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=image-enrichment-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

# Monitor Errors for regressions
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=image-enrichment-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Sum --output json

# Verify memory_used peak is within headroom at the new MemorySize
aws cloudwatch get-metric-statistics --namespace LambdaInsights \
  --metric-name memory_used \
  --dimensions Name=function_arn,Value=arn:aws:lambda:us-east-1:<acct>:function:image-enrichment-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) --end-time $(date +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json
```

If Errors spike or Duration regresses beyond the pre-change baseline,
roll back by pointing the production alias at the prior version:

```bash
aws lambda update-alias --function-name image-enrichment-prod \
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
   remaining x86 functions. Re-run Power Tuning after each migration.
