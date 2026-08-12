---
name: ecs-cluster-autoscaling-optimizer
description: 'Optimises Amazon ECS cluster autoscaling across eleven dimensions: capacity provider strategy (spot vs on-demand weight and base — the spot base + on-demand burst pattern), managed EC2 capacity provider
  auto-scaling (replaces the legacy Cluster Autoscaler / cluster-autoscaler project with native ECS managed scaling), target tracking metric selection (ECSServiceAverageCPUUtilization vs ECSServiceAverageMemoryUtilization vs ALB
  RequestCountPerTarget), scale-in cooldown tuning (default 300 s is too long for spiky workloads), bin-packing efficiency (detecting empty hosts and stranded resources), Fargate capacity provider (no capacity planning needed for
  serverless tasks), EC2 instance warm-up time (AMI boot + container agent registration delay), drain instance lifecycle (DRAINING to DEPROVISIONING state management for graceful task migration), desired count vs running count
  gap analysis (detecting stuck or pending tasks), task placement strategy (spread vs binpack vs random for optimal host utilization), and service auto-scaling vs scheduled scaling for predictable workload patterns. Reads
  ECS DescribeClusters, DescribeServices, DescribeCapacityProviders, DescribeContainerInstances, CloudWatch ECS/EKS metrics, and CapacityProviderReservation metrics. Emits OPTIMIZED or FURTHER_OPTIMIZATION_AVAILABLE with specific
  capacity provider reconfiguration, placement strategy changes, and dollar-denominated utilization improvement. Use when reviewing ECS cluster autoscaling, tuning capacity providers, triaging bin-packing waste, or running an
  ECS FinOps review.'
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted ECS describe-clusters/describe-services output, capacity provider JSON,
  and CloudWatch ECSInsights metrics. Live-account optimization uses aws ecs describe-clusters, aws ecs describe-services, aws ecs describe-capacity-providers, aws ecs describe-container-instances, aws ecs describe-tasks, aws
  application-autoscaling describe-scaling-policies, aws cloudwatch get-metric-statistics (CPUUtilization, MemoryUtilization, RunningTaskCount, DesiredTaskCount, CapacityProviderReservation, ALBRequestCountPerTarget), aws ec2
  describe-instances, and aws ce get-cost-and-usage (AWS CLI v2, SSO or key-based credentials). Pricing references us-east-1 published rates as of 2026; re-state regional rates for other regions.
keywords:
- ECS
- ECS cluster
- capacity provider
- managed scaling
- Cluster Autoscaler
- spot instances
- on-demand
- bin-packing
- binpack
- task placement
- spread strategy
- Fargate
- target tracking
- ECSServiceAverageCPUUtilization
- scale-in cooldown
- drain instances
- DRAINING
- DEPROVISIONING
- scheduled scaling
- service autoscaling
- capacity provider strategy
- Compute
- FinOps
tags:
- ecs
- compute
- autoscaling
- capacity-provider
- cost-optimization
- finops
- bin-packing
- spot-instances
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
  when_to_use: Optimising ECS cluster autoscaling, switching from Cluster Autoscaler to managed EC2 capacity provider, tuning capacity provider strategy (spot vs on-demand), selecting target tracking metrics, tuning scale-in
    cooldown, detecting bin-packing waste and empty hosts, managing drain instance lifecycle, evaluating Fargate vs EC2 capacity provider, choosing service auto-scaling vs scheduled scaling, or improving task placement strategy.
  when_not_to_use: EC2 instance rightsizing (use ec2-rightsizing-optimizer), EKS cluster autoscaling (use eks-autoscaling-optimizer — different API surface), ECS task-level troubleshooting (container crashes, task failures,
    health-check issues — use the ECS troubleshooter), ECS service mesh or App Mesh configuration, or Fargate capacity provisioning (Fargate has no capacity planning surface). This skill focuses on cluster-level autoscaling
    optimization, not functional debugging of broken tasks.
  activation_triggers:
  - optimise ECS autoscaling
  - ECS capacity provider
  - ECS managed scaling
  - ECS Cluster Autoscaler migration
  - ECS spot capacity provider
  - ECS bin-packing
  - ECS binpack placement
  - ECS task placement strategy
  - ECS scale-in cooldown
  - ECS drain instances
  - ECS DRAINING lifecycle
  - ECS target tracking
  - ECS Fargate capacity provider
  - ECS scheduled scaling
  - ECS service autoscaling
  - ECS empty host detection
  - ECS FinOps
  - ECS cluster utilization
  invocation_schema: 'Input: either (a) a cluster name + live-account context, (b) a describe-clusters/describe-services/describe-capacity-providers JSON payload, OR (c) CloudWatch CapacityProviderReservation and
    ECSServiceAverageCPUUtilization metrics with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_IMPACT/MIGRATION_STEPS block per cluster, where VERDICT is one of OPTIMIZED,
    FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline capacity provider classification):\nClusterName: ecs-prod-cluster\nLaunch type: EC2 (2 capacity providers: on-demand, spot)\nCapacity provider strategy: on-demand weight=4,\
    \ base=2; spot weight=1, base=0\nManaged scaling: disabled (using legacy cluster-autoscaler)\nPlacement strategy: spread by az\nScale-in cooldown: 300 s (default)\nMetrics (last 30 days):\n  - CPUUtilization avg: 35%, p95:\
    \ 55%\n  - MemoryUtilization avg: 28%, p95: 45%\n  - CapacityProviderReservation (on-demand): avg 60%\n  - RunningEC2Tasks avg: 40, DesiredTasks avg: 40\n  - Empty container instances: 8 of 20 (40% stranded)\nEmit the\
    \ standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS)."
---

# ECS Cluster Autoscaling Optimizer

## What this skill does

Translates an Amazon ECS cluster's autoscaling configuration and
runtime utilization into a concrete cost-and-utilization optimization
recommendation. The verdict is the highest-leverage action across
eleven dimensions — capacity provider strategy, managed scaling, target
tracking metric, scale-in cooldown, bin-packing efficiency, Fargate
capacity provider, EC2 instance warm-up, drain instance lifecycle,
desired vs running count gap, task placement strategy, and scaling mode
(service vs scheduled) — applied in priority order. Always pairs the
recommendation with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Five headline rules and the utilization math | First read |
| Mindset | Why managed scaling + binpack wins | Approach |
| Verdict thresholds | Decision matrix at a glance | Classifying |
| Pre-flight data gate | ECS API, CloudWatch, capacity providers | Before any rec |
| Step 0 non-obvious behaviours | Spot base, drain lifecycle, warm-up | Edge cases |
| Step 1 Capacity provider strategy | Spot vs on-demand weight and base | Headline dimension |
| Step 2 Managed scaling vs Cluster Autoscaler | Native ECS replacement | Legacy migration |
| Step 3 Target tracking metric | CPU vs memory vs ALB request count | Metric selection |
| Step 4 Scale-in cooldown | Tuning the 300 s default | Spiky workloads |
| Step 5 Bin-packing efficiency | Empty host detection + binpack | Utilization waste |
| Step 6 Fargate capacity provider | Serverless tasks | No-capacity workloads |
| Step 7 EC2 instance warm-up | Boot + agent registration delay | Scale-out latency |
| Step 8 Drain instance lifecycle | DRAINING to DEPROVISIONING | Graceful migration |
| Step 9 Desired vs running count | Stuck task detection | Service health |
| Step 10 Placement strategy | Spread vs binpack vs random | Host utilization |
| Output format | VERDICT block + worked examples | Emitting result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check |
| Pre-flight safety | CONFIRM gate, drain, deployment | Before apply CLI |

## Quick start

- **Managed EC2 capacity provider auto-scaling replaces Cluster Autoscaler.**
  The legacy `cluster-autoscaler` project (or its K8s equivalent for
  ECS) is obsolete for native ECS. The managed capacity provider has
  built-in target tracking on `CapacityProviderReservation` and handles
  scale-out AND scale-in natively. Migrate if still on the legacy path.
- **Spot base + on-demand burst is the cost-optimal pattern.** Set
  `base = 2` on the on-demand provider (steady-state floor), `weight =
  1` on spot (fills burst capacity at 70% discount). This avoids
  spot-only risk while capturing the majority of the savings.
- **Binpack placement maximizes utilization.** The default `spread`
  strategy places one task per host, wasting 60-80% of host capacity.
  Switch to `binpack` (by `memory` or `cpu`) to pack tasks densely and
  reduce the host count.
- **Scale-in cooldown 300 s is too long for spiky workloads.** Default
  is 300 s; for microservices with bursty traffic, 60-120 s prevents
  stranded hosts from lingering after the burst ends.
- **Empty hosts are pure waste.** A container instance with 0 running
  tasks costs the full EC2 rate. Detect with
  `describe-container-instances` and eliminate via scale-in or binpack
  placement.

## Mindset

ECS cluster autoscaling optimization is a utilization-and-cost decision.
The goal is the capacity provider configuration and placement strategy
that maximizes host utilization (binpack) while preserving availability
(on-demand base for steady state + spot for burst) — not the absolute
minimum instances that run tasks.

Four principles guide every recommendation:

- **Managed scaling adapts; Cluster Autoscaler does not.** The managed
  capacity provider observes `CapacityProviderReservation` and scales
  natively. The legacy Cluster Autoscaler is a separate controller with
  known lag, race conditions, and extra operational overhead.
- **Spot base + on-demand burst is the cost-optimal hybrid.** Pure
  on-demand pays full price; pure spot risks availability. The `base`
  parameter on on-demand ensures a steady-state floor; spot `weight`
  captures burst capacity at a discount.
- **Binpack placement maximizes utilization.** The default `spread`
  strategy wastes host capacity by distributing tasks one-per-host.
  `binpack` packs tasks densely, reducing the total host count.
- **Scale-in cooldown controls cost during traffic dips.** A long
  cooldown (300 s default) keeps stranded hosts alive after a burst
  ends. A shorter cooldown (60-120 s) for microservices eliminates
  waste faster.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| Using legacy cluster-autoscaler AND not using managed EC2 capacity provider | **FURTHER_OPTIMIZATION_AVAILABLE** (managed scaling) | Step 2 — migrate to managed capacity provider |
| All on-demand capacity provider AND workload is burst-tolerant | **FURTHER_OPTIMIZATION_AVAILABLE** (spot strategy) | Step 1 — add spot capacity provider with base+weight |
| Pure spot capacity provider AND no on-demand base AND availability SLO requires steady floor | **FURTHER_OPTIMIZATION_AVAILABLE** (spot strategy) | Step 1 — add on-demand base for steady-state |
| Placement strategy = spread AND avg host utilization (CPU or memory) < 40% | **FURTHER_OPTIMIZATION_AVAILABLE** (bin-packing) | Step 5+10 — switch to binpack placement |
| Scale-in cooldown = 300 s (default) AND traffic is spiky (CV > 0.5) | **FURTHER_OPTIMIZATION_AVAILABLE** (cooldown) | Step 4 — reduce cooldown to 60-120 s |
| Empty container instances > 10% of fleet AND scale-in not firing | **FURTHER_OPTIMIZATION_AVAILABLE** (bin-packing) | Step 5 — enable binpack + verify scale-in |
| Target tracking = CPU only AND workload is memory-bound (memory > 70% when CPU < 40%) | **FURTHER_OPTIMIZATION_AVAILABLE** (target tracking) | Step 3 — switch to memory or dual-metric |
| Desired count != running count for > 5% of services (sustained) | **FURTHER_OPTIMIZATION_AVAILABLE** (desired/running gap) | Step 9 — investigate stuck tasks |
| Predictable workload (e.g., business hours only) AND using service auto-scaling | **FURTHER_OPTIMIZATION_AVAILABLE** (scheduled scaling) | Add scheduled scaling for predictable peaks |
| All dimensions verified AND managed scaling + spot base + binpack + tuned cooldown in place | **OPTIMIZED** | Emit post-state verification |
| CloudWatch metrics absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI sequences are in
`references/ecs-autoscaling-configuration-and-pricing.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Cluster configuration: `aws ecs describe-clusters` (include
   `ATTACHMENTS` for capacity provider info)
2. Services: `aws ecs describe-services` (desired/running/pending counts)
3. Capacity providers: `aws ecs describe-capacity-providers`
4. Container instances: `aws ecs describe-container-instances` (CPU and
   memory remaining per instance)
5. Scaling policies: `aws application-autoscaling describe-scaling-policies`
6. CloudWatch: CPUUtilization, MemoryUtilization, RunningTaskCount,
   DesiredTaskCount, CapacityProviderReservation
7. EC2 instances: `aws ec2 describe-instances` (for host type and age)

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `describe-clusters` returns cluster not found | Cluster does not exist in this region. Skip. |
| `describe-clusters` shows `runningTasksCount = 0` over 14 days | Cluster dormant. **NEED_MORE_INFO**. |
| Observation window < 14 days | Workload may reflect atypical load. **NEED_MORE_INFO**. |
| `CapacityProviderReservation` metric absent | Managed scaling not enabled. Confirm via describe-capacity-providers. |
| Container instances show `0 remaining CPU AND 0 remaining memory` | Cluster is at capacity. Scale-out needed before tuning. |
| Cluster is Fargate-only (no EC2 capacity providers) | Different optimization surface — focus on task right-sizing, not capacity providers. |

When ECS API and CloudWatch disagree, the ECS API wins for real-time
state; CloudWatch wins for trend analysis.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **`base` on a capacity provider is the steady-state floor.** Set `base`
  on the on-demand provider to guarantee a minimum number of tasks on
  on-demand regardless of spot availability.
- **`weight` controls the distribution ratio.** For every N tasks, the
  ratio is `weight`-proportional across providers. For cost-optimization:
  on-demand weight = 1, spot weight = 4 (with on-demand base = 2).
- **Managed scaling uses CapacityProviderReservation.** The managed
  capacity provider reports its own CloudWatch metric for target
  tracking, distinct from service-level ECSServiceAverageCPUUtilization.
- **Scale-in has two cooldowns: policy-level and capacity-provider-level.**
  The policy `CooldownSeconds` defaults to 300. The
  `instanceWarmupPeriod` controls how fast new instances register.
- **Spread strategy is the default but wastes hosts.** `spread` by
  `host` leaves 60-80% of host capacity unused. Switch to `binpack`.
- **Binpack by memory vs CPU depends on the bottleneck resource.**
  Memory-heavy (JVM, ML) → binpack by `memory`. CPU-heavy → by `cpu`.
- **Drain lifecycle: DRAINING to DEPROVISIONING.** When scale-in targets
  an instance, ECS moves it to `DRAINING`, reschedules tasks, then
  `DEPROVISIONING` terminates it. Takes 60-300 s depending on shutdown.
- **EC2 instance warm-up adds 60-120 seconds.** Boot, ECS agent
  registration, and health checks before tasks can be placed.
- **Fargate has no capacity provider to tune.** Tasks are serverless.
  Only optimization is CPU/memory right-sizing at the task level.
- **Spot instance interruption gives 2-minute warning.** Tasks must
  drain within that window or they are force-terminated.
- **Desired count != running count means tasks are failing to place.**
  Sustained gap = cluster lacks capacity. This is a scale-out signal.

### Step 1: Capacity provider strategy — spot vs on-demand

The capacity provider strategy controls how tasks distribute across
on-demand and spot capacity. The cost-optimal pattern is on-demand base
for steady state + spot weight for burst.

**Capacity provider strategy parameters:**
```json
{
  "capacityProviderStrategy": [
    {
      "capacityProvider": "on-demand-cp",
      "weight": 1,
      "base": 2
    },
    {
      "capacityProvider": "spot-cp",
      "weight": 4,
      "base": 0
    }
  ]
}
```

**Decision gate:**

| Current strategy | Workload | Verdict | Action |
|---|---|---|---|
| All on-demand, no spot | Burst-tolerant (batch, async, stateless) | **FURTHER_OPTIMIZATION_AVAILABLE** | Add spot CP with weight=4, base=0; set on-demand base=2 |
| All on-demand, no spot | Latency-sensitive (API, real-time) | KEEP on-demand | Proceed to other dimensions |
| Pure spot, no on-demand base | Any workload with availability SLO | **FURTHER_OPTIMIZATION_AVAILABLE** | Add on-demand base=2 for steady-state floor |
| On-demand base + spot weight already | Optimal hybrid | No CP finding | Proceed to other dimensions |

**Create a spot capacity provider:**
```bash
aws ecs create-capacity-provider \
  --name spot-cp \
  --auto-scaling-group-provider autoScalingGroupArn=<asg-arn>,managed-scaling.status=ENABLED,managed-scaling.target-capacity=100
```

### Step 2: Managed scaling vs Cluster Autoscaler

The legacy Cluster Autoscaler (a standalone controller) is obsolete for
native ECS. The managed EC2 capacity provider has built-in target
tracking on `CapacityProviderReservation` and handles scale-out and
scale-in natively.

**Detection:**
```bash
aws ecs describe-capacity-providers --capacity-providers <cp-name> \
  --query 'capacityProviders[0].autoScalingGroupProvider.managedScaling' \
  --output json
```

If `managedScaling.status = DISABLED` or the cluster uses a standalone
`cluster-autoscaler` deployment, migrate to managed scaling.

**Enable managed scaling:**
```bash
aws ecs put-cluster-capacity-providers \
  --cluster <cluster-name> \
  --capacity-providers <cp-name> \
  --default-capacity-provider-strategy capacityProvider=<cp-name>,weight=1,base=1

# Update the capacity provider with managed scaling
aws ecs update-capacity-provider \
  --name <cp-name> \
  --auto-scaling-group-provider managedScaling.status=ENABLED,managedScaling.targetCapacity=100,managedScaling.minimumScalingStepSize=1,managedScaling.maximumScalingStepSize=100
```

### Step 3: Target tracking metric selection

The target tracking metric controls when the service auto-scaler triggers.
Choosing the wrong metric leads to under- or over-scaling.

| Metric | When to use | Pros | Cons |
|---|---|---|---|
| `ECSServiceAverageCPUUtilization` | CPU-bound workloads | Direct compute pressure signal | Misses memory-bound workloads |
| `ECSServiceAverageMemoryUtilization` | Memory-bound workloads (JVM, caching) | Direct memory pressure signal | Misses CPU-bound workloads |
| `ALBRequestCountPerTarget` | Request-driven services | Direct demand signal | Requires ALB integration |
| `CapacityProviderReservation` | Cluster-level scaling | Managed CP native metric | Not for service-level scaling |

**Decision gate:**

| Workload profile | Recommended metric | Target value |
|---|---|---|
| CPU-bound (compute pipelines, data processing) | `ECSServiceAverageCPUUtilization` | 50-70% |
| Memory-bound (JVM, ML inference, caching) | `ECSServiceAverageMemoryUtilization` | 60-75% |
| Request-driven (API, web service) | `ALBRequestCountPerTarget` | 1000-5000 req/target |
| Mixed (both CPU and memory pressure) | Dual policy (CPU + memory) | Both must trigger |

### Step 4: Scale-in cooldown tuning

The `CooldownSeconds` parameter (default 300 s) controls how quickly the
auto-scaler can trigger consecutive scale-in actions. For spiky
workloads, 300 s leaves stranded hosts alive too long.

**Decision gate:**

| Traffic pattern | Recommended cooldown | Rationale |
|---|---|---|
| Steady (CV < 0.3) | 300 s (default) | Slow scale-in avoids flapping |
| Spiky (CV > 0.5) | 60-120 s | Fast scale-in eliminates waste quickly |
| Predictable (business hours) | 300 s + scheduled scaling | Scheduled handles the pattern |

**Tune the cooldown:**
```bash
aws application-autoscaling put-scaling-policy \
  --policy-name ecs-service-cpu-scaling \
  --policy-type TargetTrackingScaling \
  --resource-id service/<cluster>/<service> \
  --scalable-dimension ecs:service:DesiredCount \
  --service-namespace ecs \
  --target-tracking-scaling-policy-configuration \
    TargetValue=60.0,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageCPUUtilization},ScaleOutCooldown=60,ScaleInCooldown=120
```

### Step 5: Bin-packing efficiency (empty host detection)

Empty or under-utilized hosts are the primary source of ECS waste.

**Detection:**
```bash
aws ecs describe-container-instances \
  --cluster <cluster> \
  --container-instances <instance-arns> \
  --query 'containerInstances[].{id:ec2InstanceId,cpu:remainingResources[?name==`CPU`].integerValue|[0],memory:remainingResources[?name==`MEMORY`].integerValue|[0],running:runningTasksCount}' \
  --output table
```

**Empty host ratio:**
```
empty_hosts = count(instances where runningTasksCount == 0)
empty_ratio = empty_hosts / total_instances
```

If `empty_ratio > 10%`, the cluster has stranded capacity.

**Resolution:**
1. Switch placement strategy from `spread` to `binpack` (Step 10).
2. Verify the managed capacity provider scale-in is firing (check
   CloudWatch `CapacityProviderReservation`).
3. If scale-in is not firing, check the ASG `MinSize` — it may be set
   above the actual need.

### Step 6: Fargate capacity provider (no capacity planning)

For workloads that don't need EC2 control, Fargate eliminates all
capacity management. Tasks run serverlessly with per-second billing.

**Decision gate:**

| Workload | Fargate suitability |
|---|---|
| Microservices (stateless, < 4 vCPU, < 30 GB memory) | HIGH — no capacity planning |
| Long-running batch (> 4 vCPU) | LOW — Fargate caps at 16 vCPU / 120 GB |
| Tasks needing host access (daemon, privileged) | NOT supported on Fargate |
| Cost-sensitive steady-state | MEDIUM — Fargate is ~20% premium over EC2 |

### Step 7: EC2 instance warm-up time

The `instanceWarmupPeriod` on the capacity provider controls how long
ECS waits before considering a new instance available for task placement.

**Default:** 15 seconds (too short for most AMIs).

**Recommended values:**

| AMI / Boot pattern | Warm-up |
|---|---|
| Amazon Linux 2023 (ECS-optimized) | 30-60 s |
| Custom AMI with userData scripts | 60-120 s |
| Bottlerocket | 15-30 s |

**Tune warm-up:**
```bash
aws ecs update-capacity-provider \
  --name <cp-name> \
  --auto-scaling-group-provider managedScaling.status=ENABLED,instanceWarmupPeriod=60
```

### Step 8: Drain instance lifecycle (DRAINING to DEPROVISIONING)

When the managed capacity provider scales in, instances go through
`DRAINING` before `DEPROVISIONING`. During `DRAINING`, ECS reschedules
tasks to other instances.

**Monitoring drain time:**
```bash
aws ecs describe-container-instances \
  --cluster <cluster> \
  --container-instances <arns> \
  --query 'containerInstances[].{id:ec2InstanceId,status:status,running:runningTasksCount}' \
  --output table
```

If drain time exceeds 300 s:
1. Check task `StopTimeout` (default 30 s — increase if graceful
   shutdown needs more time).
2. Check for tasks with long-running connections (DB sessions, file
   transfers) that resist rescheduling.
3. Consider connection draining at the ALB level (`deregistration_delay`).

### Step 9: Desired count vs running count gap analysis

If `runningTasksCount < desiredCount` sustained, tasks cannot be placed.
This is a capacity signal, not a configuration tuning issue.

**Detection:**
```bash
aws ecs describe-services \
  --cluster <cluster> \
  --services <service-name> \
  --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}' \
  --output json
```

| Observation | Diagnosis |
|---|---|
| `pending > 0` sustained AND no scale-out | Cluster lacks CPU/memory — increase ASG MaxSize |
| `running < desired` AND `pending = 0` | Tasks are starting and immediately failing — check task logs |
| `running = desired` AND `pending = 0` | Healthy — no gap |

### Step 10: Task placement strategy

The placement strategy controls how ECS distributes tasks across hosts.

| Strategy | Effect | When to use |
|---|---|---|
| `spread` (by az) | One task per AZ | High availability (default) |
| `spread` (by host) | One task per host | Maximum isolation (wasteful) |
| `binpack` (by memory) | Pack tasks densely by memory | Cost optimization |
| `binpack` (by cpu) | Pack tasks densely by CPU | Cost optimization |
| `random` | No strategy | Not recommended for production |

**Switch to binpack:**
```bash
aws ecs update-service \
  --cluster <cluster> \
  --service <service> \
  --placement-strategy type=binpack,field=memory type=spread,field=attribute:ecs.availability-zone
```

This strategy: binpack by memory first, then spread across AZs for
availability.

### Step 11: Service auto-scaling vs scheduled scaling

For predictable workloads (business hours, nightly batch), scheduled
scaling eliminates the reaction-time lag of target tracking.

**Decision gate:**

| Workload pattern | Recommended scaling |
|---|---|
| Unpredictable (spiky, event-driven) | Target tracking (service auto-scaling) |
| Predictable (business hours, nightly batch) | Scheduled scaling + target tracking |
| Seasonal (holiday peaks) | Scheduled scaling for known peaks |

**Scheduled scaling:**
```bash
aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --resource-id service/<cluster>/<service> \
  --scalable-dimension ecs:service:DesiredCount \
  --scheduled-action-name business-hours-scale-up \
  --schedule "cron(0 9 ? * MON-FRI *)" \
  --scalable-target-action MinCapacity=10,MaxCapacity=50
```

### Step 12: Impact estimation

Compute the utilization improvement for each recommendation:

```
current_host_count = describe-container-instances count
current_avg_utilization = avg(CPUUtilization or MemoryUtilization)
projected_host_count = current_host_count × (current_avg_utilization / target_utilization)
host_savings = current_host_count - projected_host_count
monthly_savings = host_savings × 730 hours × $/hour

# For spot migration:
spot_savings = on_demand_hours_converted × 730 × (on_demand_rate - spot_rate)
```

Always state assumptions: target utilization, spot discount rate (70%
typical), node type, and region.

### Step 13: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions verified AND managed scaling + spot base + binpack +
  tuned cooldown in place → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (metrics absent, window < 14 days) → **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO` / `BLOCKED` gate.

## Output format

```text
TARGET: <cluster-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <capacity provider strategy>, managed scaling <on/off>, placement <strategy>,
    cooldown <seconds>, target tracking <metric>
  Proposed: <capacity provider strategy>, managed scaling <on/off>, placement <strategy>,
    cooldown <seconds>, target tracking <metric>
  Dimensions changed: <cp_strategy | managed_scaling | target_tracking | cooldown | bin_packing | fargate | warmup | drain | desired_running_gap | placement_strategy | scaling_mode>
  Dimensions checked: <list ALL eleven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_IMPACT:
  Current host count: <count>, avg utilization <percent>
  Projected host count: <count>, avg utilization <percent>
  Host reduction: <count> (<percent>)
  Monthly savings: $<amount>
  Assumptions: <list (node type, spot discount, target utilization, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <cluster-name> in <region>.
  Proceed? (yes/no)"
```

Full worked examples are in `references/worked-examples-and-edge-cases.md`.

## STRICT output contract

These rules are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block before returning.

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Host reduction: 0` AND `Monthly savings: $0.00`.** If every dimension
   nets zero improvement, the verdict MUST be `OPTIMIZED`.
2. **NEVER show savings math that does not balance.** `Current host count
   - Host reduction == Projected host count`.
3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.
4. **NEVER recommend spot capacity provider without verifying the
   workload tolerates interruption.** Stateful, long-running, or
   latency-critical tasks must stay on on-demand.
5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all eleven dimensions.
6. **NEVER recommend switching to binpack without also recommending AZ
   spread as a secondary strategy.** Pure binpack risks all tasks on one
   host per AZ. Use `binpack` + `spread by az` combined.
7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE

```text
TARGET: ecs-prod-cluster
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster uses all on-demand capacity provider with spread
  placement. Average CPU utilization is 35% and 8 of 20 container
  instances have 0 running tasks (40% stranded). Managed scaling is
  disabled (legacy cluster-autoscaler). Switching to managed scaling +
  spot capacity provider (base on-demand=2, spot weight=4) + binpack
  placement reduces host count by 40% and captures 70% spot discount on
  burst capacity.
RECOMMENDATION:
  Current: all on-demand, managed scaling off, placement spread-by-host,
    cooldown 300 s, target tracking CPU=60%
  Proposed: on-demand base=2 + spot weight=4, managed scaling on,
    placement binpack-by-memory + spread-by-az, cooldown 120 s,
    target tracking CPU=65%
  Dimensions changed: cp_strategy + managed_scaling + placement_strategy +
    cooldown + bin_packing
  Dimensions checked: cp_strategy → (add spot)  managed_scaling → (enable)
    target_tracking ✓ (CPU is correct for this workload)  cooldown →
    (300→120)  bin_packing → (enable)  fargate ✓ (EC2 needed for >4 vCPU)
    warmup ✓ (60 s configured)  drain ✓ (no issues)  desired_running_gap ✓
    (no stuck tasks)  placement_strategy → (spread→binpack)  scaling_mode ✓
    (target tracking appropriate)
  Confidence: HIGH — 40% empty hosts confirmed via
    describe-container-instances; workload is stateless microservices
    (burst-tolerant for spot); CPU < 40% confirms headroom for binpack.
ESTIMATED_IMPACT:
  Current host count: 20, avg utilization 35% CPU, 28% memory
  Projected host count: 12, avg utilization 58% CPU, 47% memory
  Host reduction: 8 (40%)
  Monthly savings: $2,120.00
    on-demand reduction: 8 hosts × 730 h × $0.4032/h = $2,352.00
    spot premium offset: -2 spot hosts × 730 h × $0.1208/h (spot rate)
      = -$232.00 (spot hosts added for burst at 70% discount)
    net: $2,120.00/month
  Assumptions: m5.2xlarge at $0.384/h on-demand, $0.1152/h spot (us-east-1),
    target utilization 60% CPU, 70% spot discount.
MIGRATION_STEPS:
  1. Create spot capacity provider:
     aws ecs create-capacity-provider --name spot-cp \
       --auto-scaling-group-provider autoScalingGroupArn=<spot-asg-arn>,managedScaling.status=ENABLED,managedScaling.targetCapacity=100
  2. Update service with new capacity provider strategy + binpack:
     aws ecs update-service --cluster ecs-prod-cluster --service api-service \
       --capacity-provider-strategy capacityProvider=on-demand-cp,weight=1,base=2 capacityProvider=spot-cp,weight=4,base=0 \
       --placement-strategy type=binpack,field=memory type=spread,field=attribute:ecs.availability-zone
  3. Enable managed scaling on the on-demand capacity provider:
     aws ecs update-capacity-provider --name on-demand-cp \
       --auto-scaling-group-provider managedScaling.status=ENABLED,managedScaling.targetCapacity=100,instanceWarmupPeriod=60
  4. Update scale-in cooldown to 120 s:
     aws application-autoscaling put-scaling-policy --policy-name api-cpu-scaling \
       --policy-type TargetTrackingScaling --resource-id service/ecs-prod-cluster/api-service \
       --scalable-dimension ecs:service:DesiredCount --service-namespace ecs \
       --target-tracking-scaling-policy-configuration TargetValue=65.0,PredefinedMetricSpecification={PredefinedMetricType=ECSServiceAverageCPUUtilization},ScaleOutCooldown=60,ScaleInCooldown=120
  5. Monitor host count and empty instances for 7 days.
CONFIRM: About to update-service on ecs-prod-cluster (spread→binpack,
  add spot CP, enable managed scaling). Host reduction 40%; monthly
  savings $2,120. Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current host count - Host reduction == Projected host count`?
- [ ] All eleven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, utilization-improving or cost-reducing recommendation. |
| `OPTIMIZED` | All dimensions pass (managed scaling + spot base + binpack + tuned cooldown in place); OR a change was applied and verified this session. |
| `NEED_MORE_INFO` | Data gate failed: ECS API data empty, CloudWatch window < 14 days, or capacity providers inaccessible. |
| `BLOCKED` | Hard precondition prevents evaluation: cluster in deletion, IAM denies ecs:DescribeClusters, ASG MinSize locked above need. |

**Zero-improvement rule:** If host_reduction == 0 AND monthly_savings ==
$0 for every dimension, verdict MUST be `OPTIMIZED`, never
`FURTHER_OPTIMIZATION_AVAILABLE`.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend spot capacity provider for stateful or latency-
   critical workloads.** Spot instances can be reclaimed with 2-minute
   notice. Stateful tasks (databases, caches with no replication) and
   single-instance latency-critical services must run on on-demand.

2. **NEVER recommend binpack placement without AZ spread as a secondary
   strategy.** Pure binpack concentrates tasks on the fewest hosts,
   risking all tasks on one AZ if that AZ fails. Always use
   `binpack` + `spread by az` combined.

3. **NEVER reduce scale-in cooldown below 60 s.** Sub-60 s cooldowns
   cause flapping — instances scale in before warm-up completes, then
   immediately scale back out. The minimum safe cooldown is 60 s.

4. **NEVER recommend managed scaling without verifying the ASG MaxSize
   is adequate.** Managed scaling only scales within the ASG's MinSize
   to MaxSize range. If MaxSize is too low, scale-out will stall
   silently.

5. **NEVER assume desired count == running count means the cluster is
   healthy.** A service with desired=running=10 but all tasks on one
   host is a single point of failure. Always check placement spread
   across hosts AND AZs.

Extended anti-patterns in `references/worked-examples-and-edge-cases.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Drain instances before terminating.** Never force-terminate a
  container instance with running tasks. Set to `DRAINING` and wait.
- **Capacity provider changes apply to new tasks.** Existing tasks
  continue on their current placement until rescheduled.
- **Placement strategy changes are immediate.** New tasks use the new
  strategy; existing tasks are NOT automatically rescheduled.
- **Spot capacity provider requires a matching ASG.** The spot ASG must
  use a spot-percentage-based launch template.
- **Managed scaling conflicts with external auto-scalers.** Disable the
  legacy Cluster Autoscaler before enabling managed scaling on the same
  ASG. Running both causes race conditions.
- **Scale-in cooldown changes apply immediately.** A shorter cooldown
  may cause rapid scale-in during a traffic dip — verify tolerance.
- **Fargate tasks cannot use host networking or privileged mode.**
  Verify task definition compatibility before recommending Fargate.
- **Binpack placement concentrates risk.** Always pair with AZ spread.
- **Bulk-operation limit:** Process at most 3 clusters per batch. Sort
  by estimated savings, verify each batch first.

## Recent AWS features (2024-2026)

- **Managed EC2 capacity provider auto-scaling (GA 2024):** Native ECS
  managed scaling on `CapacityProviderReservation`. Replaces the legacy
  Cluster Autoscaler for ECS.
- **Capacity provider weight and base refinement (2024-2025):** `base`
  on on-demand guarantees a minimum task floor; `weight` controls the
  distribution ratio across providers.
- **Fargate capacity up to 16 vCPU / 120 GB (2024):** Expanded task
  size limits for larger workloads.
- **ECS Service Connect (2024-2025):** Built-in service mesh for
  inter-task communication. Does not affect capacity provider tuning.
- **Bottlerocket AMI for ECS (2024):** Minimal boot time (15-30 s).
  Reduces `instanceWarmupPeriod` from 60 s to 30 s.
- **Spot instance interruption handler (2024-2025):** ECS drains tasks
  on spot instances receiving a 2-minute reclaim notice automatically.
- **CapacityProviderReservation CloudWatch metric (2024):** Direct
  visibility into managed scaling target capacity percentage.
- **Application Auto Scaling dual-policy (2025):** A service can now
  have both CPU and memory target-tracking policies simultaneously.

## References

- `references/ecs-autoscaling-configuration-and-pricing.md` — pricing
  tables, EC2 instance type reference, capacity provider JSON schema,
  target tracking metric guide, spot discount rates, warm-up period
  guidance, regional pricing multipliers.
- `references/worked-examples-and-edge-cases.md` — full worked examples
  (managed scaling migration, spot strategy, binpack, target tracking,
  already-optimal, NEED_MORE_INFO, end-to-end walkthrough), CLI failure
  handling, operational edge cases, extended NEVER list.

## Domain

AWS CloudOps / ECS Compute Autoscaling & FinOps.

## AWS documentation

- **Amazon Elastic Container Service Developer Guide** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html
- **ECS Capacity Providers** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-capacity-providers.html
- **ECS Managed Scaling** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/asg-capacity-providers.html
- **ECS Service Auto Scaling** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html
- **ECS Target Tracking Policies** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/application-auto-scaling-target-tracking.html
- **ECS Task Placement** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-placement.html
- **AWS Fargate** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/AWS_Fargate.html
- **Spot Instances for ECS** — https://docs.aws.amazon.com/AmazonECS/latest/developerguide/container-instance-spot.html
- **Application Auto Scaling** — https://docs.aws.amazon.com/autoscaling/application/userguide/what-is-application-auto-scaling.html
- **AWS CLI ECS reference** — https://docs.aws.amazon.com/cli/latest/reference/ecs/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
