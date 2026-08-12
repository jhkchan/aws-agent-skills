---
name: ecs-task-cost-optimizer
description: 'Optimises Amazon ECS task cost across seven dimensions: launch type selection (Fargate per-second pricing vs
  EC2 break-even at ~30% steady utilization — EC2 wins for always-on workloads, Fargate wins for bursty or <30% utilization),
  Graviton2 (arm64) migration for 20% cost reduction with compatibility verification, task definition right-sizing via CloudWatch
  Container Insights CPU/memory utilization analysis, capacity provider strategy (spot base capacity + on-demand top for 30-70%
  spot savings), Savings Plan coverage mapping (compute SP applies to both Fargate and EC2-backed ECS), task placement bin-packing
  strategy (spread vs binpack for EC2 density), and auto-scaling target tracking tuning. Evaluates standalone task vs service
  scheduling, process vs daemon scheduling, EFS vs EBS persistent storage cost, and service auto-scaling vs scheduled scaling.
  Emits OPTIMIZED when all dimensions pass, or FURTHER_OPTIMIZATION_AVAILABLE with specific recommendation and estimated savings.
  Use when reviewing ECS spen...'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification
  works from pasted CloudWatch Container Insights metrics, task definition configs, and Cost Explorer findings. Live-account
  optimization uses aws ecs describe-services, aws ecs describe-tasks, aws ecs describe-task-definition, aws ecs describe-capacity-providers,
  aws cloudwatch get-metric-statistics (CPUUtilization, MemoryUtilization from ECS/ContainerInsights), aws ce get-cost-and-usage
  (AWS CLI v2, SSO or key-based credentials). Pricing references us-east-1 published rates as of 2026; re-state regional rates
  from the reference matrix for other regions.
keywords:
- ECS
- Fargate
- EC2 launch type
- cost optimization
- Graviton2
- arm64
- task definition
- right-sizing
- capacity provider
- spot
- on-demand
- Savings Plan
- bin-packing
- task placement
- Container Insights
- auto-scaling
- target tracking
- scheduled scaling
- EFS
- EBS
- FinOps
- container cost
tags:
- ecs
- compute
- containers
- cost-optimization
- finops
- fargate
- graviton
- capacity-provider
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
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising ECS task cost, evaluating Fargate vs EC2 launch type crossover, planning a Graviton2 (arm64) task
    migration, right-sizing task definitions from Container Insights, designing capacity provider strategy (spot + on-demand),
    mapping Savings Plan coverage to ECS spend, tuning task placement bin-packing for EC2 density, or tuning auto-scaling
    target tracking for cost.
  when_not_to_use: EKS cost optimization (use eks-cost-optimizer), Fargate standalone cost optimization without ECS (use fargate-cost-optimizer),
    ECS task troubleshooting (container crashes, deployment failures, task lifecycle issues — use ecs-task-troubleshooter),
    or ECS task definition security auditing (use ecs-task-definition-auditor). This skill focuses on cost-driven optimization
    of ECS tasks, not functional debugging.
  activation_triggers:
  - optimise ECS cost
  - ECS Fargate vs EC2
  - ECS launch type crossover
  - ECS Graviton2 migration
  - ECS arm64 compatibility
  - ECS task right-sizing
  - ECS task definition CPU memory
  - ECS capacity provider strategy
  - ECS spot capacity provider
  - ECS Savings Plan coverage
  - ECS task placement bin-packing
  - ECS Container Insights cost
  - ECS auto-scaling target tracking
  - ECS scheduled scaling
  - ECS standalone task vs service
  - ECS EFS vs EBS storage
  - ECS FinOps
  - reduce container bill
  - ECS cost review
  invocation_schema: 'Input: either (a) an ECS service/task identifier + live-account context, (b) a Cost Explorer ECS/Fargate
    charge breakdown, OR (c) CloudWatch Container Insights metrics (CPUUtilization, MemoryUtilization) with task definition
    details and at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS
    block per service/task, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline finding classification):\nServiceName: order-api-prod\nLaunchType: FARGATE\n\
    TaskDefinition: order-api:42\nCPU: 1024 (1 vCPU)\nMemory: 2048 MB\nRegion: us-east-1\nArchitecture: x86_64\nMetrics (last\
    \ 30 days):\n  - CPUUtilization avg: 12%, p95: 25%\n  - MemoryUtilization avg: 18%, p95: 30%\n  - RunningTaskCount avg:\
    \ 8\nCost (last month): $1,847.00 (Fargate compute)\nEmit the standard optimization block (TARGET, VERDICT, REASON,\n\
    RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# ECS Task Cost Optimizer

## What this skill does

Translates an ECS task or service's runtime posture into a concrete
cost-optimization recommendation with a dollar-denominated savings
estimate. The verdict reflects the highest-leverage action across seven
dimensions — launch type, architecture, right-sizing, capacity provider
strategy, Savings Plan coverage, task placement, and auto-scaling —
applied in priority order. Always pairs the recommendation with exact
CLI commands or infrastructure-as-code snippets.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why launch type is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a service |
| Pre-flight data gate | Container Insights, Cost Explorer | Before any recommendation |
| Step 0 non-obvious behaviours | Fargate billing, Graviton compat, SP scoping | Edge cases |
| Step 1 Launch type | Fargate vs EC2 crossover at ~30% | Always-on vs bursty |
| Step 2 Architecture (Graviton2) | arm64 20% discount + compat check | Cross-cutting savings |
| Step 3 Task right-sizing | CPU/memory from Container Insights | The headline savings dimension |
| Step 4 Capacity provider strategy | spot base + on-demand top | Spot savings |
| Step 5 Savings Plan coverage | Compute SP for Fargate + EC2 | Commitment discount |
| Step 6 Task placement & scheduling | binpack, spread, daemon, standalone | EC2 density |
| Step 7 Auto-scaling tuning | target tracking, scheduled scaling | Over-provisioning |
| Step 8 Impact estimation | The cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, canary deploy | Before any apply CLI |

## Quick start

- **Launch type is the #1 lever.** Fargate charges per-second (1-minute
  minimum); EC2 charges per-second (60-second minimum) but requires
  capacity management. For always-on workloads at >30% steady
  utilization, EC2 backing is cheaper. For bursty or <30% utilization,
  Fargate avoids paying for idle compute.
- **Cost formula — Fargate (memorise this):**
  `cost = (vCPU_hours × $0.04048) + (GB_hours × $0.004445)`
  Per-second after 1-minute minimum. vCPU and memory billed independently.
- **Cost formula — EC2-backed ECS:**
  `cost = EC2_instance_hourly (regardless of task count)`
  The ECS surcharge is $0; you pay for the EC2 instances in the cluster.
- **Graviton2 (arm64) is a free 20%.** arm64 task definitions cost ~20%
  less on both Fargate and EC2 (Graviton instances). Check application
  compatibility (compiled binaries, JNI, native libs) before migrating.
- **Spot capacity providers save 30-70%.** For fault-tolerant workloads,
  a spot base capacity provider with an on-demand top provider delivers
  the best cost profile. Never use spot for stateful single-instance
  services.

## Mindset

ECS cost optimization is a utilization-and-commitment exercise. The goal
is the launch type, architecture, task size, and capacity strategy that
minimizes dollar cost while preserving availability and latency SLOs.

Four principles guide every recommendation:

- **The Fargate-EC2 crossover is workload-specific.** Fargate's premium
  over EC2 is roughly 30-50% for always-on workloads. Below ~30%
  steady utilization, Fargate's per-second billing wins because you
  don't pay for idle hosts. Above ~30%, EC2's lower base rate wins.
- **Right-sizing compounds.** An over-provisioned task (1024 CPU at 10%
  utilization) on Fargate costs 4x what it should. On EC2, it wastes
  cluster capacity that could pack additional tasks. Either way, the
  cost leak is proportional to the over-allocation.
- **Commitment discounts stack on top of optimization.** A Compute
  Savings Plan applies to both Fargate and EC2-backed ECS. Apply it
  AFTER right-sizing and architecture migration — committing to
  over-provisioned spend locks in waste.
- **Spot is a strategy, not a setting.** Spot capacity requires
  divergence handling (connection draining, request hedging, graceful
  shutdown). A capacity provider strategy with spot base + on-demand
  top is the production-grade pattern.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Launch type = FARGATE AND steady utilization > 30% AND always-on service | **FURTHER_OPTIMIZATION_AVAILABLE** (launch type) | Step 1 — migrate to EC2-backed capacity provider |
| Launch type = EC2 AND steady utilization < 15% AND bursty/ephemeral workload | **FURTHER_OPTIMIZATION_AVAILABLE** (launch type) | Step 1 — migrate to Fargate |
| Architecture = x86_64 AND application is arm64-compatible (interpreted lang, arm64 native libs) | **FURTHER_OPTIMIZATION_AVAILABLE** (architecture) | Step 2 — migrate to arm64 (Graviton2) |
| CPUUtilization avg < 30% of allocated CPU AND task CPU > 256 (0.25 vCPU) | **FURTHER_OPTIMIZATION_AVAILABLE** (right-size) | Step 3 — reduce CPU allocation |
| MemoryUtilization avg < 30% of allocated memory AND task memory > 512 MB | **FURTHER_OPTIMIZATION_AVAILABLE** (right-size) | Step 3 — reduce memory allocation |
| No spot capacity provider configured AND workload is stateless/fault-tolerant | **FURTHER_OPTIMIZATION_AVAILABLE** (spot) | Step 4 — add spot base capacity provider |
| No Savings Plan covering ECS spend AND monthly ECS charge > $2,000 (steady) | **FURTHER_OPTIMIZATION_AVAILABLE** (commitment) | Step 5 — purchase Compute Savings Plan |
| EC2 cluster with spread placement AND avg instance utilization < 60% | **FURTHER_OPTIMIZATION_AVAILABLE** (placement) | Step 6 — switch to binpack placement |
| All dimensions verified AND architecture on arm64 AND task right-sized AND SP coverage in place | **OPTIMIZED** | None — continue monitoring |
| Container Insights metrics absent or window < 14 days | **NEED_MORE_INFO** | Enable Container Insights, wait 14 days |
| All dimensions verified AND a change was applied and confirmed this session | **OPTIMIZED** | Emit post-state verification |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/ecs-pricing-and-capacity-providers.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Service/task configuration: `aws ecs describe-services`, `aws ecs describe-task-definition`
2. CPU + Memory utilization (14-30 day window): `aws cloudwatch get-metric-statistics --namespace ECS/ContainerInsights`
3. Capacity providers: `aws ecs describe-capacity-providers`
4. Running task count: `aws cloudwatch get-metric-statistics --metric-name RunningTaskCount`
5. EC2 instance utilization (if EC2-backed): `aws cloudwatch get-metric-statistics --namespace AWS/EC2`
6. Savings Plan coverage: `aws savingsplans describe-savings-plans-coverage`
7. Cost Explorer breakdown: `aws ce get-cost-and-usage --service Amazon Elastic Container Service`

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `CPUUtilization` metric absent (Container Insights not enabled) | **NEED_MORE_INFO**. Enable: `aws ecs update-cluster-settings --settings name=containerInsights,value=enabled`. |
| Metrics window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| `RunningTaskCount` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "dormant service." |
| Service `desiredCount = 0` | Skip optimization; surface as dormant. |
| Cost Explorer breakdown absent | Proceed with Fargate pricing formula; mark MEDIUM confidence. |
| Savings Plan coverage API returns empty | No SP in place; use on-demand pricing. |
| Service uses external deployment controller | Verify controller before recommending changes. |

When Container Insights and Cost Explorer disagree, Cost Explorer is
the ground truth for actual charges — metrics inform the optimization
lever, Cost Explorer confirms the dollar impact.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These billing-model and operational gotchas route a recommendation away
from the obvious choice:

- **Fargate bills CPU and memory independently and per-second.** A task
  running for 90 seconds is billed for 90 seconds (1.5 minutes ×
  combined rate). The 1-minute minimum means tasks running < 60 seconds
  are billed for a full minute.
- **Fargate vCPU is not the same as EC2 vCPU.** Fargate tasks get
  dedicated vCPU; EC2-backed tasks share host vCPU via the Docker
  runtime. 1 Fargate vCPU performs similarly to 1 EC2 vCPU but the
  billing model is different (per-second vs per-hour).
- **Graviton2 (arm64) costs ~20% less on both Fargate and EC2.**
  Fargate arm64 pricing is lower per vCPU-hour and GB-hour. EC2
  Graviton instances (c7g, m7g, r7g) have lower hourly rates than x86
  equivalents. Check application compatibility before migrating.
- **Compute Savings Plans apply to BOTH Fargate and EC2-backed ECS.** A
  single Compute SP covers Fargate vCPU/GB-hours and EC2 instance-hours.
  This is unlike RIs which are instance-specific.
- **Spot capacity provider requires fault tolerance.** Spot instances
  can be reclaimed with 2-minute warning. Services must handle SIGTERM
  gracefully with on-demand fallback. Never use spot for stateful
  single-instance databases.
- **Task placement strategy affects EC2 density.** `binpack` fills
  instances before starting new ones (maximizes density). `spread`
  distributes across instances (maximizes availability). Default is
  `spread`.
- **Container Insights has a cost.** Container Insights charges $0.01
  per container instance per hour for the enhanced metrics. For large
  clusters, this adds up — but the optimization value typically exceeds
  the observability cost.
- **EFS charges per provisioned throughput, not per GB.** For ECS tasks
  using EFS for persistent storage, the cost model is throughput-based
  (provisioned or bursting). EBS charges per GB-month. Choose based on
  access pattern, not just capacity.
- **Standalone tasks are billed identically to service tasks.** A task
  definition deployed as a standalone task (one-shot batch job) costs
  the same per-second as a service task. The difference is lifecycle:
  services auto-restart; standalone tasks run once.
- **Daemon scheduling strategy deploys one task per instance.** This is
  useful for log agents (Firelens, CloudWatch agent) but means the task
  count scales with the instance count, not the application load.

### Step 1: Launch type selection — Fargate vs EC2 (the #1 lever)

Launch type is the primary cost lever because Fargate charges a 30-50%
premium over EC2 for always-on workloads, while EC2 requires capacity
management overhead.

**The crossover math (~30% utilization rule):**
```
Fargate cost (per task, per hour):
  vCPU: 1.0 × $0.04048 = $0.04048/hr
  Memory: 2 GB × $0.004445 = $0.00889/hr
  Total: $0.04937/hr → $36.04/month per task

EC2 cost (per instance, per hour, amortized across tasks):
  m5.large (2 vCPU, 8 GB): $0.096/hr → $70.08/month
  If 4 tasks pack onto 1 instance: $17.52/task/month
  Saving vs Fargate: 51% for the same task footprint

Crossover: if average tasks per instance > 2-3 (steady), EC2 wins.
If tasks are bursty or < 30% utilization, Fargate's per-second wins.
```

**Decision tree:**
```
Is the workload always-on (24/7 steady-state)?
├── NO (batch, cron, event-driven) → Fargate. Per-second billing wins.
└── YES → Is steady utilization > 30%?
    ├── NO → Fargate. You're paying for idle EC2 capacity.
    └── YES → Is the team willing to manage EC2 capacity (ASG, AMI, patching)?
        ├── NO → Fargate with Savings Plan (accept the premium for simplicity).
        └── YES → EC2-backed with capacity provider strategy. Save 30-50%.
```

**Capacity provider for launch type migration:**
```bash
# Create a capacity provider with EC2 ASG backing
aws ecs create-capacity-provider \
  --name ec2-cap-provider \
  --auto-scaling-group-provider \
    autoScalingGroupArn=<asg-arn>,managedScaling=...
```

### Step 2: Architecture migration — Graviton2 (arm64)

Graviton2 (arm64) delivers ~20% cost reduction on both Fargate and EC2.
For Fargate, arm64 pricing is lower per vCPU and GB. For EC2, Graviton
instances (c7g, m7g, r7g) have lower hourly rates.

**Fargate pricing comparison (us-east-1, 2026):**
```
x86_64:  $0.04048/vCPU-hr + $0.004445/GB-hr
arm64:   $0.03238/vCPU-hr + $0.003561/GB-hr  (20% cheaper)
```

**Compatibility check before migration:**

| Application type | ARM64 risk | Verification step |
|---|---|---|
| Interpreted (Python, Node, Ruby) | LOW | Verify native deps have arm64 wheels/gems |
| JVM (Java, Kotlin, Scala) | LOW | Verify JNI libs; JDK 11+ supports arm64 |
| .NET | LOW-MEDIUM | Verify native interop libs |
| Go | LOW | Recompile with `GOARCH=arm64` |
| Rust | LOW | Recompile with `--target aarch64-unknown-linux-gnu` |
| C/C++ | MEDIUM | Recompile for arm64; verify inline assembly |
| Container with x86 binary | HIGH | Requires multi-arch build (`docker buildx`) |

**Migrating to arm64:**
```bash
# Register a new task definition with arm64 runtimePlatform
aws ecs register-task-definition \
  --family order-api \
  --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX \
  --container-definitions file://containers-arm64.json

# Update the service to use the new revision
aws ecs update-service \
  --cluster prod-cluster \
  --service order-api-prod \
  --task-definition order-api:43
```

See `references/ecs-pricing-and-capacity-providers.md` for the full
runtime ARM64 compatibility matrix.

### Step 3: Task definition right-sizing

Right-sizing is the second multiplier. An over-provisioned task wastes
money proportional to the over-allocation. Container Insights provides
CPU and memory utilization metrics for sizing decisions.

**The right-sizing decision gate:**

| Metric (14-30 day window) | Finding | Action |
|---|---|---|
| CPUUtilization avg < 20% AND allocated CPU > 256 (0.25 vCPU) | Over-provisioned | Reduce CPU to p90 × 1.5 (safety margin) |
| CPUUtilization avg > 80% sustained | Under-provisioned | Increase CPU (performance issue, not cost) |
| MemoryUtilization avg < 30% AND allocated memory > 512 MB | Over-provisioned | Reduce memory to p90 × 1.5 |
| MemoryUtilization avg > 85% | Under-provisioned | Increase memory (OOM risk) |
| CPUUtilization p95 > 70% with spikes to 100% | Near ceiling | Increase CPU or add tasks (scale out) |

**Right-sizing math (Fargate, 8 tasks):**
```
Current: 1 vCPU, 2 GB per task → $0.04937/hr × 8 tasks × 730 hr = $288.36/month
Proposed: 0.5 vCPU, 1 GB per task → $0.02473/hr × 8 tasks × 730 hr = $144.45/month
Saving: $143.91/month (50%) — if utilization was < 20% at the original size
```

**Fargate valid CPU/memory combinations:**

| CPU (vCPU) | Memory range (GB) |
|---|---|
| 0.25 | 0.5, 1, 2 |
| 0.5 | 1, 2, 3, 4 |
| 1 | 2, 3, 4, 5, 6, 7, 8 |
| 2 | 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16 |
| 4 | 8, 9, 10, ..., 30 |
| 8 | 16, 17, ..., 60 |

Fargate CPU and memory must be compatible. See the reference for the
full valid-combination table.

### Step 4: Capacity provider strategy (spot + on-demand)

Capacity providers define the infrastructure backing for EC2-launched
ECS tasks. A spot base + on-demand top strategy saves 30-70% for
fault-tolerant workloads.

**Capacity provider strategy patterns:**

| Pattern | Cost | When to use |
|---|---|---|
| 100% on-demand | Baseline (no discount) | Stateful, single-instance, cannot tolerate interruption |
| Spot base (70%) + on-demand top (30%) | 30-50% saving | Stateless web services, microservices, workers |
| 100% spot | 70% saving | Batch jobs, queue workers, fault-tolerant CI/CD |
| Spot + Fargate fallback | Mixed | Hybrid approach for critical periods |

**Spot capacity provider setup:**
```bash
# Create a spot-backed capacity provider
aws ecs create-capacity-provider \
  --name spot-cap-provider \
  --auto-scaling-group-provider \
    autoScalingGroupArn=<spot-asg-arn>,\
    managedScaling=status=ENABLED,targetCapacity=70,\
    managedTerminationProtection=DISABLED

# Assign the strategy to the cluster
aws ecs put-cluster-capacity-providers \
  --cluster prod-cluster \
  --capacity-providers spot-cap-provider on-demand-cap-provider \
  --default-capacity-provider-strategy \
    capacityProvider=spot-cap-provider,weight=70,base=2,\
    capacityProvider=on-demand-cap-provider,weight=30
```

**Spot interruption handling:**
ECS spot capacity providers integrate with EventBridge for 2-minute
reclaim warnings. Ensure:
- Task `stopTimeout` >= 30 seconds for graceful shutdown
- Application handles SIGTERM (flush buffers, close connections)
- Capacity provider strategy has on-demand fallback (base >= 2)

### Step 5: Savings Plan coverage

Compute Savings Plans apply to both Fargate and EC2-backed ECS. They
commit to a $/hour spend in exchange for a discount (up to 54% for
1-year commitment, up to 72% for 3-year).

**Savings Plan vs Reserved Instance:**

| Feature | Compute SP | Reserved Instance |
|---|---|---|
| Applies to Fargate | YES | NO |
| Applies to EC2 ECS | YES | YES |
| Flexibility (any instance family) | YES (any family, any size, any AZ) | NO (specific family only) |
| Applies to Lambda | YES | NO |
| Discount depth | Up to 54% (1yr), 72% (3yr) | Up to 72% (3yr Standard) |

**Coverage analysis:**
```bash
# Check current SP coverage
aws savingsplans describe-savings-plans-coverage \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"Service","Values":["Amazon Elastic Container Service","AmazonEC2"]}}'

# Check SP utilization (are you using what you committed to?)
aws savingsplans describe-savings-plans-utilization \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --granularity MONTHLY
```

**Decision gate for SP purchase:**

| Monthly ECS spend (on-demand) | Steady (>12 months)? | Recommendation |
|---|---|---|
| > $5,000 | YES | 1-year Compute SP at 50-70% coverage |
| > $10,000 | YES | 1-year Compute SP at 70-90% coverage (or 3-year for max discount) |
| < $2,000 | Any | SP overhead is not worth the commitment tracking |
| Any | NO (growing/shrinking fast) | Delay SP until spend stabilizes |

### Step 6: Task placement and scheduling strategy

Task placement strategy determines how tasks distribute across EC2
instances in an EC2-backed cluster. This affects instance density and
therefore cost.

**Placement strategy comparison:**

| Strategy | Effect | Cost impact | When to use |
|---|---|---|---|
| `spread` (default) | Distributes tasks across all instances | Lower density (more instances needed) | High-availability, fault-isolation |
| `binpack` | Packs tasks onto fewest instances | Higher density (fewer instances) | Cost optimization for stateless |
| `random` | No strategy | Unpredictable | Testing only |

**Scheduling strategy comparison:**

| Strategy | Effect | Cost impact |
|---|---|---|
| `REPLICA` (service) | Maintains desired count; auto-restarts | Always-on cost |
| `DAEMON` (service) | One task per instance | Scales with fleet size (use for agents) |
| Standalone task | Run once, no auto-restart | Per-invocation cost (batch jobs) |

**Bin-pack placement for EC2 density:**
```bash
aws ecs create-service \
  --cluster prod-cluster \
  --service-name order-api-prod \
  --task-definition order-api:43 \
  --scheduling-strategy REPLICA \
  --placement-strategy type=binpack,field=memory \
  --placement-constraints type=distinctInstance
```

### Step 7: Auto-scaling target tracking

Auto-scaling adjusts the desired task count based on a CloudWatch metric
target. Poorly tuned scaling policies cause over-provisioning (too many
tasks) or under-provisioning (SLO violations).

**Target tracking tuning:**

| Metric | Recommended target | Notes |
|---|---|---|
| ECS CPUUtilization | 50-65% | Lower = more tasks = more cost; higher = SLO risk |
| ECS MemoryUtilization | 60-75% | Memory doesn't compress — tune to app behavior |
| ALB RequestCountPerTarget | App-specific | Better for latency-driven scaling than CPU |
| Custom metric (queue depth) | App-specific | Best for batch/queue-driven workloads |

**Scheduled scaling for known patterns:**
For workloads with predictable traffic (e.g., business-hours spike),
scheduled scaling is cheaper than reactive target tracking because it
pre-provisions before the load arrives:

```bash
aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --resource-id service/prod-cluster/order-api-prod \
  --scalable-dimension ecs:service:DesiredCount \
  --scheduled-action-name BusinessHoursScaleUp \
  --schedule "cron(0 9 ? * MON-FRI *)" \
  --scalable-target-action MinCapacity=10,MaxCapacity=20
```

### Step 8: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (Fargate) vCPU_hours × $0.04048 + GB_hours × $0.004445
  OR
  (EC2) instance_count × instance_hourly × 730

projected_monthly_cost =
  (Fargate arm64) vCPU_hours × $0.03238 + GB_hours × $0.003561
  OR
  (EC2 Graviton) instance_count × graviton_hourly × 730
  OR
  (right-sized) reduced_vCPU_hours × rate + reduced_GB_hours × rate
  × (1 - SP_discount) if Savings Plan applied

monthly_saving = current_monthly_cost - projected_monthly_cost
```

Always state assumptions: launch type, architecture, task count,
utilization baseline, pricing region, capacity provider mix.

### Step 9: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass AND architecture on arm64 AND task right-sized AND
  SP coverage in place → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (Container Insights absent, window < 14 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

```text
TARGET: <service-name or task-definition>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <launch type>, <CPU> vCPU, <memory> GB, <architecture>, <task count>, <capacity provider>
  Proposed: <launch type>, <CPU> vCPU, <memory> GB, <architecture>, <task count>, <capacity provider>
  Dimensions changed: <launch-type | architecture | right-size | spot | savings-plan | placement | autoscaling>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list (task count, pricing region, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <service-name> in <cluster>.
  Proceed? (yes/no)"
```

Full worked examples (launch type migration, Graviton2, right-sizing,
spot capacity provider, already-optimized, NEED_MORE_INFO, end-to-end
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
TARGET: <service-name or task-definition>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <launch type>, <CPU> vCPU, <memory> GB, <architecture>, <task count>, <capacity provider>
  Proposed: <launch type>, <CPU> vCPU, <memory> GB, <architecture>, <task count>, <capacity provider>
  Dimensions changed: <launch-type | architecture | right-size | spot | savings-plan | placement | autoscaling>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show subtotals (compute, storage, requests if applicable)
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with `Monthly
   saving: $0.00`.** If every dimension nets zero cost delta, the verdict
   MUST be `OPTIMIZED`.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend a Graviton2 (arm64) migration without citing the
   application's compatibility evidence.** The REASON MUST name the
   verification source (interpreted runtime, arm64 wheels, multi-arch
   container build).

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER recommend spot capacity without warning about interruption
   risk and verifying the application handles graceful shutdown.**
   Surface the fault-tolerance requirement in MIGRATION_STEPS.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE with verified math

Every field below is internally consistent. Copy this shape exactly.

```text
TARGET: order-api-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Fargate service at 1024 CPU / 2048 MB with avg CPUUtilization
  12% and MemoryUtilization 18% across 8 running tasks. Two findings:
  (1) right-size to 512 CPU / 1024 MB (Container Insights confirms
  steady p95 utilization under 30% of allocated); (2) migrate from
  x86_64 to arm64 (Node.js 20 — full arm64 support, no native deps).
  Combined monthly saving: $172.97 (60% compute reduction).
RECOMMENDATION:
  Current: FARGATE, 1.0 vCPU, 2.0 GB, x86_64, 8 tasks, on-demand
  Proposed: FARGATE, 0.5 vCPU, 1.0 GB, arm64, 8 tasks, on-demand
  Dimensions changed: right-size (Step 3) + architecture (Step 2)
  Dimensions checked: launch-type ✓ (Fargate, < 30% utilization confirms Fargate)
    architecture → (x86 to arm64)  right-size → (1.0/2.0 to 0.5/1.0)
    spot ✓ (Fargate, no spot)  savings-plan ✓ (covered)  placement ✓ (Fargate)
    autoscaling ✓ (target tracking at 60% CPU)
  Confidence: HIGH — Container Insights confirms 30-day avg CPUUtilization
    12% and MemoryUtilization 18%; Node.js 20 fully supports arm64;
    no native dependencies in container image.
ESTIMATED_SAVINGS:
  Current monthly: $288.32
    compute: 1.0 vCPU × 8 tasks × 730 hr × $0.04048 = $236.40
    memory: 2.0 GB × 8 tasks × 730 hr × $0.004445 = $51.92
  Projected monthly: $115.35
    compute: 0.5 vCPU × 8 tasks × 730 hr × $0.03238 = $94.55
    memory: 1.0 GB × 8 tasks × 730 hr × $0.003561 = $20.80
  Monthly saving: $172.97 ($288.32 − $115.35)
  Annual saving: $2,075.64
MIGRATION_STEPS:
  1. Register new task definition with arm64 + right-sized resources:
     aws ecs register-task-definition --family order-api
       --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX
       --cpu 512 --memory 1024 --container-definitions file://containers-arm64.json
  2. Deploy via canary (Distributed Map or CodeDeploy):
     aws ecs update-service --cluster prod-cluster
       --service order-api-prod --task-definition order-api:43
  3. Monitor CPUUtilization and MemoryUtilization for 7 days post-change.
  4. Verify no OOM kills or throttle events in Container Insights.
CONFIRM: About to update-service on order-api-prod
  (1.0 vCPU x86 → 0.5 vCPU arm64, 2.0 GB → 1.0 GB). Monthly saving
  $172.97 (60.0%). Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | All dimensions pass (arm64, right-sized, SP coverage, appropriate capacity provider). Also emitted when a change was applied and verified this session. |
| `NEED_MORE_INFO` | Data gate failed: Container Insights not enabled, metrics absent, window < 14 days. |
| `BLOCKED` | Hard precondition prevents evaluation: service in a different account, IAM denies ecs:DescribeServices. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `OPTIMIZED`, never `FURTHER_OPTIMIZATION_AVAILABLE`.
Exception: a latency or availability improvement without cost change is
surfaced in REASON, not as dollar savings.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend a Graviton2 migration without verifying application
   compatibility.** Compiled binaries (C/C++, Go with CGO, Rust inline
   assembly) and JNI libraries may fail on arm64. Always require
   multi-arch container build verification before recommending.

2. **NEVER recommend spot capacity for stateful single-instance services.**
   Spot reclamation causes task termination. Stateful services (databases,
   caches with no replication) cannot tolerate interruption. Spot is for
   stateless, horizontally scalable workloads only.

3. **NEVER right-size a task definition below the application's actual
   peak memory usage.** Memory is not compressible — an OOM kill is a
   production incident. Use p95 MemoryUtilization × 1.5 as the floor.

4. **NEVER recommend migrating Fargate to EC2 without warning about the
   operational overhead.** EC2-backed ECS requires ASG management, AMI
   patching, capacity provider tuning, and instance monitoring. The cost
   saving is real but the operational burden is significant.

5. **NEVER recommend a Savings Plan purchase without analyzing utilization
   stability.** An SP commits to $X/hour for 1-3 years. If the workload
   is shrinking or migrating to a different service, the commitment
   becomes wasted spend.

Extended anti-patterns in `references/ecs-pricing-and-capacity-providers.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Canary deployments for task definition changes.** Never roll to 100%
  at once. Use CodeDeploy canary (10% → 50% → 100%) or weighted targets.
- **Graviton migration requires arm64 container image.** Verify the
  registry image is multi-arch or arm64-native before updating.
- **Right-sizing changes can cause OOM.** Monitor MemoryUtilization for
  24-48 hours after reducing memory. Roll back immediately on OOM.
- **Capacity provider changes trigger task replacement.** New tasks
  launch on the new infrastructure; existing tasks may be drained.
- **Spot capacity provider requires drain hook.** Application must handle
  SIGTERM; stopTimeout >= 30 seconds for graceful connection draining.
- **Savings Plan purchases are irreversible.** A 1-3 year commitment
  cannot be cancelled. Verify the spend baseline is stable first.
- **Auto-scaling changes can cause flapping.** Change target tracking
  in small increments (5-10% at a time).
- **Bulk-operation limit:** Process at most 5 services per batch. Sort
  by estimated savings, verify each batch. Abort on errors or latency.

## Recent AWS features (2024-2026)

- **ECS Fargate arm64 (Graviton2) GA (2024):** Full support for arm64
  on Fargate. ~20% cheaper than x86_64.
- **Capacity provider managed scaling enhancements (2024-2025):**
  Tighter target-capacity tracking for EC2-backed clusters.
- **Container Insights enhanced metrics (2024):** Per-task CPU, memory,
  network, and storage metrics.
- **ECS Service Connect (2024 GA):** Built-in service discovery and
  load balancing without Cloud Map or ALB cost.
- **Fargate per-second billing (2024):** Consistent per-second billing
  across all regions with 1-minute minimum.
- **Graviton4 instances (2024-2025):** c8g, m8g, r8g with improved
  price-performance over Graviton3.

## References

- `references/ecs-pricing-and-capacity-providers.md` — pricing tables,
  Fargate valid CPU/memory combinations, Graviton2 compatibility matrix,
  capacity provider configuration, Savings Plan discount tiers, regional
  pricing multipliers, cost calculation worked examples.
- `references/worked-examples.md` — full worked examples (launch type
  migration, Graviton2, right-sizing, spot capacity provider,
  already-optimized, NEED_MORE_INFO, end-to-end walkthrough).

## Domain

AWS CloudOps / ECS Container Cost Optimization & FinOps.

## AWS documentation

- **Amazon ECS Developer Guide** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html
- **AWS Fargate pricing** — https://aws.amazon.com/fargate/pricing/
- **ECS capacity providers** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-capacity-providers.html
- **ECS task definition parameters** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html
- **CloudWatch Container Insights** — https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContainerInsights.html
- **ECS service auto-scaling** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html
- **AWS Graviton for ECS** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/ecs-graviton.html
- **Savings Plans** — https://docs.aws.amazon.com/savingsplans/latest/userguide/
- **AWS CLI ECS reference** — https://docs.aws.amazon.com/cli/latest/reference/ecs/
- **Well-Architected Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
