---
name: autoscaling-policy-deployer
description: >-
  Provisions Amazon EC2 Auto Scaling policies and surrounding primitives with
  production defaults: target tracking (CPUUtilization, ALBRequestCountPerTarget,
  custom metrics), step scaling (CloudWatch alarm → step adjustments), scheduled
  scaling, warm pools, instance refresh, capacity rebalance, predictive scaling
  (ML-based forecast), and Mixed Instances Policy (On-Demand + Spot blend).
  Emits READY_TO_DEPLOY / PREREQUISITES_MISSING with every item verified and
  copy-pasteable autoscaling / cloudwatch commands. Use when attaching a
  scaling policy, configuring scheduled actions, enabling warm pool or
  capacity rebalance, triggering an instance refresh, or blending On-Demand
  with Spot. Triggers: Auto Scaling policy, target tracking, step scaling,
  scheduled action, warm pool, instance refresh, capacity rebalance,
  predictive scaling, Mixed Instances Policy.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Live provisioning uses AWS CLI v2 with autoscaling
  (put-scaling-policy, put-scheduled-update-group-action, put-warm-pool,
  start-instance-refresh, update-auto-scaling-group, create-auto-scaling-group),
  cloudwatch (put-metric-alarm), ec2 (describe-launch-templates,
  describe-instance-types), and cloudformation / terraform
  aws_autoscaling_* equivalents.
keywords:
  - aws
  - ec2
  - autoscaling
  - auto-scaling-group
  - target-tracking
  - step-scaling
  - scheduled-scaling
  - warm-pool
  - instance-refresh
  - capacity-rebalance
  - predictive-scaling
  - mixed-instances-policy
  - spot-instances
  - cloudops
  - deploy
tags:
  - aws
  - autoscaling
  - ec2
  - scaling-policy
  - spot-instances
  - warm-pool
  - instance-refresh
  - deploy
  - compute
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  when_to_use: >-
    Attaching a scaling policy (target tracking, step, predictive) to an
    existing Auto Scaling Group, configuring recurring scheduled scaling
    actions, enabling a warm pool for fast scale-out, triggering or
    scheduling an instance refresh for rolling template updates, enabling
    capacity rebalance for Spot-backed ASGs, defining a Mixed Instances
    Policy with On-Demand + Spot blend and allocation strategy, or
    generating IaC (CloudFormation / Terraform) for any of the above. Do
    NOT invoke for ECS Service Auto Scaling (use ecs-fargate-deployer),
    for DynamoDB capacity (use dynamodb-table-deployer), or for ASG audit
    posture (use autoscaling-group-auditor).
  activation_triggers:
    - "Auto Scaling policy"
    - "target tracking scaling"
    - "step scaling policy"
    - "scheduled scaling action"
    - "warm pool"
    - "instance refresh"
    - "capacity rebalance"
    - "predictive scaling"
    - "Mixed Instances Policy"
    - "Spot Instance diversification"
    - "ASG scaling plan"
  invocation_schema: >-
    Input: an Auto Scaling Group name + one or more scaling configurations
    (target tracking metric+target, step scaling alarm+adjustments,
    scheduled action recurrence, warm pool spec, instance refresh trigger,
    capacity rebalance enablement, predictive scaling forecast, Mixed
    Instances Policy spec). Output: deterministic POLICY_SPEC / VERDICT /
    CHECKLIST / VERIFICATION_COMMANDS block per the STRICT output contract,
    where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.
---

# Auto Scaling Policy Deployer

## What this skill does

Provisions Amazon EC2 Auto Scaling scaling policies, scheduled actions,
and surrounding primitives (warm pool, instance refresh, capacity
rebalance, Mixed Instances Policy) with correct defaults. The skill walks
a 9-step procedure, surfaces the silent-failure modes unique to ASG
scaling (most dangerous: two scaling policies on the same metric fight
each other; predictive scaling silently emits no forecast with < 24h of
history; capacity rebalance no-ops on an ASG with no Spot capacity), and
emits a READY_TO_DEPLOY checklist verifying every item against actual
state. The single most common incident this skill prevents: an operator
adds a step scaling policy on top of a target tracking policy for the
same metric, the ASG oscillates between scaling out and in, and the
CloudWatch alarms enter INSUFFICIENT_DATA with no error surfaced.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Provisioning summary (9 steps), verdict thresholds, dependency graph | Before any operation |
| **Activation keywords** | Phrases that route to this skill | Disambiguating routing |
| **Invocation contract** | Required literal labels in the response | Formatting the response |
| **Reasoning framework** | Why the 9-step order matters; policy-type semantics | Understanding the deploy model |
| **Dependency graph** | Which configs silently no-op without their prerequisite | Debugging "policy doesn't fire" |
| **Expert heuristic** | The dual-policy trap; predictive scaling history; warm-pool drain race | Pre-empt production incidents |
| **Prerequisites** | What to verify before emitting any command | Avoid PREREQUISITES_MISSING rework |
| **9-step procedure** | The actual provisioning with copy-pasteable CLI | Executing the deploy |
| **NEVER (top 5)** | Hard rules that prevent oscillation / silent Spot loss | Review before deploy |
| **STRICT output contract** | Required POLICY_SPEC / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block | Formatting the response |
| **Recent AWS features** | Predictive scaling, capacity rebalance, warm pool checkpoints | Stay current |

## Quick reference — provisioning summary (9 steps)

| Step | Action | Reversible? | Key risk if skipped |
|---|---|---|---|
| 1 | Confirm ASG baseline (launch template, min/max/desired, subnets, health checks) | — | policies on a misconfigured ASG amplify outages |
| 2 | Choose scaling policy type(s) — one per metric dimension | Yes | **silent oscillation** if two policies on same metric |
| 3 | Configure target tracking (recommended default: CPU or ALB RequestCountPerTarget) | Yes | custom metric that stops emitting → ASG freezes |
| 4 | Configure step scaling (CloudWatch alarm → step adjustments) on a DIFFERENT metric | Yes | alarm in INSUFFICIENT_DATA forever — never fires |
| 5 | Configure scheduled scaling (recurrence) for known peaks/troughs | Yes | timezone mismatch — scales at wrong hour |
| 6 | Configure warm pool (pre-initialized instances for fast scale-out) | Yes | incompatible launch template → warm instances fail health |
| 7 | Trigger instance refresh (rolling update of existing instances) | Yes | no checkpoints → can't pause/rollback |
| 8 | Configure advanced: capacity rebalance (Spot), predictive scaling, Mixed Instances Policy | Yes | capacity rebalance no-op on On-Demand-only ASG |
| 9 | Verify every configuration item against actual state + emit checklist | — | silent no-ops |

**Critical ordering constraints:** ASG baseline before policies (scaling
amplifies any underlying misconfiguration); one policy type per metric
dimension before adding more (prevents the dual-policy trap); alarm
creation before step scaling policy (policy references the alarm);
warm pool before instance refresh (warm pool pre-seeds replacement
instances); capacity rebalance enabled before raising Spot fraction.
Rationale and the silent-failure table are below.

## Activation keywords

Auto Scaling policy, target tracking scaling, step scaling, scheduled
scaling action, recurring scaling, warm pool, pre-initialized instances,
instance refresh, rolling update ASG, capacity rebalance, Spot Instance
replacement, predictive scaling, ML-based scaling forecast, Mixed
Instances Policy, On-Demand + Spot blend, capacity-optimized,
lowest-price, prioritized Spot allocation strategy, launch template
override, ASG scaling plan.

## Invocation contract (hard requirement)

When this skill is invoked with an ASG scaling provisioning request,
the agent MUST respond with the checklist defined in §"STRICT output
contract" using the literal all-caps labels `POLICY_SPEC:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

## Reasoning framework (why the provisioning order matters)

Auto Scaling policies look like "a rule that adds or removes capacity"
but the underlying model has four traps:

1. **Multiple scaling policies on the same metric fight each other.**
   Target tracking on CPU and step scaling on CPU both emit scale
   activities against the same capacity dimension. The ASG honors
   whichever alarm fires first; alarms enter conflicting states
   (target tracking ALARM while step scaling OK), producing
   oscillation. Use ONE policy type per metric dimension.

2. **Target tracking creates its own CloudWatch alarms.** Operators
   sometimes hand-author an alarm for the same metric the target
   tracking policy already manages. The two alarms double-fire on the
   same threshold breach. Target tracking's internal alarms are visible
   via `describe-alarms` and prefixed with the policy name — never
   hand-author a duplicate.

3. **Step scaling with a missing datapoint never fires.** A step
   scaling alarm with insufficient data points enters
   `INSUFFICIENT_DATA` and produces no scaling activity. Operators
   assume "no alarm = healthy" when in fact the metric isn't being
   emitted. Always set `TreatMissingData` explicitly.

4. **Predictive scaling, warm pool, capacity rebalance, and Mixed
   Instances Policy have their own silent-failure modes.** Predictive
   scaling needs 24h+ of CloudWatch data or forecasts are empty; warm
   pool instances that fail launch-template health checks silently fall
   back to cold start; capacity rebalance is a no-op on an On-Demand-only
   ASG; Mixed Instances Policy with the wrong allocation strategy
   produces unexpected instance-type selection.

## Dependency graph (silent-failure table)

| Configuration | Hard dependencies (API error without) | Silent failure mode (returns 200, does nothing) | Enables downstream |
|---|---|---|---|
| Target tracking (predefined metric) | ASG exists; metric in same region/account | **custom metric stops emitting → ASG freezes at last capacity** | hands-off scaling |
| Target tracking (custom metric) | ASG exists; custom namespace emitting; `Dimensions` match ASG | **wrong `Dimensions` → ASG sees no datapoints, never scales; no error** | custom-app scaling |
| Step scaling policy | ASG exists; CloudWatch alarm ARN valid | alarm stuck in `INSUFFICIENT_DATA` → policy never fires; CloudWatch shows OK | threshold-reactive scaling |
| Scheduled scaling action | ASG exists; recurrence cron valid; timezone set | **UTC vs local timezone mismatch → scales at wrong hour; no error signal** | known-peak capacity |
| Warm pool | ASG exists; launch template version valid | **launch template change incompatible with warm pool AMI → warm instances fail health, cold start transparently** | fast scale-out |
| Instance refresh | ASG exists; launch template has new version | no checkpoints configured → cannot pause/rollback at 50% | safe template rollout |
| Capacity rebalance | ASG exists; `--capacity-rebalance` true | **no Spot capacity in ASG → rebalance no-ops silently** | Spot reliability |
| Predictive scaling | ASG exists; >= 24h CloudWatch traffic data | **< 24h history → forecasts empty, policy does nothing; no error surfaced** | proactive scaling |
| Mixed Instances Policy | ASG exists; launch template + overrides | **`prioritized` strategy with one type → falls back to single-type; allocation strategy silently ignored** | Spot diversification |
| Spot Instance allocation strategy | Mixed Instances Policy defined | `capacity-optimized` on launch template without `SpotPlacement` → unexpected AZ | Spot cost/availability |

**The four silent-failure rows are the ones a baseline model misses.**
Custom metric with wrong dimensions, scheduled action timezone
mismatch, capacity rebalance on an On-Demand ASG, and predictive
scaling with insufficient history all return success and only
post-config verification (Step 9) catches the gap. This is why the
procedure verifies every item rather than trusting the API response.

## Expert heuristic: the dual-policy trap

The most dangerous scaling misconfiguration: two scaling policies on
the SAME metric dimension.

```text
Operator thinks:               What actually happens:
CPU target tracking 50% +      Both policies' alarms evaluate the same
CPU step scaling alarm 70%  →  metric; target tracking scales out at 50%,
                               step alarm fires at 70%, both activities
                               land on the same ASG; on cooldown, target
                               tracking scales back in while step alarm
                               is still ALARM; ASG oscillates.
```

The correct model: ONE reactive policy per metric dimension. If you
need both proactive and reactive scaling on CPU, use predictive
scaling (proactive) + target tracking (reactive), NOT two reactive
policies. The tell-tale signal in CloudWatch: two `ScalingPolicies`
for the same ASG both keyed on the same metric name.

## Expert heuristic: predictive scaling's history requirement

Predictive scaling looks like "ML forecasts your traffic." Two
operational truths are routinely missed:

1. **Predictive scaling needs >= 24h of CloudWatch data.** A fresh ASG
   or one with sparse traffic has empty forecasts. The `LoadMetric`
   (typically `CPUUtilization`) must have at least one full day of
   datapoints. Operators enable predictive scaling on day 1, see no
   forecasts, and assume the feature is broken. Remedy: check
   `describe-scaling-policies` for empty `LoadForecast` datapoints;
   wait 24h before validating.

2. **`Mode` controls whether capacity is pre-provisioned.** The default
   `ForecastOnly` emits forecasts but does NOT provision capacity —
   operators read "predictive scaling enabled" as "scaling is
   happening." `ForecastAndScale` is required for actual
   pre-provisioning. Verify the mode with `describe-scaling-policies`.

## Expert heuristic: warm pool drain race and capacity rebalance

The warm pool holds pre-initialized instances to speed scale-out. Two
race conditions are routinely missed:

1. **Capacity rebalance can drain the warm pool prematurely.** When a
   Spot Instance interruption is signaled, capacity rebalance launches
   a replacement from the warm pool — but the warm pool's `MinSize` is
   the buffer for scale-out, not for Spot replacement. Operators set
   `WarmPoolMinSize=0`, a Spot interruption drains the pool, and the
   next scale-out falls back to cold start. Remedy: set
   `WarmPoolMinSize >= 1` on Spot-backed ASGs.

2. **Instance refresh consumes the warm pool's instances.** A rolling
   refresh pulls instances from the warm pool to satisfy
   `MinHealthyPercentage`. Without a warm pool checkpoint, the refresh
   depletes the buffer. Remedy: enable warm pool BEFORE triggering
   instance refresh, and set `InstanceWarmup` >= the application's
   health-check grace period.

## Prerequisites (verify before provisioning)

Before emitting any provisioning command, verify these prerequisites.
If any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| ASG exists and is healthy | Policies on a non-existent ASG error; on a degraded ASG amplify outages | `aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <ASG>` |
| Launch template / configuration | Target tracking, warm pool, instance refresh all reference a valid template | `aws ec2 describe-launch-templates --launch-template-names <LT>` |
| Min/max/desired sensible | Scheduled scaling with `MinSize > MaxSize` is a silent failure | `describe-auto-scaling-groups` — verify Max >= Desired >= Min |
| VPC subnets across >= 2 AZs | Single-AZ ASG cannot rebalance on Spot interruption | `describe-auto-scaling-groups --query AutoScalingGroups[].VPCZoneIdentifier` |
| Health check type | `ELB` health checks required for ALB-backed target tracking on `ALBRequestCountPerTarget` | `describe-auto-scaling-groups --query AutoScalingGroups[].HealthCheckType` |
| CloudWatch metric emitting | Custom metric target tracking / step scaling alarm needs live datapoints | `aws cloudwatch get-metric-statistics --namespace ... --metric-name ...` |
| Target Group ARN (ALB metric) | `ALBRequestCountPerTarget` requires the Target Group attached to the ASG | `describe-load-balancer-target-groups --auto-scaling-group-name <ASG>` |
| IAM service-linked role | `AWSServiceRoleForAutoScaling` must exist (created automatically, but verify in hardened accounts) | `aws iam get-role --role-name AWSServiceRoleForAutoScaling` |
| >= 24h CloudWatch history (predictive only) | Predictive scaling forecasts are empty without history | `aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --start-time ...` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 9-step provisioning procedure

### Step 1 — Confirm ASG baseline

A scaling policy does NOT remediate ASG-level weaknesses. Before
attaching policies, confirm the ASG meets the production baseline:
multi-AZ `VPCZoneIdentifier`, valid launch template version, health
check type matching the metric (ELB health checks for ALB-based
metrics), and Min <= Desired <= Max.

```bash
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <ASG> \
  --query 'AutoScalingGroups[].[AutoScalingGroupName,MinSize,MaxSize,DesiredCapacity,HealthCheckType,VPCZoneIdentifier,LaunchTemplate.LaunchTemplateId]'
```

**Common mistake:** skipping this step because "the policy will adjust
capacity." A policy cannot scale beyond MaxSize; an ASG with MaxSize=1
and a CPU target tracking policy silently caps at 1 instance regardless
of load.

### Step 2 — Choose scaling policy type(s)

Pick ONE policy per metric dimension:

- **Target tracking** (default recommendation): scales to keep a metric
  at a target value. Use `CPUUtilization` (compute-bound),
  `ALBRequestCountPerTarget` (request-driven), or a custom metric
  (application-specific signal like queue depth per instance).
- **Step scaling** (reactive): scales in response to a CloudWatch alarm
  with step adjustments (different capacity changes at different
  thresholds). Use for a DIFFERENT metric than target tracking.
- **Predictive scaling** (proactive): ML-based forecast that
  pre-provisions capacity ahead of predicted demand. Use for workloads
  with a predictable diurnal pattern.

**Common mistake:** layering target tracking and step scaling on the
SAME metric. This is the dual-policy trap (see Expert heuristic). Use
different metric dimensions or predictive + target tracking.

### Step 3 — Configure target tracking

```bash
# Predefined CPU metric (recommended default)
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> --policy-name cpu-target-50 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "PredefinedMetricSpecification": {"PredefinedMetricType": "ASGAverageCPUUtilization"},
    "TargetValue": 50.0, "ScaleOutCooldown": 60, "ScaleInCooldown": 300
  }'

# ALB RequestCountPerTarget (include ResourceLabel from Target Group)
#   "PredefinedMetricType": "ALBRequestCountPerTarget",
#   "ResourceLabel": "app/<ALB>/<TG>", "TargetValue": 1000.0

# Custom metric (e.g., SQS queue depth — verify Dimensions match emitted metric)
#   "CustomizedMetricSpecification": {
#     "MetricName": "ApproximateNumberOfMessagesVisible",
#     "Namespace": "AWS/SQS",
#     "Dimensions": [{"Name": "QueueName", "Value": "my-queue"}],
#     "Statistic": "Average"
#   }, "TargetValue": 100.0
```

**Common mistake:** using a `Dimensions` value that doesn't match the
metric actually emitted. Target tracking silently sees no datapoints
and never scales — no error is surfaced. Verify the metric emits data
with `get-metric-statistics` BEFORE attaching the policy.

**Common mistake:** `TargetValue` for ALB RequestCountPerTarget is
per-instance-per-minute. Setting 1000 means 1000 requests per instance
per minute (~16 RPS per instance). Operators conflate this with RPS and
under-provision.

### Step 4 — Configure step scaling (different metric only)

Step scaling requires a CloudWatch alarm FIRST, then the policy:

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name <ASG>-sqs-depth-high \
  --metric-name ApproximateNumberOfMessagesVisible --namespace AWS/SQS \
  --statistic Average --period 60 --evaluation-periods 2 --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=QueueName,Value=my-queue \
  --treat-missing-data breaching --alarm-actions <POLICY_ARN>

aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> --policy-name sqs-step-scaling-out \
  --policy-type StepScaling --adjustment-type PercentChangeInCapacity \
  --metric-aggregation-type Average \
  --step-adjustments \
    MetricIntervalLowerBound=0,MetricIntervalUpperBound=100,ScalingAdjustment=20 \
    MetricIntervalLowerBound=100,MetricIntervalUpperBound=500,ScalingAdjustment=50 \
    MetricIntervalLowerBound=500,ScalingAdjustment=100
```

**Common mistake:** omitting `--treat-missing-data`. The default
behavior is `missing` (alarm stays in its prior state), which means a
metric that stops emitting never triggers a scale-in. Use `breaching`
for scale-out alarms (missing data = treat as breaching) or
`notBreaching` for scale-in alarms.

**Common mistake:** creating the policy BEFORE the alarm, then
forgetting to attach the policy ARN as an `--alarm-actions`. The
policy exists but never fires.

### Step 5 — Configure scheduled scaling

```bash
aws autoscaling put-scheduled-update-group-action \
  --auto-scaling-group-name <ASG> \
  --scheduled-action-name business-hours-scale-up \
  --recurrence "0 9 * * Mon-Fri" \
  --min-size 3 --desired-capacity 5 --max-size 10 \
  --time-zone "America/New_York"
```

**Common mistake:** omitting `--time-zone`. The default is UTC; an
operator who writes `0 9 * * 1-5` expecting 9 AM local gets 9 AM UTC
(5 AM Eastern). Always specify `--time-zone` and verify with
`describe-scheduled-actions`.

**Common mistake:** setting `MinSize > MaxSize` across overlapping
scheduled actions. Two scheduled actions at the same time with
conflicting bounds produce unpredictable capacity. Verify the schedule
chain: each action's bounds must be consistent with the next.

### Step 6 — Configure warm pool

```bash
aws autoscaling put-warm-pool \
  --auto-scaling-group-name <ASG> \
  --pool-state Stopped \
  --min-size 2 \
  --instance-reuse-policy '{"ReuseOnScaleIn": true}'
```

**Common mistake:** setting `pool-state Running` for cost-sensitive
workloads — Running warm pool instances bill at full On-Demand/Spot
rate. Use `Stopped` (default) for the cost/performance tradeoff;
instances are pre-initialized (EBS volumes persist) but not billing
compute.

**Common mistake:** a launch template change that breaks the warm
pool's AMI. The warm pool continues to hold instances from the OLD
template version; new scale-out pulls instances from the warm pool
that don't match the new template. Always trigger an instance refresh
(Step 7) after a launch template change to cycle the warm pool.

### Step 7 — Trigger instance refresh

```bash
aws autoscaling start-instance-refresh \
  --auto-scaling-group-name <ASG> \
  --strategy Rolling \
  --preferences '{
    "MinHealthyPercentage": 50,
    "InstanceWarmup": 300,
    "CheckpointPercentages": [50, 100],
    "CheckpointDelay": 300
  }'
```

**Common mistake:** omitting `CheckpointPercentages`. Without
checkpoints, the refresh runs to completion with no pause point — a
bad template version rolls through all instances before you can stop.
Set checkpoints at 50% and 100% to allow a pause-and-evaluate gate.

**Common mistake:** triggering instance refresh on an ASG with no
warm pool and aggressive `MinHealthyPercentage=100`. The refresh
cannot replace any instance because doing so drops below 100% healthy.
Either set `MinHealthyPercentage <= 90` or provision a warm pool
first.

### Step 8 — Configure advanced features

#### 8a. Capacity rebalance (Spot-backed ASGs)

```bash
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name <ASG> \
  --capacity-rebalance
```

Capacity rebalance proactively launches a replacement when a Spot
Instance interruption notice is received, then terminates the
interrupted instance after the replacement passes health checks. Pair
with `Mixed Instances Policy` (8c) for diversification.

**Common mistake:** enabling capacity rebalance on an On-Demand-only
ASG. The setting is accepted but no-ops silently because there are no
Spot interruptions to respond to. Verify with
`describe-auto-scaling-groups --query ...MixedInstancesPolicy`.

#### 8b. Predictive scaling

```bash
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name <ASG> \
  --policy-name predictive-cpu-forecast \
  --policy-type PredictiveScaling \
  --predictive-scaling-configuration '{
    "MetricSpecifications": [{
      "TargetValue": 40.0,
      "PredefinedMetricPairSpecification": {
        "PredefinedMetricType": "ASGCPUUtilization",
        "ResourceLabel": ""
      }
    }],
    "Mode": "ForecastAndScale",
    "SchedulingBufferTime": 300,
    "MaxCapacityBreachBehavior": "IncreaseMaxCapacity",
    "MaxCapacityBuffer": 10
  }'
```

**Common mistake:** using `Mode: ForecastOnly` and reading "predictive
scaling enabled" as "scaling is happening." `ForecastOnly` only emits
forecasts; `ForecastAndScale` is required for actual pre-provisioning.

**Common mistake:** insufficient CloudWatch history. Predictive
scaling needs >= 24h of `LoadMetric` data. On a fresh ASG, forecasts
are empty with no error surfaced. Verify with
`describe-scaling-policies` and check the `LoadForecast` datapoints.

#### 8c. Mixed Instances Policy

```bash
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name <ASG> \
  --mixed-instances-policy '{
    "LaunchTemplate": {
      "LaunchTemplateSpecification": {
        "LaunchTemplateName": "my-template",
        "Version": "$Default"
      },
      "Overrides": [
        {"InstanceType": "m5.large"},
        {"InstanceType": "m5a.large"},
        {"InstanceType": "m4.large"}
      ]
    },
    "InstancesDistribution": {
      "OnDemandPercentageAboveBaseCapacity": 50,
      "SpotAllocationStrategy": "capacity-optimized",
      "SpotInstancePools": 3
    }
  }' \
  --min-size 2 --max-size 10 --desired-capacity 4 \
  --vpc-zone-identifier "subnet-abc,subnet-def,subnet-ghi"
```

**Common mistake:** using `SpotAllocationStrategy: lowest-price` with
`SpotInstancePools: 1`. This is the legacy strategy and picks the
single cheapest pool — it has the highest interruption rate. Use
`capacity-optimized` (recommended) or `price-capacity-optimized` for
production.

**Common mistake:** `prioritized` strategy with only one instance type
override. The strategy silently falls back to single-type behavior;
the allocation strategy is ignored. Provide >= 2 overrides for any
diversification strategy to take effect.

### Step 9 — Verification

Run every verification command and confirm each output matches the
expected state.

```bash
aws autoscaling describe-policies --auto-scaling-group-name <ASG>
aws autoscaling describe-scheduled-actions --auto-scaling-group-name <ASG>
aws autoscaling describe-warm-pool --auto-scaling-group-name <ASG>
aws autoscaling describe-instance-refreshes --auto-scaling-group-name <ASG>
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <ASG> \
  --query 'AutoScalingGroups[].{CapacityRebalance:CapacityRebalance,MIP:MixedInstancesPolicy}'
aws cloudwatch describe-alarms --alarm-name-prefix <ASG>
aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average
```

For predictive scaling, additionally verify the forecast is non-empty:

```bash
aws autoscaling describe-scaling-policies --auto-scaling-group-name <ASG> \
  --policy-names predictive-cpu-forecast \
  --query 'ScalingPolicies[].PredictiveScalingConfiguration'
```

## NEVER do these things

These anti-patterns cause oscillation, silent Spot loss, or capacity
freezes. Each is observed in real production incidents — the "why it's
wrong" line is the post-mortem finding.

1. **NEVER attach two reactive scaling policies to the SAME metric
   dimension.** Why it's wrong: target tracking on CPU and step scaling
   on CPU both emit scale activities against the same capacity
   dimension. Their alarms enter conflicting states, the ASG oscillates
   between scale-out and scale-in, and CloudWatch alarms thrash
   between ALARM and OK. Use ONE policy per metric dimension. For
   proactive + reactive, use predictive scaling + target tracking
   (different mechanisms, same metric is OK).

2. **NEVER enable predictive scaling on an ASG with < 24h of
   CloudWatch history.** Why it's wrong: predictive scaling's ML model
   needs >= 24h of `LoadMetric` datapoints to produce a forecast. On a
   fresh ASG, forecasts are empty and the policy does nothing — no
   error is surfaced. Operators read "predictive scaling enabled" as
   "scaling is happening" and capacity freezes. Verify
   `get-metric-statistics` has 24h of data before enabling.

3. **NEVER enable capacity rebalance on an On-Demand-only ASG and
   assume it provides value.** Why it's wrong: capacity rebalance
   responds to Spot Instance interruption notices. An ASG with no Spot
   capacity has no interruptions to respond to — the setting is
   accepted but no-ops silently. Verify `MixedInstancesPolicy` includes
   Spot capacity before relying on rebalance.

4. **NEVER trigger an instance refresh without checkpoints.** Why it's
   wrong: without `CheckpointPercentages`, the refresh runs to
   completion with no pause point. A bad launch template version
   rolls through all instances before you can stop. Set checkpoints at
   50% and 100% to allow a pause-and-evaluate gate.

5. **NEVER set a scheduled scaling action with `MinSize > MaxSize`
   from a prior action, and never omit `--time-zone`.** Why it's
   wrong: overlapping scheduled actions with conflicting bounds
   produce unpredictable capacity. Omitting `--time-zone` defaults to
   UTC; an operator expecting 9 AM local gets 9 AM UTC. Always specify
   `--time-zone` and verify the schedule chain's bounds are consistent.

## Output format (STRICT output contract)

When this skill is invoked with an ASG scaling provisioning request,
the agent MUST respond with the checklist defined below using the
literal all-caps labels `POLICY_SPEC:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

### Decision tree — scaling policy selection

```text
Need to scale an ASG?
├── Metric is well-defined and continuous (CPU, ALB req count, custom)?
│     └── TARGET TRACKING (recommended default)
│           ├── Predefined: ASGAverageCPUUtilization | ALBRequestCountPerTarget
│           ├── Custom: must verify Dimensions match emitted metric
│           ├── Target value: CPU % (e.g., 50) | req/target/min (e.g., 1000)
│           ├── Cooldowns: ScaleOutCooldown 60s, ScaleInCooldown 300s (defaults)
│           └── Rule: ONE target tracking policy per metric dimension
├── Need threshold-based reactive scaling on a DIFFERENT metric?
│     └── STEP SCALING
│           ├── Prerequisite: CloudWatch alarm created FIRST
│           ├── Set TreatMissingData explicitly (breaching for scale-out)
│           ├── Step adjustments: MetricIntervalLowerBound/UpperBound + ScalingAdjustment
│           └── NEVER use same metric as target tracking (dual-policy trap)
├── Need proactive scaling for predictable traffic patterns?
│     └── PREDICTIVE SCALING
│           ├── Requires >= 24h of CloudWatch history
│           ├── Mode: ForecastAndScale (not ForecastOnly)
│           └── Pairs with target tracking (different mechanism, same metric OK)
├── Need capacity at known times (business hours, off-hours)?
│     └── SCHEDULED SCALING
│           ├── Always set --time-zone (default is UTC)
│           └── Verify Min <= Desired <= Max across overlapping actions
└── Need safe template rollout or Spot reliability?
      ├── INSTANCE REFRESH: checkpoints [50,100], MinHealthyPercentage <= 90
      └── CAPACITY REBALANCE: only for Spot-backed ASGs (no-op on On-Demand-only)
```

### Output template

```text
POLICY_SPEC: <asg-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗|OPTIONAL] ASG baseline (multi-AZ, health checks, Min<=Desired<=Max)
  [✓|✗|OPTIONAL] Scaling policy type(s): one per metric dimension (no dual-policy)
  [✓|✗|OPTIONAL] Target tracking: <metric> target <value> ScaleOutCooldown <s> ScaleInCooldown <s>
  [✓|✗|OPTIONAL] Step scaling: <metric> alarm <arn> + step adjustments (different metric)
  [✓|✗|OPTIONAL] Scheduled scaling: <recurrence> <timezone> (Min/Max consistent)
  [✓|✗|OPTIONAL] Warm pool: <state> min <n> (ReuseOnScaleIn=<true|false>)
  [✓|✗|OPTIONAL] Instance refresh: <strategy> checkpoints [<pct>] MinHealthyPercentage <pct>
  [✓|✗|OPTIONAL] Advanced: capacity rebalance <on|off> | predictive <mode> | MIP <strategy>
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands — one per [✓] item>
```

### FORBIDDEN NEVER patterns (output contract)

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` without showing ALL 8
   checklist items.** Every item MUST appear with a status marker:
   `[✓]` (applied and verified), `[✗]` (not applied or misconfigured),
   or `[OPTIONAL]` (not needed for this workload). Omitting a row
   implies it was not evaluated.

2. **NEVER mark both Target tracking and Step scaling as `[✓]` without
   confirming they target DIFFERENT metrics.** Two reactive policies on
   the same metric is the dual-policy trap. If both are on the same
   metric, one MUST be `[✗]` with a warning, OR the verdict MUST be
   `PREREQUISITES_MISSING`.

3. **NEVER mark Target tracking as `[✓]` without confirming the metric
   emits live datapoints.** Custom metric target tracking with no
   datapoints silently freezes capacity. The verification MUST include
   `get-metric-statistics` citing the namespace and dimensions.

4. **NEVER mark Predictive scaling as `[✓]` without confirming
   `Mode: ForecastAndScale` and >= 24h of history.** `ForecastOnly`
   emits forecasts but does NOT provision capacity. < 24h history
   produces empty forecasts with no error.

5. **NEVER mark Capacity rebalance as `[✓]` without confirming the ASG
   has Spot capacity.** Capacity rebalance on an On-Demand-only ASG is
   a silent no-op. Verify `MixedInstancesPolicy` includes Spot.

6. **NEVER mark Instance refresh as `[✓]` without confirming
   `CheckpointPercentages` is set.** Without checkpoints, the refresh
   runs to completion with no pause point for rollback.

7. **NEVER emit `VERDICT: PREREQUISITES_MISSING` without citing the
   specific gap.** Each `[✗]` item MUST have a one-line reason citing
   what is wrong and how to fix it. A bare `[✗]` is non-compliant.

### Perfect worked example — target tracking on ALB RequestCountPerTarget

```text
POLICY_SPEC: prod-web-asg
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] ASG baseline: multi-AZ (us-east-1a, us-east-1b, us-east-1c), ELB health checks, Min=4 Desired=6 Max=20
  [✓] Scaling policy type(s): target tracking (ALBRequestCountPerTarget) — one policy, one metric dimension
  [✓] Target tracking: ALBRequestCountPerTarget target 1000.0 ScaleOutCooldown 60 ScaleInCooldown 300 (ResourceLabel: app/prod-alb/123abc/prod-web-tg)
  [OPTIONAL] Step scaling: not configured (target tracking on ALB req count is sufficient for this workload)
  [✓] Scheduled scaling: "0 9 * * Mon-Fri" America/New_York (Min=6 Max=20); "0 19 * * *" America/New_York (Min=2 Max=10)
  [✓] Warm pool: Stopped min 2 (ReuseOnScaleIn=true)
  [✓] Instance refresh: Rolling checkpoints [50,100] MinHealthyPercentage 50 InstanceWarmup 300
  [OPTIONAL] Advanced: capacity rebalance off (On-Demand-only ASG) | predictive off | MIP none
VERIFICATION_COMMANDS:
  aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names prod-web-asg
  aws autoscaling describe-policies --auto-scaling-group-names prod-web-asg --query 'ScalingPolicies[].{Name:PolicyName,Type:PolicyType,Target:TargetTrackingConfiguration.TargetValue,Metric:TargetTrackingConfiguration.PredefinedMetricSpecification.PredefinedMetricType,ResourceLabel:TargetTrackingConfiguration.PredefinedMetricSpecification.ResourceLabel,ScaleOut:TargetTrackingConfiguration.ScaleOutCooldown,ScaleIn:TargetTrackingConfiguration.ScaleInCooldown}'
  aws autoscaling describe-scheduled-actions --auto-scaling-group-name prod-web-asg
  aws autoscaling describe-warm-pool --auto-scaling-group-name prod-web-asg
  aws autoscaling describe-instance-refreshes --auto-scaling-group-name prod-web-asg
  aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:us-east-1:123456789012:targetgroup/prod-web-tg/abc123
  aws cloudwatch get-metric-statistics --namespace AWS/ApplicationELB --metric-name RequestCountPerTarget --dimensions Name=TargetGroup,Value=app/prod-alb/123abc/prod-web-tg Name=LoadBalancer,Value=app/prod-alb/123abc --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 60 --statistics Sum
```

**Key details in this example:**

- **Metric:** `ALBRequestCountPerTarget` with `ResourceLabel:
  app/prod-alb/123abc/prod-web-tg` (ties the policy to a specific ALB
  + Target Group pair).
- **Target value:** `1000.0` requests per target per minute (~16.7 RPS
  per instance). This is per-instance-per-minute, NOT aggregate RPS.
  Operators who conflate this with RPS under-provision.
- **Cooldowns:** ScaleOut 60s (fast response to traffic spikes),
  ScaleIn 300s (5-minute grace to avoid premature termination).
- **Health checks:** ELB type required for ALB-based metrics — the
  prerequisite table confirmed this before the policy was attached.
- **No dual-policy:** Step scaling is `[OPTIONAL]` — NOT configured on
  the same metric. If step scaling were needed, it would target a
  DIFFERENT metric (e.g., SQS queue depth).
- **Capacity rebalance off:** This ASG is On-Demand-only. Marking it
  `[✓]` would be a silent no-op violation.

### Worked example — PREREQUISITES_MISSING (dual-policy trap)

```text
POLICY_SPEC: prod-web-asg
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] ASG baseline: multi-AZ (3 AZs), EC2 health checks, Min=2 Desired=4 Max=10
  [✗] Scaling policy type(s): dual-policy conflict — target tracking on CPU AND step scaling on CPU; both reactive on same metric dimension
  [✓] Target tracking: ASGAverageCPUUtilization target 50.0 ScaleOutCooldown 60 ScaleInCooldown 300
  [✗] Step scaling: SAME metric (CPU) as target tracking — this is the dual-policy trap; alarms conflict, ASG oscillates. Choose a different metric or remove.
  [OPTIONAL] Scheduled scaling: not configured
  [OPTIONAL] Warm pool: not configured
  [OPTIONAL] Instance refresh: not configured
  [OPTIONAL] Advanced: capacity rebalance off | predictive off | MIP none
VERIFICATION_COMMANDS:
  aws autoscaling describe-policies --auto-scaling-group-names prod-web-asg
```

**Self-check before emit:**
- [ ] All 8 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] If Target tracking AND Step scaling are both `[✓]`, they target DIFFERENT metrics?
- [ ] If Predictive scaling is `[✓]`, `Mode: ForecastAndScale` and >= 24h history confirmed?
- [ ] If Capacity rebalance is `[✓]`, ASG has Spot capacity (MIP present)?
- [ ] If Instance refresh is `[✓]`, CheckpointPercentages is set?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

## Recent AWS features

- **Predictive scaling (ML-based forecast)**: `policy-type
  PredictiveScaling` with `MetricSpecifications`, `Mode`
  (ForecastOnly | ForecastAndScale), and `MaxCapacityBreachBehavior`
  to allow bursting above MaxSize. Requires >= 24h of `LoadMetric`
  history; verify forecast non-empty via `describe-scaling-policies`.
- **Capacity rebalance**: `--capacity-rebalance` on ASG update/create.
  Proactively launches replacement on Spot Instance interruption
  notice. No-ops silently on On-Demand-only ASGs — verify MIP presence.
- **Warm pool `InstanceReusePolicy`**: `ReuseOnScaleIn: true` returns
  terminating instances to the warm pool on scale-in events. Pair with
  `MinSize` to maintain buffer for capacity rebalance.
- **Instance refresh checkpoints**: `CheckpointPercentages` (e.g.,
  [50, 100]) with `CheckpointDelay` pause the refresh at each threshold.
  Without checkpoints, refresh runs to completion with no pause point.
- **Mixed Instances Policy allocation strategies**: `capacity-optimized`
  (recommended for Spot), `price-capacity-optimized` (cost + availability
  balance), `lowest-price` (legacy, highest interruption rate),
  `prioritized` (On-Demand fallback ordering). `capacity-optimized` with
  >= 3 overrides is the AWS-recommended production default.
- **On-Demand / Spot blend via `InstancesDistribution`**:
  `OnDemandPercentageAboveBaseCapacity` controls the On-Demand fraction
  above base; `OnDemandBaseCapacity` sets the absolute floor.
