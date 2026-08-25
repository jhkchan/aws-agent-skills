---
name: ecs-cluster-autoscaling-optimizer
description: 'Optimises Amazon ECS cluster autoscaling across eleven dimensions: capacity provider strategy (spot vs on-demand weight and base — the spot base + on-demand burst pattern), managed EC2 capacity provider auto-scaling (replaces the legacy Cluster Autoscaler / cluster-autoscaler project with native ECS managed scaling), target tracking metric selection (ECSServiceAverageCPUUtilization vs ECSServiceAverageMemoryUtilization vs ALB RequestCountPerTarget), scale-in cooldown tuning (default 300 s is too long for spiky workloads), bin-packing efficiency (detecting empty hosts and stranded resources), Fargate capacity provider (no capacity planning needed for serverless tasks), EC2 instance warm-up time (AMI boot + container agent registration delay), drain instance lifecycle (DRAINING to DEPROVISIONING state management for graceful task migration), desired count vs running count gap analysis (detecting stuck or pending tasks), task placement strategy (spread vs binpack vs random for optimal host utilization), and...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted ECS describe-clusters/describe-services output, capacity provider JSON, and CloudWatch ECSInsights metrics. Live-account optimization uses aws ecs describe-clusters, aws ecs describe-services, aws ecs describe-capacity-providers, aws ecs describe-container-instances, aws ecs describe-tasks, aws application-autoscaling describe-scaling-policies, aws...
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
  when_to_use: Optimising ECS cluster autoscaling, switching from Cluster Autoscaler to managed EC2 capacity provider, tuning capacity provider strategy (spot vs on-demand), selecting target tracking metrics, tuning scale-in cooldown, detecting bin-packing waste and empty hosts, managing drain instance lifecycle, evaluating Fargate vs EC2 capacity provider, choosing service auto-scaling vs scheduled scaling, or improving task placement strategy.
  when_not_to_use: EC2 instance rightsizing (use ec2-rightsizing-optimizer), EKS cluster autoscaling (use eks-autoscaling-optimizer — different API surface), ECS task-level troubleshooting (container crashes, task failures, health-check issues — use the ECS troubleshooter), ECS service mesh or App Mesh configuration, or Fargate capacity provisioning (Fargate has no capacity planning surface). This skill focuses on cluster-level autoscaling optimization, not functional debugging of broken tasks.
  activation_triggers: optimise ECS autoscaling, ECS capacity provider, ECS managed scaling, ECS Cluster Autoscaler migration, ECS spot capacity provider, ECS bin-packing, ECS binpack placement, ECS task placement strategy, ECS scale-in cooldown, ECS drain instances, ECS DRAINING lifecycle, ECS target tracking, ECS Fargate capacity provider, ECS scheduled scaling, ECS service autoscaling, ECS empty host detection, ECS FinOps, ECS cluster utilization
  invocation_schema: 'Input: either (a) a cluster name + live-account context, (b) a describe-clusters/describe-services/describe-capacity-providers JSON payload, OR (c) CloudWatch CapacityProviderReservation and ECSServiceAverageCPUUtilization metrics with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_IMPACT/MIGRATION_STEPS block per cluster, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline capacity provider classification):\nClusterName: ecs-prod-cluster\nLaunch type: EC2 (2 capacity providers: on-demand, spot)\nCapacity provider strategy: on-demand weight=4, base=2; spot weight=1, base=0\nManaged scaling: disabled (using legacy cluster-autoscaler)\nPlacement strategy: spread by az\nScale-in cooldown: 300 s (default)\nMetrics (last 30 days):\n  - CPUUtilization avg: 35%, p95: 55%\n  - MemoryUtilization avg: 28%, p95: 45%\n  - CapacityProviderReservation (on-demand): avg 60%\n  - RunningEC2Tasks avg: 40, DesiredTasks avg: 40\n  - Empty container instances: 8 of 20 (40% stranded)\nEmit the standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: ECS, ECS cluster, capacity provider, managed scaling, Cluster Autoscaler, spot instances, on-demand, bin-packing, binpack, task placement, spread strategy, Fargate, target tracking, ECSServiceAverageCPUUtilization, scale-in cooldown, drain instances, DRAINING, DEPROVISIONING, scheduled scaling, service autoscaling, capacity provider strategy, Compute, FinOps
  tags: ecs, compute, autoscaling, capacity-provider, cost-optimization, finops, bin-packing, spot-instances
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

Quick-start headline rules moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for the five headline rules (managed scaling, spot base + burst, binpack, cooldown, empty hosts).

## Mindset

Mindset prose and the four guiding principles moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when framing a recommendation (managed vs legacy scaling, hybrid spot pattern, binpack, cooldown control).

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
Required data-source listing moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when pulling cluster, service, capacity-provider, container-instance, scaling-policy, CloudWatch, and EC2 data.

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

Step 0 non-obvious behaviours moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a recommendation depends on a non-obvious behaviour (base/weight semantics, CapacityProviderReservation, dual cooldowns, drain lifecycle, warm-up, 2-minute spot notice).

### Step 1: Capacity provider strategy — spot vs on-demand

Step 1 prose and the capacity provider strategy JSON moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when authoring a spot + on-demand capacity provider strategy.

**Decision gate:**

| Current strategy | Workload | Verdict | Action |
|---|---|---|---|
| All on-demand, no spot | Burst-tolerant (batch, async, stateless) | **FURTHER_OPTIMIZATION_AVAILABLE** | Add spot CP with weight=4, base=0; set on-demand base=2 |
| All on-demand, no spot | Latency-sensitive (API, real-time) | KEEP on-demand | Proceed to other dimensions |
| Pure spot, no on-demand base | Any workload with availability SLO | **FURTHER_OPTIMIZATION_AVAILABLE** | Add on-demand base=2 for steady-state floor |
| On-demand base + spot weight already | Optimal hybrid | No CP finding | Proceed to other dimensions |

Create-spot-capacity-provider CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when applying the Step 1 recommendation.

### Step 2: Managed scaling vs Cluster Autoscaler

Step 2 prose and the describe-capacity-providers detection CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand for the Cluster Autoscaler to managed scaling migration.

If `managedScaling.status = DISABLED` or the cluster uses a standalone
`cluster-autoscaler` deployment, migrate to managed scaling.

Enable-managed-scaling CLI (put-cluster-capacity-providers + update-capacity-provider) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when applying the managed scaling migration.

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

Cooldown tuning CLI (application-autoscaling put-scaling-policy) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when applying a scale-in cooldown change.

### Step 5: Bin-packing efficiency (empty host detection)

Empty or under-utilized hosts are the primary source of ECS waste.

Step 5 empty-host detection CLI, ratio math, and resolution steps moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when quantifying and eliminating stranded capacity.

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

Warm-up tuning CLI (update-capacity-provider instanceWarmupPeriod) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when adjusting EC2 instance warm-up.

### Step 8: Drain instance lifecycle (DRAINING to DEPROVISIONING)

When the managed capacity provider scales in, instances go through
`DRAINING` before `DEPROVISIONING`. During `DRAINING`, ECS reschedules
tasks to other instances.

Step 8 drain monitoring CLI and drain-time resolution steps moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when drain time exceeds 300 s.

### Step 9: Desired count vs running count gap analysis

If `runningTasksCount < desiredCount` sustained, tasks cannot be placed.
This is a capacity signal, not a configuration tuning issue.

Step 9 desired-vs-running gap detection CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when diagnosing stuck or pending tasks.

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

Switch-to-binpack CLI (update-service placement-strategy) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when applying the Step 10 recommendation.

### Step 11: Service auto-scaling vs scheduled scaling

For predictable workloads (business hours, nightly batch), scheduled
scaling eliminates the reaction-time lag of target tracking.

**Decision gate:**

| Workload pattern | Recommended scaling |
|---|---|
| Unpredictable (spiky, event-driven) | Target tracking (service auto-scaling) |
| Predictable (business hours, nightly batch) | Scheduled scaling + target tracking |
| Seasonal (holiday peaks) | Scheduled scaling for known peaks |

Scheduled scaling CLI (put-scheduled-action) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand for predictable business-hours or nightly batch workloads.

### Step 12: Impact estimation

Impact estimation formula and assumptions moved verbatim to [references/ecs-autoscaling-configuration-and-pricing.md](references/ecs-autoscaling-configuration-and-pricing.md).
Load on demand when computing host reduction and monthly savings.

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

Pre-flight safety checks (CONFIRMATION GATE, drain rules, capacity-provider caveats, batch limits) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before executing any state-changing optimization CLI.

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when evaluating managed scaling GA, Fargate 16 vCPU/120 GB, Service Connect, Bottlerocket, or dual-policy scaling.

## References

- `references/ecs-autoscaling-configuration-and-pricing.md` — pricing
  tables, EC2 instance type reference, capacity provider JSON schema,
  target tracking metric guide, spot discount rates, warm-up period
  guidance, regional pricing multipliers.
- `references/worked-examples-and-edge-cases.md` — full worked examples
  (managed scaling migration, spot strategy, binpack, target tracking,
  already-optimal, NEED_MORE_INFO, end-to-end walkthrough), CLI failure
  handling, operational edge cases, extended NEVER list.

## References (load on demand)

- [references/diagnostic-commands.md](references/diagnostic-commands.md) — required data sources, per-step detection/tuning CLI, and pre-flight safety checks moved from SKILL.md.
- [references/advanced-patterns.md](references/advanced-patterns.md) — quick-start rules, mindset, Step 0 non-obvious behaviours, and recent AWS features moved from SKILL.md.
- [references/ecs-autoscaling-configuration-and-pricing.md](references/ecs-autoscaling-configuration-and-pricing.md) — pricing tables, capacity provider JSON schema, warm-up guidance, and the Step 12 impact estimation formula moved from SKILL.md.
- [references/worked-examples-and-edge-cases.md](references/worked-examples-and-edge-cases.md) — full worked examples, CLI failure handling, operational edge cases, extended NEVER list.

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
