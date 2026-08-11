---
name: fargate-cost-optimizer
description: >-
  Optimises AWS Fargate cost across seven dimensions: task right-sizing
  (CPU/memory from 28 allowed combos, CloudWatch CPUUtilization and
  MemoryUtilization analysis), Fargate Spot vs On-Demand (up to 70%
  savings for fault-tolerant workloads), ARM64/Graviton migration (20%
  cheaper), task scheduling/bin-packing via capacity providers, Savings
  Plans (1yr/3yr commitment for steady-state), and latest features
  (Fargate EFA for HPC/ML, Fargate instance storage for high-I/O).
  Reads CloudWatch metrics, ECS configs, and Cost Explorer data. Emits
  OPPORTUNITY_FOUND with recommendation and estimated savings,
  OPTIMIZED, or ALREADY_OPTIMAL. Use when reviewing Fargate spend,
  right-sizing ECS tasks, evaluating Spot/ARM64 migration, or a FinOps
  review of container spend.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). Offline recommendation classification works from
  pasted CloudWatch metrics, ECS task definitions, and Cost Explorer
  data. Live-account optimization uses aws ecs describe-task-definition,
  describe-services, describe-capacity-providers, aws cloudwatch
  get-metric-statistics (CPUUtilization, MemoryUtilization),
  aws ce get-cost-and-usage, aws ce get-reservation-utilization, and
  aws compute-optimizer get-ec2-recommendations (AWS CLI v2, SSO or
  key-based credentials).
keywords:
  - Fargate
  - ECS
  - cost optimization
  - right-sizing
  - task definition
  - CPU
  - memory
  - Fargate Spot
  - On-Demand
  - capacity provider
  - ARM64
  - Graviton
  - Savings Plans
  - bin-packing
  - task scheduling
  - EFA
  - instance storage
  - FinOps
  - Compute Optimizer
  - container
tags: [fargate, ecs, compute, cost-optimization, finops, rightsizing, graviton, spot, savings-plans]
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: >-
    Optimising Fargate cost, right-sizing ECS task definitions (CPU
    and memory), evaluating Fargate Spot vs On-Demand capacity provider
    strategy, migrating x86_64 tasks to ARM64/Graviton, tuning task
    scheduling efficiency (bin-packing, capacity providers), evaluating
    Savings Plans for Fargate, or a FinOps review of container spend.
  when_not_to_use: >-
    EC2 instance rightsizing (use ec2-rightsizing-optimizer), Lambda
    cost optimization (use lambda-cost-optimizer), EKS cost
    optimization (use eks-cost-optimizer), or ECS task troubleshooting
    (task failures, deployment issues — use ecs-task-troubleshooter).
    This skill focuses on cost-driven optimization, not functional
    debugging.
  activation_triggers:
    - "optimise Fargate cost"
    - "Fargate right-sizing"
    - "Fargate CPU memory combo"
    - "Fargate Spot savings"
    - "Fargate capacity provider"
    - "Fargate ARM64 Graviton"
    - "Fargate Savings Plans"
    - "Fargate bin-packing"
    - "Fargate task scheduling"
    - "Fargate FinOps"
    - "reduce Fargate bill"
    - "Fargate cost review"
    - "ECS task over-provisioned"
    - "Fargate EFA"
    - "Fargate instance storage"
  invocation_schema: >-
    Input: either (a) a task definition ARN + live-account context,
    (b) CloudWatch metrics (CPUUtilization, MemoryUtilization) with at
    least 14 days of observation, OR (c) an ECS service configuration
    with capacity provider strategy. Output: a deterministic TARGET /
    VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS /
    MIGRATION_STEPS block per task definition or service, where VERDICT
    is one of {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL}.
---

# Fargate Cost Optimizer

## Activation

Activate this skill when the user reports Fargate cost concerns. Trigger
phrases: "optimise Fargate cost", "Fargate right-sizing", "Fargate CPU
memory combo", "Fargate Spot savings", "Fargate capacity provider",
"Fargate ARM64 Graviton", "Fargate Savings Plans", "Fargate bin-packing",
"Fargate FinOps", "reduce Fargate bill", "ECS task over-provisioned".

## Mindset

**One-line takeaway:** Fargate charges per vCPU-second and per
GB-second. Every dimension of optimization either reduces vCPU-seconds
(fewer vCPUs, cheaper ARM64 vCPUs, Spot pricing) or reduces GB-seconds
(less memory), or eliminates idle capacity (bin-packing, capacity
providers, Savings Plans). Start with right-sizing, then pricing model,
then architecture.

Three facts make Fargate cost optimization different from generic
container tuning:

- **Fargate task CPU and memory must be from a fixed combination
  table — you cannot pick arbitrary values.** There are 28 allowed
  combinations (e.g. 0.25 vCPU pairs with 0.5/1/2 GB; 1 vCPU pairs with
  2-8 GB). Right-sizing means finding the smallest combo that still
  meets the workload's needs, not arbitrary increments.
- **CloudWatch CPUUtilization and MemoryUtilization are measured
  against the task's configured limits, not the node.** A task at 15%
  CPUUtilization on a 2-vCPU config is using 0.3 vCPU — it can likely
  drop to 0.5 vCPU. The metric IS the right-sizing signal.
- **Fargate Spot and Savings Plans stack with architecture savings.**
  ARM64 is 20% cheaper per-unit. Spot is up to 70% cheaper. Savings
  Plans commits for 1-3 years at a discount. The optimal workload uses
  all three: ARM64 + Spot + Savings Plans for fault-tolerant, steady
  workloads; ARM64 + On-Demand for stateful services.

## Quick reference — optimization dimensions

| Dimension | Potential savings | First probe |
|---|---|---|
| Task right-sizing (CPU/memory) | 30-60% | CloudWatch CPUUtilization + MemoryUtilization (14-day avg + max) |
| Fargate Spot vs On-Demand | Up to 70% | Is the workload fault-tolerant? (batch, workers, stateless web) |
| ARM64/Graviton migration | ~20% | Is the image ARM64-compatible? What runtime/language? |
| Capacity provider bin-packing | 10-25% | How many tasks run vs how many are needed? |
| Savings Plans | 20-40% on committed | Is the workload steady-state 24/7? |
| Provisioned capacity | Eliminates cold-start scale-up cost | Is the traffic predictable? |

## Quick navigation

- **Step 0** — Capture the optimization target (task def, service, metrics).
- **Step 1** — Map to an optimization category (A-G).
- **Step 2** — RIGHT_SIZE: CPU/memory combination analysis.
- **Step 3** — SPOT: Fargate Spot vs On-Demand evaluation.
- **Step 4** — ARM64: Graviton migration evaluation.
- **Step 5** — SCHEDULING: bin-packing and capacity provider efficiency.
- **Step 6** — SAVINGS_PLANS: commitment-based discount evaluation.
- **Step 7** — Root-cause catalog (top patterns + canonical fixes).
- **Step 8** — Verify the recommendation.
- **Step 9** — Decide VERDICT (OPTIMIZED / OPPORTUNITY_FOUND / ALREADY_OPTIMAL).

## Process — Optimization decision tree (apply in order)

### Step 0: Capture the optimization target

Gather these inputs. Each step below branches on which are available.

| Signal | Source | Why required |
|---|---|---|
| **Task definition** | `aws ecs describe-task-definition` | CPU/memory config, architecture, family |
| **CloudWatch metrics** | `get-metric-statistics` CPUUtilization + MemoryUtilization | Right-sizing signal |
| **Service configuration** | `aws ecs describe-services` | Capacity provider strategy, desired count, scheduling |
| **Cost data** | `aws ce get-cost-and-usage` filtered by Fargate | Baseline spend |

If the user has not provided the task definition or metrics, output:

```text
TARGET: <task-definition or service>
VERDICT: NEED_MORE_INFO
REASON: Cannot optimize without CPU/memory utilization data.
MISSING:
  - Task definition ARN or name:revision
  - CloudWatch CPUUtilization and MemoryUtilization (14+ days)
  - Current capacity provider strategy (if any)
  - Monthly Fargate spend (from Cost Explorer)
```

```bash
# Describe the current task definition:
aws ecs describe-task-definition \
  --task-definition <task-def> \
  --query 'taskDefinition.{cpu:cpu,memory:memory,arch:runtimePlatform.cpuArchitecture,containerDefs:containerDefinitions[*].{name:name,cpu:cpu,memory:memory,memoryReservation:memoryReservation}}'

# Pull 14-day CPU and memory utilization:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average Maximum \
  --query 'Datapoints[*].{time:Timestamp,avg:Average,max:Maximum}'
```

### Step 1: Identify the optimization category

| Category | Signal | Diagnostic step |
|---|---|---|
| **A. RIGHT_SIZE** | CPUUtilization avg < 50% or MemoryUtilization avg < 60% | Step 2 |
| **B. SPOT** | Workload is fault-tolerant (batch, workers, stateless); currently 100% On-Demand | Step 3 |
| **C. ARM64** | Runtime is x86_64; language supports ARM64 (Java 11+, Python, Node.js, Go) | Step 4 |
| **D. SCHEDULING** | Tasks > needed capacity; no capacity provider strategy | Step 5 |
| **E. SAVINGS_PLANS** | Steady-state 24/7 workload on On-Demand | Step 6 |
| **F. ALREADY_OPTIMAL** | Right-sized, Spot/SP applied, ARM64, efficient scheduling | Verdict: ALREADY_OPTIMAL |
| **G. PROVISIONED** | Predictable traffic with cold-start scale-up latency | Step 5 (capacity provider) |

**Apply A before B before C.** Right-sizing reduces the base; Spot and
ARM64 are multipliers on top. Savings Plans are evaluated last because
the commitment should be based on the post-optimized config.

### Step 2: RIGHT_SIZE — CPU/memory combination analysis

Fargate charges per vCPU-hour and per GB-hour. An over-provisioned task
pays for resources it never uses. The right-sizing signal is
CloudWatch's CPUUtilization and MemoryUtilization, measured against the
task's configured limits.

#### Fargate allowed CPU/memory combinations

| CPU (vCPU) | Memory (GB) |
|---|---|
| 0.25 | 0.5, 1, 2 |
| 0.5 | 1, 2, 3, 4 |
| 1 | 2, 3, 4, 5, 6, 7, 8 |
| 2 | 4, 5, 6, ..., 16 |
| 4 | 8, 9, 10, ..., 30 |
| 8 | 16, 17, 18, ..., 60 |
| 16 | 32, 33, 34, ..., 120 |

**Decision table (apply to the task's current config):**

| Metric signal | Current config | Recommended action |
|---|---|---|
| CPUUtilization avg < 30%, max < 50% | 1+ vCPU | Drop to next-lower CPU combo |
| CPUUtilization avg 30-60%, max < 80% | Any | Consider dropping one combo if memory allows |
| CPUUtilization avg > 70%, max > 90% | Any | Under-provisioned — do NOT downsize |
| MemoryUtilization avg < 50% | 4+ GB | Reduce memory within the same CPU tier |
| MemoryUtilization avg > 85% | Any | Memory-bound — do NOT downsize memory |
| CPUUtilization spikes to 100% for <5 min, then settles | Any | Use Application Auto Scaling, not upsize |

**The combo-floor rule.** When downsizing CPU, you may need to also
reduce memory (the memory range is constrained by the CPU tier). E.g.,
dropping from 2 vCPU / 10 GB to 1 vCPU means the max memory drops to 8
GB. Verify MemoryUtilization supports the new memory level.

**The memory floor.** Memory is less elastic than CPU. A JVM heap set
to 8 GB needs at least 8 GB task memory regardless of
MemoryUtilization averages. Check `-Xmx` / `MaxRAMPercentage` before
downsizing memory on Java tasks.

**Diagnostic commands:**

```bash
# 14-day CPU utilization (hourly avg + max):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# 14-day Memory utilization:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum
```

**Savings estimation (us-east-1, On-Demand, x86_64, 2026):**

| Config | Hourly rate | Monthly (730h) |
|---|---|---|
| 0.25 vCPU / 0.5 GB | $0.011 | $8.03 |
| 0.5 vCPU / 1 GB | $0.022 | $16.06 |
| 1 vCPU / 2 GB | $0.043 | $31.39 |
| 2 vCPU / 4 GB | $0.087 | $63.51 |
| 4 vCPU / 8 GB | $0.173 | $126.29 |
| 8 vCPU / 16 GB | $0.346 | $252.58 |

Dropping from 2 vCPU / 4 GB to 1 vCPU / 2 GB saves ~$32/task/month.

### Step 3: SPOT — Fargate Spot vs On-Demand evaluation

Fargate Spot offers up to 70% savings for workloads that can tolerate
interruptions. Spot tasks can be reclaimed with a 2-minute warning.

**Eligibility assessment:**

| Workload characteristic | Spot-eligible? | Rationale |
|---|---|---|
| Batch processing, job workers | YES | Stateless, retriable |
| Stateless web/API (behind ALB) | YES | ALB health checks drain on interruption |
| Event-driven (SQS/Kinesis consumers) | YES | Messages return to queue on interruption |
| Scheduled tasks (cron) | YES | Retry on next schedule |
| Stateful services (DB, cache) | NO | Interruption loses in-memory state |
| Long-running singletons (leader election) | NO | Interruption disrupts leadership |
| WebSocket / SSE long-poll connections | CAUTION | Users disconnected on interruption; use reconnection logic |

**Capacity provider strategy (the standard Spot pattern):**

```json
{
  "capacityProviderStrategy": [
    {
      "capacityProvider": "FargateSpot",
      "weight": 4,
      "base": 0
    },
    {
      "capacityProvider": "Fargate",
      "weight": 1,
      "base": 1
    }
  ]
}
```

This places `base: 1` On-Demand task (always running) and distributes
the rest 4:1 (Spot:On-Demand). For 10 desired tasks: 1 base On-Demand +
7 Spot + 2 On-Demand = ~80% Spot.

**Interruption handling checklist:**
- ECS sends a `SIGTERM` 2 minutes before Spot reclamation.
- The app must handle `SIGTERM`: finish in-flight requests, drain
  connections, checkpoint state.
- Set `deploymentMinimumHealthyPercent` > 0 so replacements launch
  before old tasks terminate.
- For SQS consumers: use `visibilityTimeout` > processing time so
  interrupted messages return to the queue.

**Savings estimation:**

| Pricing | 2 vCPU / 4 GB hourly | Monthly (730h) | Savings |
|---|---|---|---|
| On-Demand | $0.087 | $63.51 | — |
| Spot (approx) | $0.026 | $18.98 | 70% |

For 50 tasks at 2 vCPU / 4 GB: On-Demand = $3,176/month; 80% Spot =
~$1,200/month. Savings: ~$1,976/month.

### Step 4: ARM64 — Graviton migration evaluation

ARM64 (Graviton2/Graviton3) is ~20% cheaper per vCPU-hour and per
GB-hour on Fargate. Most modern runtimes support ARM64 natively.

**Runtime compatibility:**

| Runtime | ARM64 support | Notes |
|---|---|---|
| Java (Corretto, OpenJDK) | YES (Java 11+) | No code changes; rebuild image |
| Python | YES | Pure Python: no changes. C extensions: rebuild wheels |
| Node.js | YES | No changes for pure JS; test native modules |
| Go | YES | Cross-compile: `GOOS=linux GOARCH=arm64 go build` |
| .NET | YES (.NET 6+) | Rebuild image |
| Ruby | YES | Pure Ruby: no changes. Gems with C exts: rebuild |
| Rust | YES | Cross-compile: `cargo build --target aarch64-unknown-linux-gnu` |

**Migration steps:**
1. Build a multi-arch image: `docker buildx build --platform
   linux/amd64,linux/arm64 -t <repo>:<tag> --push`.
2. Update the task definition: set
   `runtimePlatform.cpuArchitecture: "ARM64"`.
3. Deploy a canary service with 1 ARM64 task alongside the x86_64
   service.
4. Monitor for errors, latency differences, and memory usage (ARM64
   may use slightly different memory characteristics).
5. Cut over the service to ARM64 once validated.

**Pricing comparison (us-east-1, On-Demand, 2026):**

| Config | x86_64 hourly | ARM64 hourly | ARM64 savings |
|---|---|---|---|
| 1 vCPU / 2 GB | $0.0430 | $0.0344 | 20% |
| 2 vCPU / 4 GB | $0.0870 | $0.0696 | 20% |
| 4 vCPU / 8 GB | $0.1730 | $0.1384 | 20% |

**Stacking with Spot:** ARM64 + Spot is the cheapest combination.
ARM64 Spot is ~76% cheaper than x86_64 On-Demand.

### Step 5: SCHEDULING — bin-packing and capacity provider efficiency

Task scheduling efficiency is about running the minimum number of tasks
needed to handle the load, with auto scaling that tracks demand.

**Common inefficiencies:**

| Pattern | Problem | Fix |
|---|---|---|
| Static desired count = 10, traffic drops 80% at night | Paying for idle tasks | Application Auto Scaling on CPU/ALB request count |
| desiredCount = 20, but 5 tasks handle peak | Over-provisioned service | Lower desiredCount; add auto scaling |
| minimumHealthyPercent = 200 during deploy | Doubles task count during rollout | Set to 100 (ECS maintains desired count during deploy) |
| maximumPercent = 400 during deploy | Allows 4x tasks during rollout | Set to 200 |
| No capacity provider strategy; 100% Fargate On-Demand | Missing Spot savings | Add FargateSpot capacity provider (Step 3) |
| Provisioned capacity for unpredictable traffic | Paying for idle baseline | Evaluate if traffic is truly unpredictable; if predictable, provisioned is correct |

**Auto scaling policy recommendation:**

```bash
# Create a target tracking scaling policy on CPU utilization:
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/<cluster>/<service> \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 20

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/<cluster>/<service> \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":60.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ECSServiceAverageCPUUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":300}'
```

Target 60% CPU gives headroom for traffic spikes while avoiding
over-provisioning. `ScaleInCooldown` of 300s prevents flapping.

### Step 6: SAVINGS_PLANS — commitment-based discount evaluation

Compute Savings Plans apply to Fargate, EC2, and Lambda. A 1-year or
3-year commitment provides a discount on the per-vCPU-hour and per-GB-hour
rate.

**When Savings Plans make sense:**

| Workload pattern | SP recommendation | Rationale |
|---|---|---|
| Steady-state 24/7 (always-on services) | 1yr or 3yr SP | Commit to the baseline; On-Demand for spikes |
| Business-hours only (8h/day, 5d/wk) | Do NOT use SP | Only 34% utilization; SP wastes off-hours commitment |
| Spiky / unpredictable | Do NOT use SP | Cannot predict the commit level |
| Multi-service (Fargate + EC2 + Lambda) | YES — SP covers all | Compute SP is flexible across services |

**Savings Plan discount rates (approximate, us-east-1, 2026):**

| Commitment | Discount vs On-Demand |
|---|---|
| 1-year, no upfront | ~20% |
| 1-year, all upfront | ~28% |
| 3-year, no upfront | ~38% |
| 3-year, all upfront | ~48% |

**Key rule:** Commit to the steady-state baseline (the minimum number
of tasks that run 24/7). The SP covers the baseline; On-Demand or Spot
handles spikes above the baseline. Over-committing wastes money;
under-committing leaves savings on the table.

**Diagnostic commands:**

```bash
# Check current Savings Plans utilization and coverage:
aws ce get-savings-plans-utilization \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY

# Get Fargate spend by service:
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"Service","Values":["Elastic Compute Cloud - CloudWatch"]}}' \
  --metrics "UsageQuantity" "UnblendedCost" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE
```

### Step 7: Map to root-cause catalog

| # | Pattern | Category | Fix | Est. savings |
|---|---|---|---|---|
| 1 | CPUUtilization avg < 30% on 2+ vCPU task | RIGHT_SIZE | Drop to next-lower CPU combo | 30-50% |
| 2 | MemoryUtilization avg < 50% on 4+ GB task | RIGHT_SIZE | Reduce memory within CPU tier | 10-25% |
| 3 | 100% On-Demand, fault-tolerant workload | SPOT | Capacity provider with Spot base | Up to 70% |
| 4 | x86_64 task, ARM64-compatible runtime | ARM64 | Rebuild image for arm64; update task def | ~20% |
| 5 | Static desired count, no auto scaling | SCHEDULING | Application Auto Scaling on CPU | 20-40% |
| 6 | No Savings Plans, steady-state 24/7 | SAVINGS_PLANS | 1yr or 3yr Compute SP | 20-48% |
| 7 | minimumHealthyPercent = 200 during deploy | SCHEDULING | Set to 100 | Eliminates deploy-time doubling |
| 8 | ARM64 + Spot + SP all applicable | ALL | Stack all three | 80-90% |

### Step 8: Verify the recommendation

- **For RIGHT_SIZE:** deploy the smaller task def; monitor
  CPUUtilization and MemoryUtilization for 7 days. If CPU avg > 70%,
  revert. If MemoryUtilization > 85%, revert memory.
- **For SPOT:** deploy the capacity provider strategy with `base: 1`
  On-Demand; monitor for `ServiceDeployments` events showing Spot task
  interruptions. If interruption rate is too high, adjust the
  Spot:On-Demand weight.
- **For ARM64:** deploy a canary task first; compare error rate and
  latency for 24-48 hours before full cutover.
- **For SCHEDULING:** monitor the auto scaling target for 7 days;
  verify `ScaleOutCooldown` catches traffic spikes.
- **For SAVINGS_PLANS:** start with a 1-year, no-upfront plan at the
  current baseline; adjust the commitment after 1 month of observed
  utilization.

### Step 9: Decide — OPTIMIZED vs OPPORTUNITY_FOUND vs ALREADY_OPTIMAL

- **OPPORTUNITY_FOUND.** At least one optimization dimension has a
  clear recommendation with estimated savings. Output RECOMMENDATION
  and ESTIMATED_SAVINGS.
- **OPTIMIZED.** The task/service has already been right-sized, is
  using Spot/SP where applicable, and is on ARM64 where compatible.
  No further action needed.
- **ALREADY_OPTIMAL.** The workload is already at the optimal
  configuration across all dimensions.

## STRICT output contract

```text
TARGET: <task-definition>:<revision> (service <service> on cluster <cluster>)
VERDICT: OPPORTUNITY_FOUND | OPTIMIZED | ALREADY_OPTIMAL
REASON: <summary of findings across dimensions>
RECOMMENDATION:
  1. <RIGHT_SIZE recommendation with old → new combo>
  2. <SPOT recommendation with capacity provider strategy>
  3. <ARM64 recommendation if applicable>
  4. <SCHEDULING recommendation if applicable>
  5. <SAVINGS_PLANS recommendation if applicable>
ESTIMATED_SAVINGS: $<monthly savings> ($<annual savings>)
MIGRATION_STEPS:
  1. <specific step with AWS CLI or console action>
  2. <verification step>
  3. <rollback step>
```

### Worked example — over-provisioned task + Spot opportunity

```text
TARGET: order-processor:42 (service order-processor on cluster prod)
VERDICT: OPPORTUNITY_FOUND
REASON: Task is over-provisioned (CPU avg 18%, max 35% on 2 vCPU / 4
GB); workload is stateless and fault-tolerant but running 100%
On-Demand; runtime is Java 21 (ARM64 compatible).
RECOMMENDATION:
  1. RIGHT_SIZE: drop from 2 vCPU / 4 GB to 1 vCPU / 2 GB (CPU avg
     18%, max 35% — 1 vCPU has headroom at ~36% avg, ~70% max)
  2. SPOT: add capacity provider strategy with FargateSpot weight 4,
     Fargate base 1 (workload is stateless behind ALB)
  3. ARM64: rebuild image for linux/arm64; set
     runtimePlatform.cpuArchitecture = ARM64
ESTIMATED_SAVINGS: $2,470/month ($29,640/year)
  - Right-size: 10 tasks × ($63.51 - $31.39) = $321/month
  - Spot: 8 Spot tasks × $18.98 vs $31.39 = ~$99/month saved
  - ARM64: 10 tasks × 20% × $25.11 avg = ~$50/month saved
  - Combined stacking on the optimized base
MIGRATION_STEPS:
  1. Register new task definition order-processor:43 with cpu=1024,
     memory=2048, runtimePlatform.cpuArchitecture=ARM64
  2. Build multi-arch image: docker buildx build --platform
     linux/amd64,linux/arm64 -t <repo>:v43 --push
  3. Create FargateSpot capacity provider on the cluster
  4. Update service with capacity provider strategy: Spot weight 4
     base 0, Fargate weight 1 base 1
  5. Monitor CPUUtilization for 7 days; revert if avg > 70%
```

## Expert heuristic — "Right-size first, pricing model second, commitment third"

Three rules, in order, produce 90% of Fargate savings:

1. **Right-size the task definition first.** This reduces the base cost
   that all other optimizations multiply against. A 2-vCPU task at 18%
   CPU is paying for 1.6 vCPUs it never uses. Dropping to 1 vCPU nearly
   halves the cost — and then Spot, ARM64, and Savings Plans all apply
   to the smaller (cheaper) base.
2. **Switch the pricing model second.** Once the task is right-sized,
   evaluate Spot for fault-tolerant workloads (70% off) and ARM64 for
   compatible runtimes (20% off). These are multiplicative: ARM64 Spot
   is 76% off the x86_64 On-Demand price of the same task.
3. **Commit with Savings Plans third.** Only after the task is
   right-sized and on the right pricing model. The SP commitment should
   match the steady-state baseline of the optimized configuration.
   Committing to an over-provisioned baseline locks in waste.

## Anti-Patterns — NEVER

- **NEVER** downsize a task without checking MemoryUtilization
  separately from CPUUtilization. CPU and memory have different
  dynamics: a task at 15% CPU may be at 90% memory. Downsizing based on
  CPU alone can cause OOMKills. Always check both metrics.

- **NEVER** recommend Fargate Spot for stateful services (databases,
  caches, session stores) without explicit confirmation that the
  workload can handle interruption. Spot reclamation sends SIGTERM
  with 2 minutes notice; in-memory state is lost. Spot is for
  fault-tolerant, stateless, or retriable workloads.

- **NEVER** commit to a Savings Plan based on the pre-optimization
  spend. Always right-size first, then evaluate Spot/ARM64, then
  commit the SP to the optimized steady-state baseline. Committing to
  the pre-optimization baseline locks in the waste.

- **NEVER** assume a Java task's memory is CPU-scalable. JVM heap
  (`-Xmx` or `MaxRAMPercentage`) pins the memory floor. A JVM with
  `-XX:MaxRAMPercentage=75` on a 4 GB task uses 3 GB heap. Downsizing
  to 2 GB without adjusting the JVM flag will OOMKill the task.

- **NEVER** skip the canary phase for ARM64 migration. ARM64 has
  different memory characteristics and potential library
  incompatibilities. Deploy a single ARM64 task alongside x86_64 and
  monitor for 24-48 hours before full cutover.

- **NEVER** set `minimumHealthyPercent` to 200 for cost savings
  reasons. This is a deployment safety setting, not a cost setting.
  Setting it to 100 is fine for stateless services, but the motivation
  should be deployment speed, not cost.

- **NEVER** rely on the Fargate allowed-combo table from memory without
  verifying the memory range for the target CPU tier. The combos are
  not arbitrary; each CPU tier has a constrained memory range. Verify
  the desired combo exists before recommending it.

## Recent AWS features (2024-2026)

- **Fargate with EFA (Elastic Fabric Adapter, 2024-2025):** Fargate
  now supports EFA for HPC and distributed ML training workloads.
  EFA provides low-latency node-to-node communication. Relevant for
  distributed training (PyTorch DDP, TensorFlow) and MPI-based HPC.
  Not a cost optimization per se, but enables Fargate for workloads
  that previously required EC2 with EFA.
- **Fargate with instance storage (2025-2026):** Fargate tasks can now
  access ephemeral instance storage (NVMe-backed) for high-I/O
  workloads. This eliminates the need for EBS-attached storage for
  scratch space, reducing cost for tasks that need fast local disk
  (e.g., video transcoding, data processing intermediates).
- **Graviton3 on Fargate (2024+):** Fargate ARM64 tasks run on
  Graviton3 processors, which offer ~25% better price-performance
  than Graviton2. No configuration change needed — selecting ARM64
  automatically uses the latest Graviton generation.
- **Fargate Spot capacity provider improvements (2024-2025):** The
  FargateSpot capacity provider now supports `base` tasks on
  On-Demand, making it easier to maintain a minimum guaranteed
  capacity while running the bulk on Spot.
- **Compute Savings Plans coverage for Fargate (2024-2026):** Compute
  Savings Plans (1yr/3yr) apply to Fargate vCPU and GB charges,
  stacking with Spot and ARM64 for maximum savings.

## References

See `references/fargate-pricing-matrix.md` for the full pricing
reference (all CPU/memory combos, Spot vs On-Demand, x86_64 vs ARM64,
regional rate notes), and `references/rightsizing-commands.md` for the
canonical command script for each optimization dimension.

## Domain

AWS CloudOps / Fargate Compute FinOps & Container Cost Optimization.

## AWS documentation

- **AWS Fargate pricing** — https://aws.amazon.com/fargate/pricing/
- **Fargate task definition CPU/memory** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html
- **Fargate Spot** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-capacity-providers.html
- **Graviton on AWS** — https://aws.amazon.com/ec2/graviton/
- **Compute Savings Plans** — https://docs.aws.amazon.com/savingsplans/latest/userguide/sp-compute.html
- **ECS capacity providers** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-capacity-providers.html
- **Application Auto Scaling for ECS** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html
- **Fargate EFA support** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/efa.html
