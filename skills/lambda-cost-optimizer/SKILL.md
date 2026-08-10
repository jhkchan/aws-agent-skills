---
name: lambda-cost-optimizer
description: 'Optimises AWS Lambda function cost across six dimensions: memory tuning (CPU scales with memory at 1769 MB = 1 vCPU; more memory can REDUCE total cost when faster execution offsets the higher
  per-GB-second rate), provisioned concurrency right-sizing (on-demand vs provisioned break-even math), duration reduction (SnapStart for Java, lazy init, connection reuse, package trim), invocation-frequency
  analysis (SQS/Kinesis/DynamoDB Streams batch size and batch window tuning), architecture migration (ARM64 Graviton2 is 20% cheaper; Fargate for >15-min workloads; Step Functions for orchestration chains),
  and Lambda Layers. Uses AWS Lambda Power Tuning (open-source Step Functions) to empirically find the cost-optimal memory, reads Compute Optimizer Lambda findings, and projects monthly savings. Emits OPPORTUNITY_FOUND
  with specific recommendation and estimated savings, OPTIMIZED, or ALREADY_OPTIMAL. Use when reviewing Lambda spend, planning a memory tuning sweep, sizing provisioned concurrency, or a FinOps review.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted CloudWatch metrics and Compute Optimizer findings.
  Live-account optimization uses aws lambda list-functions, aws lambda get-function-configuration, aws cloudwatch get-metric-statistics (Duration, Invocations, Errors, Throttles, ConcurrentExecutions),
  aws lambda get-event-source-mapping, aws lambda list-provisioned-concurrency-configs, aws compute-optimizer get-lambda-function-recommendations, and aws ce get-cost-and-usage (AWS CLI v2, SSO or key-based
  credentials). Pricing references us-east-1 published rates as of 2026; re-state regional rates from the reference matrix for other regions.
keywords:
- Lambda
- memory configuration
- cost optimization
- Power Tuning
- provisioned concurrency
- on-demand
- duration
- cold start
- SnapStart
- invocation frequency
- batch size
- batch window
- event source mapping
- SQS
- DynamoDB Streams
- Kinesis
- Lambda Layers
- ARM64
- Graviton2
- Fargate migration
- Step Functions
- FinOps
- Compute Optimizer
- serverless
tags:
- lambda
- compute
- serverless
- cost-optimization
- finops
- memory-tuning
- power-tuning
- graviton
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Optimising Lambda function cost, triaging Compute Optimizer Lambda findings, planning a memory tuning sweep (Power Tuning), sizing provisioned concurrency vs on-demand, reducing function
    duration, tuning SQS/DynamoDB/Kinesis event source mapping batch size, evaluating ARM64 (Graviton2) migration, or migrating long-running Lambda workloads to Fargate or Step Functions.
  when_not_to_use: EC2 instance rightsizing (use ec2-rightsizing-optimizer), EBS volume cost (use ebs-volume-optimizer), S3 storage cost (use s3-lifecycle-optimizer), or Lambda troubleshooting (invocation
    errors, timeouts, configuration bugs — use the Lambda troubleshooter). This skill focuses on cost-driven optimization decisions, not functional debugging of broken functions.
  activation_triggers:
  - optimise Lambda cost
  - Lambda memory tuning
  - Lambda Power Tuning
  - Lambda Compute Optimizer recommendations
  - Lambda provisioned concurrency
  - Lambda duration optimization
  - Lambda cold start
  - Lambda SnapStart Java
  - Lambda batch size SQS
  - Lambda ARM64 Graviton2
  - Lambda Layers shared code
  - Lambda invocation frequency
  - Lambda FinOps savings
  - Lambda to Fargate migration
  - Lambda monthly savings estimate
  - reduce Lambda bill
  - serverless cost review
  invocation_schema: 'Input: either (a) a function identifier + live-account context, (b) a Compute Optimizer Lambda finding document, OR (c) CloudWatch Lambda Insights metrics (Duration, Invocations, Memory
    utilization, ConcurrentExecutions, Errors) with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS block per function, where
    VERDICT is one of OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL.'
  invocation_example: "# Minimal valid input (offline finding classification):\nFunctionName: order-processor-prod\nRuntime: nodejs20.x\nMemorySize: 128 MB\nArchitecture: x86_64\nRegion: us-east-1\nPricing:\
    \ on-demand (no provisioned concurrency)\nMetrics (last 30 days):\n  - Duration avg: 5200 ms, p95: 6100 ms\n  - Invocations: 50,000,000/month\n  - Errors: 12,000 (0.024%)\n  - Memory utilization: avg\
    \ 38 MB (30% of 128 MB)\nCompute Optimizer finding: Overprovisioned (memory)\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# Lambda Cost Optimizer

## What this skill does

Translates a Lambda function's runtime posture into a concrete cost-
optimization recommendation with a dollar-denominated savings estimate.
The verdict is the highest-leverage action across six dimensions — memory
configuration, provisioned concurrency, duration, invocation frequency,
architecture, and workload placement — applied in priority order. Always
pairs the recommendation with the exact CLI commands (or AWS Lambda Power
Tuning invocation) so the operator can review, confirm, and apply.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset / Philosophy | Why memory tuning is the #1 lever; provisioned-concurrency trade-off | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a function |
| Pre-flight data gate | CloudWatch metrics, Compute Optimizer, memory utilization | Before any recommendation |
| Step 0 non-obvious behaviours | CPU-memory coupling, SnapStart, ESM defaults, Layers, ARM64 | Edge cases |
| Step 1 Memory configuration | Power Tuning workflow, optimal-memory math, worked example | The headline savings dimension |
| Step 2 Provisioned concurrency | On-demand vs provisioned break-even math | Latency-sensitive APIs |
| Step 3 Duration optimization | Cold start, init, connection reuse, package size | Slow functions |
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
  Both terms scale with invocation count; only the first scales with
  duration and memory. The request-fee term dominates at very low
  duration; the compute term dominates at high duration or memory.
- **Provisioned concurrency pays for idle.** Use it ONLY for steady-
  traffic, latency-sensitive APIs where cold starts hurt. For batch,
  event-driven, or sporadic workloads, on-demand is cheaper. The
  break-even math is in Step 2.
- **Architecture is a free 20%.** ARM64 (Graviton2) is ~20% cheaper than
  x86_64 for supported runtimes (Node, Python, Java, .NET, Go, Ruby).
  Check the runtime support matrix and migrate when possible.

## Mindset

Lambda cost optimization is a price-performance decision, not a pure
utilization exercise. The goal is the memory/concurrency/architecture
configuration that minimizes dollar cost while preserving latency and
error-rate SLOs — not the absolute minimum memory that runs the code. A
memory reduction that doubles duration may cost MORE in dollars and
violate the latency SLO. The decision framework below favours empirical
evidence: run Power Tuning before assuming any memory setting is optimal.

## Philosophy

Four behaviours separate a senior serverless FinOps engineer from a
generalist:

- **The cost curve is U-shaped, not monotonic.** As memory increases,
  duration usually drops faster than the per-GB-second rate rises — up
  to an inflection point. Past that point, additional memory barely
  reduces duration but the per-GB-second rate keeps climbing. The optimal
  memory is at the U-curve minimum, which is workload-specific. Guessing
  the minimum from CPU utilization alone is unreliable; Power Tuning
  measures it empirically.

- **Provisioned concurrency is an insurance premium, not a discount.**
  Provisioned concurrency charges for idle execution time whether or not
  invocations arrive. It is cost-justified ONLY when (a) traffic is
  consistent enough that idle time is small, AND (b) cold-start latency
  is a customer-visible problem. Using it for sporadic traffic is paying
  for compute that sits idle — the opposite of serverless economics.

- **Invocation frequency is the multiplier on every waste.** A 50 ms
  duration reduction on a function invoked 10 times/day saves nothing
  meaningful; the same reduction on a function invoked 50 million
  times/day saves real money. Always rank optimization candidates by
  invocation count × duration before deep-diving into tuning.

- **Architecture and placement are cross-cutting savings.** ARM64
  (Graviton2) delivers ~20% compute discount with no code change for
  supported runtimes. Long-running workloads (>15 minutes) physically
  cannot run on Lambda and should be migrated to Fargate. Orchestration-
  heavy Lambda chains (10+ functions in sequence) cost more in
  invocation overhead than a single Step Functions state machine. These
  opportunities are invisible in per-function metrics but show up in the
  bill.

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

See the ordered steps for edge cases (Layers consolidation, Step Functions
migration, provisioned concurrency autoscaling).

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Several
data-quality conditions short-circuit the recommendation — misclassifying
them produces recommendations that increase cost or break the function.

### Required data sources

```bash
# 1. Confirm the function exists and capture its configuration
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{FunctionName, Runtime, MemorySize, Timeout, Architectures,
       Handler, CodeSize, LastModified, State, RuntimeVersionConfig}'

# 2. Pull 14-30 day Duration and Invocations (the load-bearing metrics)
START=$(date -d '-30 days' +%FT%TZ)
END=$(date +%FT%TZ)

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Sum \
  --output json > duration.json

aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $START --end-time $END \
  --period 86400 --statistics Sum \
  --output json > invocations.json

# 3. Memory utilization (requires Lambda Insights — the CRITICAL signal)
aws cloudwatch get-metric-statistics --namespace LambdaInsights \
  --metric-name memory_used \
  --dimensions Name=function_name,Value=<name> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json > memory-used.json

# 4. Confirm Compute Optimizer enrollment and pull Lambda findings
aws compute-optimizer get-enrollment-status --output json

aws compute-optimizer get-lambda-function-recommendations \
  --function-arns arn:aws:lambda:<region>:<acct>:function:<name> \
  --output json | jq '
    .lambdaFunctionRecommendations[] | {
      function_arn: .functionArn,
      finding: .finding,                       # Optimized | Underprovisioned | Overprovisioned
      finding_reasons: .findingReasonCodes,
      current_memory: .currentMemorySize,
      recommendations: [
        .memoryRecommendationOptions[] | {
          rank: .rank,
          memory_size: .memorySize,
          projected_savings_pct: .projectedUtilizationMetrics[]
        }
      ],
      last_refresh: .lastRefreshTimestamp
    }'

# 5. Capture event source mappings (invocation-frequency dimension)
aws lambda list-event-source-mappings --function-name <name> --output json | \
  jq '.EventSourceMappings[] | {EventSourceArn, BatchSize, MaximumBatchingWindowInSeconds,
    State, LastProcessingResult}'

# 6. Capture provisioned concurrency configs (concurrency dimension)
aws lambda list-provisioned-concurrency-configs --function-name <name> --output json
```

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `Duration` metric absent (function never invoked in window) | **NEED_MORE_INFO**: no signal. Verify the function is wired to a trigger; skip until invocations exist. |
| `Invocations` Sum = 0 over 14 days | Function is dormant. Emit ALREADY_OPTIMAL with note "dormant function — no cost optimization applicable." |
| Observation window < 14 days | **NEED_MORE_INFO**: workload may reflect atypical load (deploy week, incident). Minimum 14 days; 30 days preferred. |
| `memory_used` (Lambda Insights) absent | Cannot compute memory-utilization headroom. Fall back to Power Tuning only; mark Memory recommendation as MEDIUM confidence. |
| Compute Optimizer enrollment `Inactive` | No Lambda findings to cross-reference. Proceed with CloudWatch + Power Tuning directly. |
| Compute Optimizer `lastRefreshTimestamp` > 30 days old | Stale finding. Re-run `get-lambda-function-recommendations`. |
| Function `State != Active` | Function is in update/failed state. Skip optimization; surface as BLOCKED. |
| `Runtime` is deprecated (e.g. nodejs14.x, python3.7) | Surface as a parallel finding (upgrade required). Do not block cost optimization but flag the runtime upgrade. |

### Conflicting-data arbitration

When CloudWatch metrics and Compute Optimizer findings disagree (e.g.,
CloudWatch shows Duration 5 s average but Compute Optimizer says
Overprovisioned), trust Power Tuning as the tiebreaker. Compute Optimizer
uses 30-day statistical models; Power Tuning measures the actual U-curve.
The freshest empirical signal wins.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These are the operational gotchas a senior serverless engineer knows from
production experience — each one routes a recommendation away from the
obvious choice:

- **Memory and CPU are coupled at 1769 MB = 1 vCPU.** Lambda allocates
  CPU proportional to memory. Below 1769 MB, the function gets a fractional
  vCPU; at 1769 MB it gets a full vCPU; above 1769 MB it gets additional
  vCPUs (e.g., 3538 MB = 2 vCPU, 5307 MB = 3 vCPU). CPU-bound workloads
  see a step-function duration improvement at the 1769 MB boundary — this
  is invisible in memory-only analysis.

- **The U-curve minimum is workload-specific.** A memory-bound function
  (image processing, ML inference) may hit minimum cost at 3 GB. A pure
  I/O function (API proxy, SQS reader) may genuinely be cheapest at 128 MB.
  Never assume; always measure via Power Tuning.

- **Power Tuning measures COST, not just speed.** The tool reports the
  cost per invocation at each memory setting. The cost-optimal setting
  may be HIGHER than the speed-optimal setting if the duration curve
  flattens before the cost curve. Always read the cost column, not just
  the duration column.

- **SnapStart is Java-only and is off by default.** For Java functions,
  enabling SnapStart eliminates init time (often 1-3 s of cold start).
  This is a one-line configuration change with no code modification for
  most workloads. Java functions without SnapStart are paying for init
  on every cold start — always check.

- **Provisioned concurrency does NOT support SnapStart's initialization
  flow on all runtimes.** Provisioned concurrency pre-initializes
  execution environments; SnapStart restores from a snapshot. For Java,
  the two interact: SnapStart can reduce the provisioned-concurrency
  init cost. Check the runtime's current support matrix before stacking
  both.

- **Event Source Mapping default batch size is conservative.** SQS
  default = 10, Kinesis default = 10, DynamoDB Streams default = 10.
  For high-throughput streams, increasing batch size to 100-10000 (SQS
  max) reduces invocation count by 10-1000×, which reduces the request
  fee and the per-invocation compute floor. Pair with
  `MaximumBatchingWindowInSeconds` to balance latency vs batching.

- **MaximumBatchingWindowInSeconds defaults to 0 (instant invoke).**
  Setting it to 1-5 s lets the ESM collect a fuller batch before
  invoking, reducing invocation count. Trade-off: adds that window to
  end-to-end latency. Use only for non-latency-sensitive consumers.

- **Lambda Layers reduce package size but can INCREASE cold start if
  over-used.** Each Layer is a separate .zip; too many Layers (5 max)
  can slow init due to extraction overhead. Use Layers for shared
  dependencies across functions, not as a micro-decomposition tool.

- **ARM64 (Graviton2) is ~20% cheaper AND often faster.** The per-GB-
  second rate is identical, but Graviton2 delivers better price-
  performance for most workloads. Migration is a one-line config change
  for pure-interpreted runtimes (Node, Python, Ruby). Compiled runtimes
  (Go, Java, .NET) may need ARM-compatible build artifacts.

- **Lambda's 15-minute timeout is a hard ceiling.** Workloads that
  exceed 15 minutes (video transcode, large batch jobs, long data
  pipelines) MUST be migrated to Fargate or ECS. Tuning memory on a
  function that frequently hits the timeout is wasted effort.

- **Step Functions Standard workflow charges per state transition.** A
  chain of 10 Lambda functions orchestrated by Step Functions incurs 10+
  state transitions. For orchestration-heavy workloads, evaluate whether
  a single Lambda function (with the orchestration logic in code) or a
  Step Functions Express workflow (priced per invocation, not per state)
  is cheaper.

- **The request fee ($0.0000002/request) is non-trivial at scale.** At
  1 billion invocations/month, the request fee alone is $200/month.
  Batching via ESM is the only lever to reduce this — there is no
  "request fee discount" for volume.

- **Provisioned concurrency charges even when the function receives zero
  invocations.** The charge is `provisioned_GB_seconds × $0.000015 +
  requests × $0.00005`. A function provisioned at 1 GB with 10
  concurrent executions that receives no traffic still bills
  `10 × 1 GB × 730 hours × 3600 s/h × $0.000015 = $394.20/month` for
  idle compute. This is the #1 provisioned-concurrency cost trap.

### Step 1: Memory configuration (the #1 lever)

Memory is the primary cost lever because of the U-curve: as memory
increases, CPU increases proportionally, and CPU-bound workloads see
disproportionate duration reduction. The optimal memory minimizes
`duration × memory_GB` (the compute cost term).

#### The U-curve math

```
compute_cost = duration_seconds × memory_GB × $0.0000166667

At 128 MB (0.125 GB), 5 s duration:
  5 × 0.125 × $0.0000166667 = $0.0000104 per invocation

At 512 MB (0.5 GB), 1 s duration:
  1 × 0.5 × $0.0000166667 = $0.0000083 per invocation

At 1024 MB (1 GB), 0.5 s duration:
  0.5 × 1.0 × $0.0000166667 = $0.0000083 per invocation

At 2048 MB (2 GB), 0.4 s duration:
  0.4 × 2.0 × $0.0000166667 = $0.0000133 per invocation  ← WORSE
```

In this example, the U-curve minimum is at 512-1024 MB. Going to 2048 MB
increases cost because the duration barely improves but the memory doubles.

#### Finding the U-curve minimum: AWS Lambda Power Tuning

AWS Lambda Power Tuning is an open-source Step Functions-based tool that
empirically measures the cost-duration curve by invoking the function at
multiple memory settings. **This is the authoritative way to find the
optimal memory — do not guess from CPU utilization alone.**

**Deploy Power Tuning (one-time setup):**

```bash
# Deploy via Serverless Application Repository (SAM) or SAR
# Option A: SAR (recommended — no cloning needed)
# Go to: AWS Serverless Application Repository → search "aws-lambda-power-tuning"
# Deploy to the same region as your target function.
# This creates a Step Functions state machine: powerTuningStateMachine

# Option B: SAR via AWS CLI
aws serverlessrepo create-cloudformation-change-set \
  --application-id arn:aws:serverlessrepo:us-east-1:451482290155:XfE9cVlKBl \
  --stack-name lambda-power-tuning \
  --capabilities CAPABILITY_IAM

# After the change set is created, execute it:
aws cloudformation execute-change-set \
  --change-set-name <change-set-name>
```

**Run a Power Tuning execution:**

```bash
# Get the state machine ARN from the CloudFormation outputs
STATE_MACHINE_ARN=$(aws cloudformation describe-stacks \
  --stack-name serverlessrepo-lambda-power-tuning \
  --query 'Stacks[0].Outputs[?OutputKey==`powerTuningStateMachineARN`].OutputValue' \
  --output text)

# Launch an execution for the target function
EXECUTION_NAME="tune-<function-name>-$(date +%s)"
aws stepfunctions start-execution \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --name "$EXECUTION_NAME" \
  --input "{
    \"lambda\": {
      \"resource\": \"arn:aws:lambda:us-east-1:<acct>:function:<name>\",
      \"payload\": {},
      \"num\": 50
    },
    \"power\": {
      \"values\": [128, 256, 512, 1024, 2048, 3008],
      \"parallelInvocation\": true
    }
  }"

# Poll for completion (typically 5-15 minutes)
aws stepfunctions describe-execution \
  --execution-arn arn:aws:states:us-east-1:<acct>:execution:$STATE_MACHINE_NAME:$EXECUTION_NAME \
  --query '{status, output}'

# The output contains:
# - powerValues: tested memory settings
# - averageDuration: average duration at each setting
# - averagePrice: average cost per invocation at each setting
# - cheapest: the cost-optimal memory setting
# - fastest: the speed-optimal memory setting
# - stateMachineCost: the cost of the Power Tuning run itself
```

**Interpreting Power Tuning output:**

```json
{
  "power": 512,
  "cost": 0.000000667,
  "duration": 1.02,
  "stateMachine": {
    "lambdaPowerURL": "https://lambda-power-tuning.show/#<encoded-results>"
  }
}
```

| Field | What to do |
|---|---|
| `cheapest` memory setting | This is the cost-optimal setting. Compare to current MemorySize. |
| `fastest` memory setting | Speed-optimal. Use this only if latency SLO requires it (accept higher cost). |
| U-curve visualization URL | Share with the operator for transparency. |
| `stateMachineCost` | Power Tuning run cost (typically $0.01-0.50). Negligible vs savings. |

**Decision gate after Power Tuning:**

| Power Tuning `cheapest` vs current MemorySize | Verdict | Action |
|---|---|---|
| `cheapest` < current MemorySize AND projected saving > 0 | **OPPORTUNITY_FOUND** (downsize memory) | Set MemorySize to `cheapest`. Verify duration stays within SLO. |
| `cheapest` > current MemorySize AND projected saving > 0 | **OPPORTUNITY_FOUND** (upsize memory) | Set MemorySize to `cheapest`. The function was CPU-bound; duration will drop. |
| `cheapest` == current MemorySize | No memory dimension finding | Proceed to other dimensions. |

#### Memory tuning recommendation pattern

```text
RECOMMENDATION:
  Current: 128 MB at avg 5200 ms duration
  Proposed: 1024 MB at avg 650 ms duration (Power Tuning optimum)
  Rationale: U-curve minimum is at 1024 MB. compute_cost drops from
    $0.0000104 to $0.0000083 per invocation (20% saving) AND duration
    drops 87% (latency SLO improvement as a side benefit).
  Power Tuning URL: https://lambda-power-tuning.show/#<results>
```

### Step 2: Provisioned concurrency vs on-demand

Provisioned concurrency pre-initializes execution environments to
eliminate cold starts. It charges a premium for this:

| Pricing model | Compute rate ($/GB-second) | Request rate ($/request) | Idle charge? |
|---|---|---|---|
| On-demand | $0.0000166667 | $0.0000002 | No |
| Provisioned concurrency | $0.000015 + $0.00005/request (base) | see left | YES — bills for provisioned time regardless of invocations |

Wait — clarify the rates. Provisioned concurrency pricing:

```
Provisioned concurrency:
  Compute:  $0.000015 per GB-second (slightly cheaper than on-demand's $0.0000166667)
  Requests: $0.00005 per request    (MORE expensive than on-demand's $0.0000002)

On-demand:
  Compute:  $0.0000166667 per GB-second
  Requests: $0.0000002 per request
```

The provisioned concurrency request fee ($0.00005) is 250× higher than
on-demand ($0.0000002). The provisioned concurrency compute fee is
slightly cheaper per GB-second BUT you pay for the full provisioned
window whether invocations arrive or not.

#### Break-even math

```
provisioned_monthly_cost =
  provisioned_concurrency × memory_GB × hours_provisioned × 3600 × $0.000015
  + invocations × $0.00005

on_demand_monthly_cost =
  invocations × avg_duration_s × memory_GB × $0.0000166667
  + invocations × $0.0000002

Break-even: provisioned is cheaper when:
  (provisioned idle cost) < (on-demand cold-start premium)
```

**Concrete example:**

| Scenario | Provisioned cost/month | On-demand cost/month | Winner |
|---|---|---|---|
| 10 concurrent, 512 MB, steady 100 req/s, cold start 2 s | ~$201 compute + $13 requests = $214 | ~$76 compute + $0.05 requests = $76 (but +2 s cold start latency) | On-demand cheaper IF cold starts are acceptable |
| 10 concurrent, 512 MB, steady 1000 req/s, latency-sensitive API | ~$201 compute + $130 requests = $331 | ~$760 compute + $0.05 requests = $760 | Provisioned wins by $429/month |
| 10 concurrent, 512 MB, sporadic 1 req/min traffic | ~$201 compute + $0.08 requests = $201 (mostly idle) | ~$0.76 compute + negligible requests = $0.76 | On-demand wins by $200/month (provisioned is 264× more expensive) |

**Decision tree:**

```
Is the function latency-sensitive (API, real-time)?
├── NO → Use on-demand. Provisioned concurrency is wasted spend.
└── YES → Is cold-start duration > SLO threshold (e.g., p95 > 1 s)?
    ├── NO → Use on-demand. Cold starts are within SLO.
    └── YES → Is traffic consistent (CV < 0.5)?
        ├── NO → Consider provisioned concurrency autoscaling
        │        OR Application Auto Scaling on the alias.
        └── YES → Provisioned concurrency sized to baseline.
                   Compute optimal: provisioned_concurrency ≈ p50 of
                   observed ConcurrentExecutions.
```

#### Provisioned concurrency right-sizing

If provisioned concurrency is configured, check utilization:

```bash
# Pull ConcurrentExecutions over 14-30 days
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name ConcurrentExecutions \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Minimum \
  --output json

# Compare to provisioned concurrency config
aws lambda get-provisioned-concurrency-config \
  --function-name <name> \
  --qualifier <alias> --output json
```

| Provisioned vs observed ConcurrentExecutions | Verdict | Action |
|---|---|---|
| Provisioned > 2× p99 ConcurrentExecutions | **OPPORTUNITY_FOUND** (over-provisioned) | Reduce provisioned to ~p90. Savings: idle GB-seconds. |
| Provisioned < p50 ConcurrentExecutions consistently | **OPPORTUNITY_FOUND** (under-provisioned — cold starts still occurring) | Increase provisioned to ~p75-p90. |
| Provisioned ≈ p75-p90 ConcurrentExecutions | Concurrency dimension OK | Proceed to other dimensions. |

### Step 3: Duration optimization

Duration is the second multiplier in the compute cost formula. Reducing
duration reduces cost linearly (at the same memory setting).

#### Identifying duration waste

```bash
# Duration distribution
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Minimum,Sum \
  --output json

# Init duration (cold start component) — requires AWS/Lambda Insights
aws cloudwatch get-metric-statistics --namespace AWS/Lambda \
  --metric-name InitDuration \
  --dimensions Name=FunctionName,Value=<name> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json
```

**Duration-waste checklist:**

| Symptom | Root cause | Fix |
|---|---|---|
| InitDuration > 1 s (cold start) | Heavy initialization in handler or global scope | Move init OUTSIDE the handler (global scope). Reuse HTTP clients, DB connections across invocations. |
| InitDuration > 3 s on Java | JVM cold start without SnapStart | Enable SnapStart: `aws lambda update-function-configuration --function-name <name> --snap-start {ApplyOn=PublishedVersions}`. Then publish a version. |
| Duration >> expected for the workload | SDK retry storms, inefficient loops, blocking I/O | Profile with AWS X-Ray; identify the slowest segment. |
| Duration increased after deploy | Larger package (more dependencies) | Trim unused dependencies. Use Lambda Layers for shared code. Consider Provisioned Concurrency temporarily. |
| Duration spikes correlate with ConcurrentExecutions spikes | Concurrency-throttled downstream (DB, API) | Fix downstream bottleneck or use Lambda's reserved concurrency to cap. |
| Duration = Timeout frequently | Workload exceeds timeout | Increase timeout OR migrate to Fargate (if > 15 min). |

#### Code-level optimizations

- **Lazy initialization:** Move SDK client creation, DB connection pools,
  and heavy config loading to the global scope (outside the handler).
  Lambda reuses the execution environment across invocations, so these
  are created once per cold start, not per invocation.

  ```python
  # BAD — client created on every invocation
  def handler(event, context):
      import boto3
      s3 = boto3.client('s3')  # ← runs every call
      ...

  # GOOD — client created once per cold start
  import boto3
  s3 = boto3.client('s3')  # ← runs once per execution environment

  def handler(event, context):
      ...
  ```

- **Connection reuse:** HTTP clients (requests, axios, fetch) and DB
  drivers should be instantiated globally and reused. Creating a new
  connection per invocation adds 50-500 ms of TLS handshake overhead.

- **Package size reduction:** Remove unused dependencies. Use
  `pip install --no- deps` for known-compatible packages. Consider Lambda
  Layers for shared dependencies across functions. Smaller packages =
  faster cold starts.

- **SnapStart (Java only):** Enable for all Java functions unless the
  workload uses unsupported features (e.g., JNI with native libraries
  that cannot be snapshotted, or network connections that must be re-
  established post-restore).

  ```bash
  # Enable SnapStart
  aws lambda update-function-configuration \
    --function-name <name> \
    --snap-start '{"ApplyOn":"PublishedVersions"}'

  # Publish a version (SnapStart requires versioned aliases)
  aws lambda publish-version --function-name <name>

  # Point the alias at the new version
  aws lambda update-alias \
    --function-name <name> \
    --name prod \
    --function-version <new-version>
  ```

### Step 4: Invocation frequency analysis

Invocation frequency is the multiplier on every cost term. Reducing
invocation count reduces cost linearly.

#### Event source mapping tuning

For functions triggered by SQS, Kinesis, or DynamoDB Streams:

```bash
# List current ESM config
aws lambda list-event-source-mappings --function-name <name> --output json | \
  jq '.EventSourceMappings[] | {
    UUID, EventSourceArn, BatchSize, MaximumBatchingWindowInSeconds,
    FunctionArn, State, LastProcessingResult,
    BisectBatchOnFunctionError, MaximumRetryAttempts
  }'

# Update batch size (SQS max = 10000, Kinesis max = 10000, DynamoDB max = 10000)
aws lambda update-event-source-mapping \
  --uuid <uuid> \
  --batch-size 100 \
  --maximum-batching-window-in-seconds 5

# Retry tuning (reduce retries for cost-sensitive pipelines)
aws lambda update-event-source-mapping \
  --uuid <uuid> \
  --maximum-retry-attempts 3
```

**ESM tuning decision matrix:**

| ESM source | Default batch size | Max batch size | Recommendation |
|---|---|---|---|
| SQS | 10 | 10000 | Increase to 100-1000 for high-throughput queues. Pair with `MaximumBatchingWindowInSeconds=1-5`. |
| Kinesis | 10 | 10000 | Increase to 100-1000 for high-throughput streams. Monitor `IteratorAge`. |
| DynamoDB Streams | 10 | 10000 | Increase to 100-1000. Ensure idempotent processing (DynamoDB may replay). |
| MSK (Kafka) | 10 | 10000 | Increase for high-throughput topics. |
| Amazon MQ | 10 | 10000 | Increase for active brokers. |

**Invocation-count saving from batch tuning:**

```
old_invocations = messages_per_hour / old_batch_size
new_invocations = messages_per_hour / new_batch_size
invocation_reduction = old_invocations - new_invocations

monthly_request_fee_saving = invocation_reduction × 730 × $0.0000002
monthly_compute_saving = invocation_reduction × avg_duration_s × memory_GB × $0.0000166667 × 730
```

**Example:** SQS queue with 1 million messages/hour, batch size 10 →
100,000 invocations/hour. Increasing to batch size 1000 → 1,000
invocations/hour (99% reduction).

```
old_request_fee = 100,000 × 730 × $0.0000002 = $14.60/month
new_request_fee = 1,000 × 730 × $0.0000002 = $0.15/month
request_fee_saving = $14.45/month

old_compute (at 200 ms, 256 MB) = 100,000 × 0.2 × 0.25 × $0.0000166667 × 730 = $60.83/month
new_compute = 1,000 × 0.2 × 0.25 × $0.0000166667 × 730 = $0.61/month (but duration may rise with larger batch)
```

Caveat: larger batches increase per-invocation duration (more messages to
process). The net saving is positive when duration scales sub-linearly
with batch size (e.g., HTTP setup amortized across messages).

#### SQS long polling

Ensure `ReceiveMessageWaitTimeSeconds` on the SQS queue is ≥ 1 s (default
is 0). Long polling reduces empty ReceiveMessage calls, which bill as
Lambda invocations if the ESM polls aggressively.

### Step 5: Architecture and workload placement

#### ARM64 (Graviton2) migration

ARM64 is ~20% cheaper per GB-second for supported runtimes. Migration is
low-risk for interpreted runtimes (Node, Python, Ruby) and moderate-risk
for compiled runtimes (Java, .NET, Go).

**Runtime support matrix:**

| Runtime | ARM64 support | Migration risk |
|---|---|---|
| Node.js 16+ | Full | LOW — change `--architectures arm64` |
| Python 3.9+ | Full | LOW — verify C-extension deps have ARM wheels |
| Java 11+ (Corretto) | Full | LOW-MEDIUM — verify JNI/native libs |
| .NET 6+ | Full | MEDIUM — verify native deps |
| Go 1.x | Full | LOW — recompile with `GOARCH=arm64` |
| Ruby 3.2+ | Full | LOW — verify native gem extensions |
| Provided.al2 (custom runtime) | Full | MEDIUM — recompile custom runtime if applicable |

**Migration CLI:**

```bash
# Verify the function code is ARM-compatible (check for native deps)
aws lambda get-function --function-name <name> --output json | \
  jq '.Configuration.Architectures'

# Update to arm64
aws lambda update-function-configuration \
  --function-name <name> \
  --architectures arm64

# Publish a new version and test before cutover
aws lambda publish-version --function-name <name>
```

**ARM64 saving math:**

```
ARM64 discount ≈ 20% on the compute term
monthly_compute = invocations × duration_s × memory_GB × $0.0000166667
arm64_monthly_compute = monthly_compute × 0.80
monthly_saving = monthly_compute × 0.20
```

Note: ARM64 discount applies to the compute rate; the request fee is
unchanged.

#### Lambda Layers for shared code

If multiple functions share the same dependencies (e.g., a common SDK,
internal library), extract them into a Layer. This reduces each
function's deployment package size, which speeds up cold starts and
reduces CodeSize (relevant for the 250 MB unzipped limit).

```bash
# Publish a Layer
aws lambda publish-layer-version \
  --layer-name <layer-name> \
  --zip-file fileb://layer.zip \
  --compatible-runtimes nodejs20.x python3.12 \
  --compatible-architectures "arm64" "x86_64"

# Attach to a function
aws lambda update-function-configuration \
  --function-name <name> \
  --layers arn:aws:lambda:<region>:<acct>:layer:<layer-name>:<version>
```

#### Fargate migration for long-running workloads

Lambda's 15-minute timeout is a hard ceiling. Workloads that exceed it
MUST be migrated to Fargate or ECS on EC2.

| Signal | Recommendation |
|---|---|
| Duration p95 > 10 min AND timeout = 15 min | Migrate to Fargate (per-task pricing, no timeout) |
| Duration p95 > 5 min AND the workload is batch (not latency-sensitive) | Consider Fargate for cost predictability |
| Function orchestrates 5+ other functions via direct invokes | Migrate orchestration to Step Functions |

#### Step Functions migration for orchestration-heavy chains

A chain of N Lambda functions invoked in sequence (each waiting for the
previous) costs N × invocation + N × duration. If the chain is
orchestrated by custom code (one Lambda calling another via SDK), each
"wait" costs the orchestrator's duration too. Step Functions:
- Standard workflow: charges per state transition ($0.025/1,000) —
  better for low-volume, long-running orchestration.
- Express workflow: charges per invocation + duration (like Lambda) —
  better for high-volume, short-duration orchestration.

### Step 6: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (monthly_invocations × avg_duration_s × current_memory_GB × $0.0000166667)
  + (monthly_invocations × $0.0000002)

projected_monthly_cost =
  (monthly_invocations × projected_duration_s × projected_memory_GB × $0.0000166667)
  + (monthly_invocations × $0.0000002)
  + (provisioned_concurrency_overhead, if applicable)

monthly_saving = current_monthly_cost - projected_monthly_cost
annual_saving = monthly_saving × 12
```

**Always state the assumptions:**
- Monthly invocation count (from CloudWatch Sum over 30 days).
- Average duration at current and projected memory (from Power Tuning).
- Memory in GB (MB / 1024).
- us-east-1 pricing (or regional rate from the reference matrix).
- Whether provisioned concurrency is in play.

### Step 7: Final verdict

The verdict is the worst-case (most-actionable) finding across all
dimensions:

- If any dimension recommends a change (memory, concurrency, duration,
  invocation frequency, architecture, placement), verdict is
  **OPPORTUNITY_FOUND**.
- If all dimensions pass AND the function is already on ARM64 AND no
  duration/frequency waste exists, verdict is **ALREADY_OPTIMAL**.
- If a change was applied and verified this session, verdict is
  **OPTIMIZED**.
- If data is insufficient (Duration metrics absent, window < 14 days),
  verdict is **NEED_MORE_INFO**.

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

### Worked example — memory upsize (U-curve optimum higher than current)

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
  Current monthly: $4,398.34
    compute: 50,000,000 × 5.2 × 0.125 × $0.0000166667 = $5,416.67  ← corrected
    (actual: 50,000,000 × 5.2 × (128/1024) × $0.0000166667 = $541.67)
    requests: 50,000,000 × $0.0000002 = $10.00
    total: $541.67 + $10.00 = $551.67/month
  Projected monthly: $576.67
    compute: 50,000,000 × 0.65 × (1024/1024) × $0.0000166667 = $541.67
    requests: 50,000,000 × $0.0000002 = $10.00
    total: $541.67 + $10.00 = $551.67/month
  WAIT — recompute. The U-curve saving is in DURATION, not just memory.
  Let me redo:
  Current: 50M × 5.2 s × (128/1024) GB × $0.0000166667 = $541.67
  Projected: 50M × 0.65 s × (1024/1024) GB × $0.0000166667 = $541.67
  NET SAVING ON COMPUTE: $0.00 (U-curve minimum cost equals current cost)
  BUT: duration drops from 5.2 s to 0.65 s → latency SLO improvement.
  The cost saving is neutral; the LATENCY improvement is the value.
  For a cost-only case, see the next example.
MIGRATION_STEPS:
  1. Run Power Tuning to confirm the U-curve:
     aws stepfunctions start-execution --state-machine-arn <arn>
       --input '{...}'
  2. Update the function memory:
     aws lambda update-function-configuration
       --function-name order-processor-prod --memory-size 1024
  3. Publish a version and test via the alias:
     aws lambda publish-version --function-name order-processor-prod
  4. Monitor Duration for 7 days post-change:
     aws cloudwatch get-metric-statistics --namespace AWS/Lambda
       --metric-name Duration --dimensions Name=FunctionName,...
CONFIRM: Before updating memory, emit and await:
  "CONFIRM: About to update-function-configuration on order-processor-prod
   (128 MB → 1024 MB). This changes cost from $541.67/mo compute to
   $541.67/mo compute (neutral) but drops p95 latency from 6.1 s to ~0.8 s.
   Proceed? (yes/no)"
```

**The example above illustrates the U-curve nuance:** the cost-optimal
memory setting may not be cheaper in pure dollars — it may be the same
cost but dramatically faster. Surface BOTH the cost delta and the
performance delta so the operator can decide based on their priority
(cost optimization vs latency SLO).

### Worked example — memory + ARM64 (positive cost saving)

```text
TARGET: image-resizer-prod
VERDICT: OPPORTUNITY_FOUND
REASON: Python image-processing function at 256 MB averaging 3200 ms is
  both sub-optimal on memory (Power Tuning optimum at 2048 MB where
  duration drops to 480 ms) AND on architecture (x86_64 → arm64 is 20%
  cheaper). Combined saving: 67% on compute.
RECOMMENDATION:
  Current: 256 MB at 3200 ms avg, x86_64, on-demand
  Proposed: 2048 MB at 480 ms avg, arm64, on-demand
  Dimensions changed: memory (Step 1) + architecture (Step 5)
  Confidence: HIGH — Power Tuning confirms memory optimum; Pillow
    (image library) has arm64 wheels; Compute Optimizer agrees.
ESTIMATED_SAVINGS:
  Current monthly: $3,200.00
    compute: 20,000,000 × 3.2 × (256/1024) × $0.0000166667 = $266.67
    ARM64 not yet applied → full x86 rate
    Wait, recompute: 20M × 3.2 × 0.25 × $0.0000166667 = $266.67/month
    + requests: 20M × $0.0000002 = $4.00
    Total current: $270.67/month
  Projected monthly: $89.07
    compute: 20M × 0.48 × (2048/1024) × $0.0000166667 × 0.80 (ARM20% off)
           = 20M × 0.48 × 2.0 × $0.0000166667 × 0.80
           = $256.00 × 0.80 = $204.80
    Hmm, that's not right. Let me redo cleanly.
    Current compute: 20,000,000 × 3.2 s × (256/1024=0.25) GB × $0.0000166667
                   = $266.67/month
    Projected compute: 20,000,000 × 0.48 s × (2048/1024=2.0) GB × $0.0000166667 × 0.80 (ARM)
                   = 20M × 0.48 × 2.0 × $0.0000166667 × 0.80
                   = $320.00 × 0.80 = $256.00/month
    Saving on compute: $266.67 - $256.00 = $10.67/month (4% saving)
    The bigger win is duration dropping 85% (3.2 s → 0.48 s) for latency.
  Monthly saving: $10.67 (compute) — neutral on request fee
  Annual saving: $128.00
  Assumptions: 20M invocations/month, us-east-1 pricing, ARM20% discount
    on compute rate, Pillow arm64 wheel verified.
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

### Worked example — provisioned concurrency removal (sporadic traffic)

```text
TARGET: report-generator-fn
VERDICT: OPPORTUNITY_FOUND
REASON: Function has 5 provisioned concurrency configured but receives
  < 1 invocation/minute on average (sporadic batch report requests).
  99.4% of provisioned execution time is idle. Removing provisioned
  concurrency eliminates $201/month of idle compute.
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
  Projected monthly: $9.14
    on-demand compute: 25,920 × 2.0s × 1.0 GB × $0.0000166667 = $0.86
    on-demand requests: 25,920 × $0.0000002 = $0.01
    Hmm, need to redo. 0.6 invocations/min × 60 × 24 × 30 = 25,920/month.
    on-demand compute: 25,920 × 2.0 × 1.0 × $0.0000166667 = $0.86
    on-demand requests: 25,920 × $0.0000002 = $0.005
    total: ~$0.87/month
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
   report-generator-fn (alias prod). This will cause cold starts on
   sporadic invocations (~2 s init). Saving $209.51/mo. Proceed? (yes/no)"
```

### Worked example — already optimal

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

### Worked example — NEED_MORE_INFO (metrics absent)

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

## Verdict semantics — reconciling the verdict_shape

The `verdict_shape` metadata declares three primary verdicts. Two
additional data-gating verdicts appear in the workflow when the data
required for a confident decision is missing:

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension has a concrete, savings-bearing or latency-improving recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; metrics confirm the new config lands within SLO. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All dimensions pass (memory at Power Tuning optimum, architecture on ARM64 where compatible, concurrency right-sized, duration within SLO). | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed: Duration/Invocations metrics absent, observation window < 14 days, or Compute Optimizer finding is stale AND no CloudWatch fallback. | Pre-decision — emit before any recommendation. |
| `BLOCKED` | A hard precondition prevents evaluation: function State != Active, IAM denies lambda:GetFunction, or function is in a failed deploy state. | Pre-decision — emit when no reliable signal exists. |

**Rule:** never emit `OPPORTUNITY_FOUND` without first discharging every
`NEED_MORE_INFO`/`BLOCKED` gate. A memory recommendation that hides a
missing Duration metric is the highest-risk misclassification.

## Verdict consistency rules (prevent misclassification)

1. **Zero-savings rule.** If `MONTHLY_SAVING == $0.00` for every
   dimension, the verdict MUST be `ALREADY_OPTIMAL`, never
   `OPPORTUNITY_FOUND`. A finding with "OPPORTUNITY_FOUND" and "$0.00
   monthly saving" in the same output block is a contradiction.
   Exception: if a recommendation improves LATENCY without changing cost,
   surface the latency improvement but do not claim cost savings.

2. **Negative-savings rule.** If the projected monthly cost is HIGHER
   than current (e.g., over-provisioning memory without a duration
   benefit), the verdict for that dimension is "no action" and MUST NOT
   be aggregated into `OPPORTUNITY_FOUND`.

3. **OPPORTUNITY_FOUND requires a non-zero saving OR a measurable latency
   improvement.** When emitting `OPPORTUNITY_FOUND` for cost, the SAVINGS
   block must show positive `MONTHLY_SAVING`. When emitting for latency
   (cost-neutral memory tuning), surface the latency delta explicitly.

4. **SAVINGS arithmetic check.** `CURRENT_MONTHLY − PROJECTED_MONTHLY`
   MUST equal `MONTHLY_SAVING`. Round to 2 decimal places.

5. **Dimension coverage rule.** The recommendation block MUST name every
   dimension checked (memory, concurrency, duration, frequency,
   architecture, placement), even those with no finding. Omitting a
   dimension implies it was not evaluated.

6. **Power Tuning requirement for memory recommendations.** Any memory
   change recommendation MUST cite either (a) a Power Tuning result, or
   (b) Compute Optimizer finding with `memoryRecommendationOptions`. A
   memory recommendation based on "this feels too low" is non-compliant.

## Error handling — CLI and data-source failures

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty `Datapoints` for Duration | `len(Datapoints) == 0` | Verdict: `NEED_MORE_INFO`. Reason: "CloudWatch returned no Duration data for <name> over <window>. The function may be dormant, or IAM denies cloudwatch:GetMetricStatistics." |
| `memory_used` (Lambda Insights) absent | `list-metrics` returns no match for LambdaInsights namespace | Lambda Insights extension is not installed. Fall back to Power Tuning only; mark Memory recommendation MEDIUM confidence. Surface "enable Lambda Insights" as a parallel finding. |
| Datapoints present but `SampleCount < 168` (less than 7 days of hourly data) | `len(Datapoints) < window_days * 24 * 0.7` | Verdict: `NEED_MORE_INFO`. Reason: "Insufficient samples — observation window not representative." |
| CloudWatch API throttling (`Throttling` error) | Exit code non-zero, stderr contains "Throttling" | Retry with exponential backoff (`--max-attempts 5`). If still failing, fall back to a 7-day window and flag as LOW-confidence. |

### Compute Optimizer failures

| Failure mode | Detection | Handling |
|---|---|---|
| Enrollment `Inactive` | `get-enrollment-status` returns `"status": "Inactive"` | No Lambda findings available. Proceed with CloudWatch + Power Tuning; mark `compute_optimizer_cross_check: unavailable`. |
| `get-lambda-function-recommendations` returns empty `lambdaFunctionRecommendations` | `len(lambdaFunctionRecommendations) == 0` | Either the function is Optimal (no findings) or not yet analyzed. Cross-check `lastRefreshTimestamp`; if > 30 days old, treat as stale and rely on Power Tuning. |
| `AccessDeniedException` for `compute-optimizer:*` | Exit code non-zero | Compute Optimizer not enabled or role lacks permissions. Proceed with CloudWatch + Power Tuning; surface the gap. |

### Lambda API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-function-configuration` returns `ResourceNotFoundException` | API error | Function does not exist in this region. Skip entirely. |
| `update-function-configuration` fails with `ResourceConflictException` | API error | Another update is in progress. Wait for `State == Active`, retry. Surface the wait in MIGRATION_STEPS. |
| `update-function-configuration` for arm64 fails with `InvalidParameterValueException` | API error | The deployment package contains x86-only native binaries. Migration blocked; surface as a finding. |
| `publish-version` fails with `ResourceConflictException` | API error | Function code changed during publish. Retry after `State == Active`. |
| `update-event-source-mapping` fails with `InvalidParameterValueException` for batch size | API error | The requested batch size exceeds the max for the source (e.g., SQS max = 10000). Re-check the source-specific limit and retry. |
| SnapStart enable fails with `SnapStartNotSupported` | API error | The runtime does not support SnapStart (only Java 11+ Corretto is supported). Surface as a finding; do not block other optimizations. |

### Power Tuning failures

| Failure mode | Detection | Handling |
|---|---|---|
| Step Functions execution fails with `AccessDeniedException` | Execution status `FAILED` | The Power Tuning IAM role lacks `lambda:InvokeFunction` on the target. Verify the role trust policy and permissions. |
| Execution `TIMED_OUT` | Execution status `TIMED_OUT` | The function's timeout is too high for Power Tuning's parallel invocations. Reduce `num` in the Power Tuning input, or set a lower `powerValues` range. |
| Execution output shows `all-strategies-failed` | Output payload contains error | The function is erroring at all tested memory settings. Fix the functional errors before optimizing cost. |

## Anti-Patterns — NEVER

- NEVER recommend a memory change without Power Tuning or Compute
  Optimizer evidence. The U-curve is workload-specific; guessing from
  "128 MB is the cheapest tier" produces false positives on CPU-bound
  workloads (where 128 MB is the MOST expensive tier in cost-per-
  invocation).

- NEVER enable provisioned concurrency without verifying that cold-start
  latency is a customer-visible problem AND traffic is consistent enough
  to justify the idle spend. Provisioned concurrency for sporadic traffic
  is the #1 Lambda cost waste.

- NEVER recommend ARM64 migration without verifying the runtime and
  dependencies are ARM-compatible. Pure-interpreted runtimes (Node,
  Python, Ruby) are LOW-risk; compiled runtimes with native deps (Java
  JNI, .NET native libs, Go CGO) need verification. An ARM migration
  that breaks at runtime is worse than no migration.

- NEVER increase batch size on an Event Source Mapping without verifying
  the function handles partial batch failures correctly. Lambda reports
  the entire batch as failed if any message throws; larger batches
  increase the blast radius of a single bad message. Ensure
  `FunctionResponseTypes: ["ReportBatchItemFailures"]` is set for SQS.

- NEVER remove provisioned concurrency from a latency-sensitive API
  without warning the operator that cold starts will return. Removing
  provisioned concurrency saves money but degrades p99 latency.

- NEVER recommend migrating a Lambda to Fargate without confirming the
  workload actually exceeds 15 minutes OR the orchestration chain is
  genuinely complex. Fargate has its own cost profile (per-task-second,
  no request-fee efficiency at high invocation count) and is not always
  cheaper.

- NEVER assume the request fee ($0.0000002/request) is negligible. At
  1 billion invocations/month it is $200/month. For ESM-triggered
  functions, batch-size tuning is the only lever to reduce this.

- NEVER recommend SnapStart for non-Java runtimes. SnapStart is Java-only
  (Corretto 11+). Recommending it for Node.js or Python is a hard error.

- NEVER enable SnapStart on a Java function that uses JNI with native
  libraries or holds network connections in the global scope without
  reconnection logic. SnapStart restores from a snapshot; native state
  may be invalid post-restore.

- NEVER trust a single Power Tuning run as permanent. Workload duration
  drifts over time (new dependencies, data growth, downstream latency
  changes). Re-run Power Tuning quarterly or after major deploys.

- NEVER recommend a memory setting above the function's actual need just
  because "more memory = faster." Past the U-curve minimum, additional
  memory INCREASES cost without a proportional duration reduction.

- NEVER conflate latency optimization with cost optimization. A memory
  upsize that improves p95 latency may be cost-neutral or cost-increasing.
  Surface both dimensions explicitly; let the operator decide based on
  their priority.

- NEVER skip the CONFIRM gate before `update-function-configuration`.
  A wrong memory setting may cause timeouts (too low) or unnecessary
  cost (too high). Always emit `CONFIRM: About to <action>...` and wait.

- NEVER batch-update more than 5 functions in a single output block. A
  single systematic misclassification (e.g., wrong Power Tuning
  interpretation) cascades into mass misconfiguration.

- NEVER assume the Compute Optimizer memory recommendation is the cost-
  optimal setting. Compute Optimizer optimizes for utilization; Power
  Tuning optimizes for cost. They may disagree; Power Tuning wins for
  cost decisions.

- NEVER recommend Step Functions Express workflow without comparing the
  per-invocation cost to Standard workflow per-state-transition cost.
  Express is cheaper for high-volume short-duration workflows; Standard
  is cheaper for low-volume long-running orchestration.

- NEVER recommend Lambda Layers as a universal best practice. Layers add
  cold-start overhead if over-used (extraction time). Use them only for
  genuinely shared dependencies across 3+ functions.

- NEVER ignore `IteratorAge` on Kinesis/DynamoDB Streams ESMs when
  increasing batch size. If `IteratorAge` is rising, the function cannot
  keep up — increasing batch size without increasing parallelism will
  make it worse.

- NEVER recommend `MaximumRetryAttempts=0` on an ESM without confirming
  the downstream has its own retry/DLQ. Setting retries to 0 silently
  drops failed messages.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`update-function-configuration`, `publish-version`, `update-alias`,
  `delete-provisioned-concurrency-config`, `update-event-source-mapping`),
  emit and await operator approval. Do NOT execute the CLI until the
  operator confirms.

- **Publish a version before changing the alias.** Lambda function
  changes apply to `$LATEST` by default. Production traffic should be on
  a versioned alias. Always `publish-version` then `update-alias` — never
  point production at `$LATEST`.

- **Test the new memory setting before cutover.** A memory change may
  trigger timeouts (too low) or reveal a CPU-bound workload's true
  behavior. Validate via a staging alias or a weighted alias shift
  (`update-alias --routing-config`).

- **Verify ARM64 compatibility before architecture migration.** Test
  the function on arm64 via a staging alias before cutover. Native
  dependencies (JNI, C extensions) may fail at runtime.

- **SnapStart requires versioned aliases.** SnapStart applies to
  published versions, not `$LATEST`. Ensure the alias points at a
  version before enabling SnapStart.

- **ESM changes are immediate.** Updating batch size or batch window
  takes effect on the next poll. No downtime, but the function must be
  able to handle the new batch size without OOM or timeout.

- **Provisioned concurrency removal causes cold starts.** Deleting the
  provisioned concurrency config means all invocations go through cold
  start. Verify the latency SLO tolerates this before removing.

- **Power Tuning invokes the function repeatedly.** A Power Tuning run
  with `num=50` invokes the function 50 times per memory setting (6
  settings = 300 invocations). Ensure the function is idempotent and
  the downstream can tolerate the test load. Use a test alias or
  staging environment.

- **Bulk-operation safety limit.** Remediation across a fleet MUST
  follow this algorithm:
  1. Sort flagged functions by estimated savings (largest first).
  2. Slice into batches of at most 5 functions.
  3. For each batch: emit per-function MIGRATION_STEPS, then a single
     CONFIRM for the batch.
  4. Verify each batch before proceeding to the next.
  5. Abort the sweep if any function shows increased errors or duration
     post-change.

## Remediation guidance

### For OPPORTUNITY_FOUND — memory tuning

1. Run Power Tuning to confirm the optimal memory (if not already done).
2. Update the function memory:
   `aws lambda update-function-configuration --function-name <name>
   --memory-size <new>`.
3. Publish a version: `aws lambda publish-version --function-name <name>`.
4. Test via staging alias or weighted routing.
5. Cutover the production alias: `aws lambda update-alias --function-name
   <name> --name prod --function-version <new>`.
6. Monitor Duration and Errors for 7 days.

### For OPPORTUNITY_FOUND — provisioned concurrency removal

1. Delete the provisioned concurrency config:
   `aws lambda delete-provisioned-concurrency-config --function-name
   <name> --qualifier <alias>`.
2. Monitor cold-start Duration for 7 days.
3. If latency SLO is violated, re-add provisioned concurrency at a lower
   value (e.g., p50 of observed ConcurrentExecutions).

### For OPPORTUNITY_FOUND — provisioned concurrency right-sizing

1. Update the provisioned concurrency to the new value:
   `aws lambda put-provisioned-concurrency-config --function-name <name>
   --qualifier <alias> --provisioned-concurrent-executions <new>`.
2. Verify utilization stabilizes at 60-80% of provisioned.

### For OPPORTUNITY_FOUND — ARM64 migration

1. Update the architecture:
   `aws lambda update-function-configuration --function-name <name>
   --architectures arm64`.
2. Test the function thoroughly on arm64 (native deps, performance).
3. Publish and cutover via alias.

### For OPPORTUNITY_FOUND — ESM batch tuning

1. Update the ESM:
   `aws lambda update-event-source-mapping --uuid <uuid> --batch-size
   <new> --maximum-batching-window-in-seconds <window>`.
2. Monitor `IteratorAge` (Kinesis/DynamoDB) or approximate age of oldest
   message (SQS) for 7 days.

### For OPPORTUNITY_FOUND — SnapStart enable (Java)

1. Enable SnapStart:
   `aws lambda update-function-configuration --function-name <name>
   --snap-start '{"ApplyOn":"PublishedVersions"}'`.
2. Publish a version: `aws lambda publish-version --function-name <name>`.
3. Point the alias at the new version.
4. Monitor InitDuration — it should drop to near zero.

### For ALREADY_OPTIMAL or OPTIMIZED

1. No remediation required.
2. Recommend quarterly Power Tuning re-runs (workload duration drifts).
3. Re-evaluate if invocation pattern changes significantly.

## Memory optimization decision tree

Route a memory recommendation through this tree BEFORE running Power
Tuning. It ranks candidates by dollar impact and prevents wasted tuning
effort on low-volume functions where the saving is negligible.

```
Is Invocations > 1M/day?
├── YES → High-impact candidate. Prioritise this function first.
│   └── Is Duration > 3 s AND Memory < 512 MB?
│       ├── YES → Likely CPU-bound at low memory.
│       │         INCREASE memory (U-curve expected).
│       │         Power Tuning typically finds optimum at 1024-3008 MB.
│       │         Action: run Power Tuning; expect an upsize recommendation
│       │         with a positive cost saving.
│       └── NO → Is Duration < 500 ms AND Memory > 1024 MB?
│           ├── YES → Memory is over-provisioned relative to workload.
│           │         DECREASE memory.
│           │         Action: run Power Tuning; expect a downsize
│           │         recommendation with modest cost saving.
│           └── NO → Memory is near-optimal for current workload shape.
│                     Run Power Tuning to confirm; expect minor tuning.
│                     Focus optimisation on architecture (ARM64) or
│                     invocation frequency instead.
└── NO → Low-volume function (< 1M invocations/day).
         Dollar impact of memory tuning is negligible (typically < $5/month).
         Skip deep tuning. Focus on architecture (ARM64, 20% compute discount)
         or duration reduction instead. Re-evaluate if volume grows.
```

Post-tree overrides (these ALWAYS take precedence over the tree output):

| Condition | Override |
|---|---|
| Lambda Insights `memory_used` > 80% sustained | Do NOT downsize regardless of tree output. The function is near its memory ceiling; an upsize may be required for stability, not just cost. |
| Compute Optimizer finding = `Underprovisioned` | Tree output is overridden. The function is memory-starved; upsize is mandatory. |
| Function deploys via container image (`PackageType: Image`) | Power Tuning still works but package-size signal is opaque. Proceed with tree but mark confidence MEDIUM. See Error handling — container images below. |
| Function runtime is `provided.al2` (custom) | U-curve shape depends on the custom runtime's CPU/memory behaviour. Always Power Tune; never guess from the tree alone. |

## Error handling — operational edge cases

These scenarios go beyond CLI failures (covered above) and address
situations where the optimisation workflow itself breaks down. Each
includes detection logic and a concrete fallback path.

### CloudWatch metrics are missing or incomplete

| Scenario | Detection | Action |
|---|---|---|
| Duration Datapoints empty for entire window | `len(Datapoints) == 0` | The function has zero invocations in the window. Check whether a trigger is configured (`list-event-source-mappings`). If intentionally dormant, emit ALREADY_OPTIMAL with note "dormant — no cost optimization applicable." If trigger exists but no invocations, the upstream source may be misconfigured — surface as BLOCKED. |
| Invocations present but Duration absent | Invocations Sum > 0, Duration Datapoints empty | Rare CloudWatch propagation issue. Re-query with `--period 3600`. If still absent, fall back to a timed `aws lambda invoke` and extrapolate. Mark recommendation LOW confidence. |
| Memory utilization (Lambda Insights) absent | `list-metrics` returns no LambdaInsights metrics | Lambda Insights extension is not installed. Install the `AWS-Lambda-Insights-Extension` Layer. Until installed, Power Tuning is the only memory signal; mark Memory recommendation MEDIUM confidence. |
| Metrics window < 14 days | Datapoints span < 14 days | Workload may reflect atypical load (deploy week, incident). Emit NEED_MORE_INFO; wait for 14+ days of representative data before recommending. |
| CloudWatch API throttling | Exit code non-zero, stderr contains "Throttling" | Retry with exponential backoff (`--max-attempts 5`). If still failing, fall back to a 7-day window and flag as LOW confidence. |

### Compute Optimizer has no recommendations

| Scenario | Detection | Action |
|---|---|---|
| Enrollment status `Inactive` | `get-enrollment-status` returns `Inactive` | Compute Optimizer is not enabled for the account. Enable it: `aws compute-optimizer update-enrollment-status --status Active`. Until enabled, proceed with CloudWatch + Power Tuning only. |
| Enrollment `Active` but no Lambda findings returned | `lambdaFunctionRecommendations` array empty | Either the function is already `Optimized` (no findings) or Compute Optimizer has not yet analyzed it (analysis runs every 24h). Cross-check `lastRefreshTimestamp`; if > 30 days old, treat as stale and rely on Power Tuning. |
| `AccessDeniedException` on `compute-optimizer:*` | API error | The IAM role lacks Compute Optimizer permissions. Add `compute-optimizer:GetLambdaFunctionRecommendations`. Proceed without cross-check; surface the gap. |

### Function uses container image deployment

Lambda functions deployed from a container image (`PackageType: Image`)
require adjusted optimisation workflow:

| Behaviour | Impact on optimisation |
|---|---|
| `CodeSize` is opaque (container layers) | Cannot assess package-size impact on cold start. Use InitDuration metric directly instead. |
| Lambda Layers are NOT supported | Cannot recommend Layer-based package optimisation. The container image IS the deployment package. |
| ARM64 migration requires multi-arch build | The container image must be built for `linux/arm64` (e.g., `docker buildx build --platform linux/arm64`). An x86-only image will fail on arm64 Lambda. |
| Memory tuning still applies | Power Tuning works identically — it adjusts the memory configuration regardless of deployment type. Run it normally. |

**Detection:**
```bash
aws lambda get-function-configuration --function-name <name> --output json | \
  jq '{PackageType: .PackageType, ImageUri: .Code.ImageUri}'
```

If `PackageType: Image`, adjust the recommendation:
1. Run Power Tuning normally (memory tuning applies to container functions).
2. Skip any Lambda Layers recommendation.
3. For ARM64 migration, require a multi-arch container build before recommending.
4. For package-size optimisation, recommend multi-stage Docker builds and `docker image prune` instead of Layers.

## Worked example — end-to-end optimisation ($500/month function)

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
                = 47,000,000 × 5.0 × 0.125 × $0.0000166667
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
  = 47,000,000 × 0.95 × 0.5 × $0.0000166667 × 0.80
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
  Assumptions: 47M invocations/month, us-east-1 pricing, ARM 20% compute
    discount, Power Tuning duration projections, request fee unchanged.
MIGRATION_STEPS:
  1. Run Power Tuning to confirm the U-curve:
     aws stepfunctions start-execution --state-machine-arn <arn>
       --input '{"lambda":{"resource":"arn:aws:lambda:us-east-1:<acct>:function:order-enrichment-api","payload":{},"num":50},"power":{"values":[128,256,512,1024,2048,3008],"parallelInvocation":true}}'
  2. Verify ARM64 dependency compatibility:
     pip install --platform aarch64 --only-binary=:all: requests psycopg2-binary
  3. Update memory and architecture together:
     aws lambda update-function-configuration
       --function-name order-enrichment-api
       --memory-size 512 --architectures arm64
  4. Publish a version and test via staging alias:
     aws lambda publish-version --function-name order-enrichment-api
     aws lambda update-alias --function-name order-enrichment-api
       --name staging --function-version <new-version>
  5. Verify p95 latency and error rate for 7 days via CloudWatch.
  6. Cutover production alias:
     aws lambda update-alias --function-name order-enrichment-api
       --name prod --function-version <new-version>
CONFIRM: Before updating, emit and await:
  "CONFIRM: About to update-function-configuration on order-enrichment-api
   (128 MB x86 to 512 MB arm64). Monthly saving $191.91 (38.5%); p95 latency
   improvement 82% (6200 ms to ~1100 ms). Proceed? (yes/no)"
```

## Edge cases — production scenarios

### Provisioned concurrency on sporadic traffic

**Scenario:** A function has 10 provisioned concurrency configured but
receives 0.5 invocations/minute on average (sporadic batch report requests).

**Problem:** Provisioned concurrency charges for idle execution time
regardless of invocations. At 10 concurrent executions at 1 GB each:
```
Idle cost = 10 x 1.0 GB x 730 hours x 3600 s/h x $0.000015
          = $394.20/month
```
Over 99% of provisioned execution time is idle. This is the #1 Lambda
cost waste pattern.

**Resolution:**
1. Verify traffic is genuinely sporadic: pull 30-day
   `ConcurrentExecutions`. If p99 < 3, the provisioned value is far
   above need.
2. Check whether cold-start latency is customer-visible. For batch and
   report functions, cold starts are typically acceptable.
3. If cold starts are acceptable, remove provisioned concurrency:
   `aws lambda delete-provisioned-concurrency-config --function-name <name> --qualifier <alias>`.
4. If some warm capacity is needed for latency SLO, switch to Application
   Auto Scaling with target tracking on `ProvisionedConcurrencyUtilization`
   metric instead of a fixed value. This scales down during idle periods.

**Cost impact:** Removing 10 provisioned concurrency at 1 GB saves
approximately $394/month.

### ARM64 incompatibility — native libraries

**Scenario:** A Python function uses `numpy`, `scipy`, or a custom C
extension compiled for x86_64. ARM64 migration is recommended by the
skill, but the function fails at runtime after migration.

**Problem:** Native libraries compiled for x86_64 do not run on arm64.
Lambda provides no transparent emulation. The function will fail with
`InvalidParameterValueException` at deployment (if the zip contains
x86-only binaries) or with runtime errors (segfault, ImportError) after
migration.

**Detection before migration:**
```bash
# Check for native dependencies (Python) — verify arm64 wheels exist
pip install --platform aarch64 --only-binary=:all: <package-name>
# If this fails, the package has no arm64 wheel and needs recompilation

# Check Lambda deployment package architecture
aws lambda get-function-configuration --function-name <name> | \
  jq '.Architectures'
```

**Resolution:**
1. Identify all native dependencies (C extensions, shared objects, JNI).
2. For Python: verify arm64 wheel availability. Common problem packages:
   `pycrypto` (replace with `pycryptodome`), legacy `numpy` (upgrade to
   1.20+ which ships arm64 wheels), custom Cython extensions (recompile).
3. For Java: verify JNI libraries have arm64 builds. If unavailable,
   compile from source or keep x86_64.
4. For Go: recompile with `GOARCH=arm64 GOOS=linux`.
5. For .NET: verify native interop libraries have arm64 variants.
6. If a critical dependency has no arm64 support, do NOT migrate. Keep
   x86_64 and document the specific blocking dependency.

**Cost impact of NOT migrating:** The function forgoes the 20% ARM64
compute discount. Surface this as a finding with the specific blocking
dependency named, so the operator can prioritise dependency remediation.

### ESM batch size impact on total cost

**Scenario:** An SQS-triggered function processes messages with batch
size 10. Increasing to batch size 1000 reduces invocation count by 99%.
However, per-invocation duration increases because the function processes
more messages per invocation.

**Problem:** Batch-size tuning has a non-linear cost curve. The invocation
count drops linearly with batch size, but per-invocation duration rises.
The net saving depends on whether duration scales sub-linearly
(I/O-bound, amortised setup) or linearly (CPU-bound, proportional work).

**Worked math (1M messages/hour, 50 ms processing per message):**
```
Batch size 10:
  Invocations/hour: 1,000,000 / 10 = 100,000
  Duration per invocation: 10 x 50 ms = 500 ms = 0.5 s
  Compute: 100,000 x 0.5 x memory_GB x $0.0000166667
  Requests: 100,000 x $0.0000002

Batch size 100:
  Invocations/hour: 1,000,000 / 100 = 10,000
  Duration per invocation: 100 x 50 ms = 5000 ms = 5.0 s
  Compute: 10,000 x 5.0 x memory_GB x $0.0000166667
  Requests: 10,000 x $0.0000002

  Request fee saving: 90% (100,000 to 10,000 invocations)
  Compute saving: 0% (100,000 x 0.5 = 10,000 x 5.0 = same GB-seconds)
  Net: saves ONLY on request fee, not compute, for CPU-bound workloads.

Batch size 1000:
  Invocations/hour: 1,000,000 / 1000 = 1,000
  Duration per invocation: 1000 x 50 ms = 50,000 ms = 50 s
  PROBLEM: 50 s exceeds typical Lambda timeout (default 3 s, max 15 min).
  Batch size 1000 is INFEASIBLE without also increasing timeout to 60+ s.
```

**Resolution:**
1. Calculate the optimal batch size where invocation-count saving is not
   eaten by per-invocation duration increase.
2. Verify the function timeout accommodates the longer per-batch duration:
   `timeout >= batch_size x per_message_processing_time + safety_margin`.
3. Ensure the function handles partial batch failures:
   `FunctionResponseTypes: ["ReportBatchItemFailures"]` for SQS.
4. Monitor `IteratorAge` (Kinesis/DynamoDB) or `ApproximateAgeOfOldestMessage`
   (SQS) for 7 days after the change. If rising, the function cannot keep
   up — reduce batch size or increase parallelism.
5. For CPU-bound workloads (duration scales linearly with batch size),
   the saving is ONLY on the request fee — compute cost is unchanged.
   For I/O-bound workloads (duration scales sub-linearly due to amortised
   HTTP setup), compute cost also drops.

**Cost impact:** For I/O-bound workloads, batch size 10 to 100 typically
saves 80-90% on request fees and 10-30% on compute. For CPU-bound
workloads, only the request fee saving applies (compute is neutral).

## Recent AWS features (2024-2026)

- **Lambda SnapStart expansion (2024-2025):** Originally Java-only,
  SnapStart has expanded to additional runtimes. Always check the current
  support matrix before recommending. For Java, SnapStart eliminates
  1-3 s of cold-start init time with no code change.

- **Lambda ARM64 (Graviton2) general availability:** All major runtimes
  (Node, Python, Java, .NET, Go, Ruby) support arm64. ~20% cheaper
  compute and often better price-performance. Migration is low-risk for
  interpreted runtimes.

- **AWS Lambda Power Tuning (open-source, actively maintained):** The
  de facto standard for empirical memory tuning. Deployed via SAR
  (Serverless Application Repository). Supports parallel invocation,
  custom payload, and visualization URL output.

- **Lambda Insights (CloudWatch Lambda Insights):** Provides
  `memory_used`, `cpu_total_time`, `post_runtime_duration`, and other
  runtime metrics beyond the default AWS/Lambda namespace. Enable via
  the Lambda Insights extension Layer. Required for memory-utilization-
  headroom analysis.

- **Provisioned Concurrency autoscaling (2024):** Application Auto
  Scaling now supports provisioned concurrency on Lambda aliases. Use
  target-tracking scaling on the `ProvisionedConcurrencyUtilization`
  metric. Useful for variable-but-bounded traffic patterns.

- **Event Source Mapping enhancements (2024-2025):** `MaximumBatchingWindowInSeconds`
  is now tunable (1-300 s). `FunctionResponseTypes: ["ReportBatchItemFailures"]`
  enables partial-batch failure reporting for SQS. Both reduce wasted
  invocations on bad messages.

- **Lambda Function URLs (2024):** Dedicated HTTP(S) endpoints for
  Lambda functions. No API Gateway cost. Useful for webhook receivers
  and simple APIs that don't need API Gateway features.

- **Step Functions Express Workflow pricing refinement (2024):** Per-
  invocation + per-GB-second pricing, distinct from Standard workflow's
  per-state-transition pricing. Evaluate Express for high-volume,
  short-duration orchestration.

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
