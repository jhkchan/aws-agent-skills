---
name: autoscaling-policy-deployer
description: 'Provisions Amazon EC2 Auto Scaling policies and surrounding primitives with production defaults: target tracking (CPUUtilization, ALBRequestCountPerTarget, custom metrics), step scaling (CloudWatch alarm → step adjustments), scheduled scaling, warm pools, instance refresh, capacity rebalance, predictive scaling (ML-based forecast), and Mixed Instances Policy (On-Demand + Spot blend). Emits READY_TO_DEPLOY / PREREQUISITES_MISSING with every item verified and copy-pasteable autoscaling / cloudwatch commands. Use when attaching a scaling policy, configuring scheduled actions, enabling warm pool or capacity rebalance, triggering an instance refresh, or blending On-Demand with Spot. Triggers: Auto Scaling policy, target tracking, step scaling, scheduled action, warm pool, instance refresh, capacity rebalance, predictive scaling, Mixed Instances Policy.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Live provisioning uses AWS CLI v2 with autoscaling (put-scaling-policy, put-scheduled-update-group-action, put-warm-pool, start-instance-refresh, update-auto-scaling-group, create-auto-scaling-group), cloudwatch (put-metric-alarm), ec2 (describe-launch-templates, describe-instance-types), and cloudformation / terraform aws_autoscaling_* equivalents.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  when_to_use: Attaching a scaling policy (target tracking, step, predictive) to an existing Auto Scaling Group, configuring recurring scheduled scaling actions, enabling a warm pool for fast scale-out, triggering or scheduling an instance refresh for rolling template updates, enabling capacity rebalance for Spot-backed ASGs, defining a Mixed Instances Policy with On-Demand + Spot blend and allocation strategy, or generating IaC (CloudFormation / Terraform) for any of the above. Do NOT invoke for ECS Service Auto Scaling (use ecs-fargate-deployer), for DynamoDB capacity (use dynamodb-table-deployer), or for ASG audit posture (use autoscaling-group-auditor).
  activation_triggers: Auto Scaling policy, target tracking scaling, step scaling policy, scheduled scaling action, warm pool, instance refresh, capacity rebalance, predictive scaling, Mixed Instances Policy, Spot Instance diversification, ASG scaling plan
  invocation_schema: 'Input: an Auto Scaling Group name + one or more scaling configurations (target tracking metric+target, step scaling alarm+adjustments, scheduled action recurrence, warm pool spec, instance refresh trigger, capacity rebalance enablement, predictive scaling forecast, Mixed Instances Policy spec). Output: deterministic POLICY_SPEC / VERDICT / CHECKLIST / VERIFICATION_COMMANDS block per the STRICT output contract, where VERDICT is READY_TO_DEPLOY or PREREQUISITES_MISSING.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: aws, ec2, autoscaling, auto-scaling-group, target-tracking, step-scaling, scheduled-scaling, warm-pool, instance-refresh, capacity-rebalance, predictive-scaling, mixed-instances-policy, spot-instances, cloudops, deploy
  tags: aws, autoscaling, ec2, scaling-policy, spot-instances, warm-pool, instance-refresh, deploy, compute
  dependencies: aws-orchestrator
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

Full reasoning-framework deep dive (the four traps with complete explanations) moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when diagnosing why a policy oscillates or silently no-ops.

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

Full heuristic moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it before attaching more than one policy to the same ASG.

## Expert heuristic: predictive scaling's history requirement

Full heuristic moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when predictive forecasts come back empty.

## Expert heuristic: warm pool drain race and capacity rebalance

Full heuristic moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when pairing warm pools with Spot interruptions or instance refresh.

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

CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

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

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

### Step 3 — Configure target tracking

CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

### Step 4 — Configure step scaling (different metric only)

Step scaling requires a CloudWatch alarm FIRST, then the policy:

CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

### Step 5 — Configure scheduled scaling

CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

### Step 6 — Configure warm pool

CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

### Step 7 — Trigger instance refresh

CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

### Step 8 — Configure advanced features

#### 8a. Capacity rebalance (Spot-backed ASGs)

CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

Capacity rebalance proactively launches a replacement when a Spot
Instance interruption notice is received, then terminates the
interrupted instance after the replacement passes health checks. Pair
with `Mixed Instances Policy` (8c) for diversification.

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

#### 8b. Predictive scaling

CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

#### 8c. Mixed Instances Policy

CLI moved to [references/provisioning-cli-commands.md](references/provisioning-cli-commands.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

Common-mistake detail moved to [references/error-handling.md](references/error-handling.md).

### Step 9 — Verification

Run every verification command and confirm each output matches the
expected state.


Full verification command listing moved to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load it at Step 9 to verify every configuration item against actual state.

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

Full example moved to [references/worked-examples.md](references/worked-examples.md).
Load it when the verdict is PREREQUISITES_MISSING.

**Self-check before emit:**
- [ ] All 8 checklist rows present (no omitted items)?
- [ ] Every `[✓]` has a matching verification command?
- [ ] If Target tracking AND Step scaling are both `[✓]`, they target DIFFERENT metrics?
- [ ] If Predictive scaling is `[✓]`, `Mode: ForecastAndScale` and >= 24h history confirmed?
- [ ] If Capacity rebalance is `[✓]`, ASG has Spot capacity (MIP present)?
- [ ] If Instance refresh is `[✓]`, CheckpointPercentages is set?
- [ ] Every `[✗]` cites the specific gap and what the operator must provide?

## Recent AWS features

Feature detail moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load it when choosing a Spot allocation strategy or enabling predictive scaling.

## References (load on demand)

- [Provisioning CLI commands](references/provisioning-cli-commands.md) — per-step CLI for the 9-step procedure (baseline, target tracking, step scaling, scheduled, warm pool, instance refresh, advanced features)
- [Scaling policy templates](references/scaling-policy-templates.md) — full per-policy-type CLI/JSON templates
- [Worked examples](references/worked-examples.md) — PREREQUISITES_MISSING worked example (dual-policy trap)
- [Error handling](references/error-handling.md) — common-mistake catalog for Steps 1-8 (Dimensions mismatch, timezone, ForecastOnly, lowest-price, and more)
- [Diagnostic commands](references/diagnostic-commands.md) — Step 9 post-deploy verification command listing
- [Advanced patterns](references/advanced-patterns.md) — reasoning-framework deep dive, expert heuristics (dual-policy trap, predictive history, warm-pool drain race), recent AWS features

