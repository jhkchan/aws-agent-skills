---
name: autoscaling-group-auditor
description: Audits AWS Auto Scaling Groups for launch-template health (legacy launch configuration, IMDSv2), ELB health-check integrity (missing target group, grace-period timing), mixed-instances policy (single Spot instance type, allocation strategy), capacity bounds (desired vs min/max), and unhealthy termination behavior (EC2-only checks behind an ELB, capacity rebalance). Emits a deterministic verdict (MISCONFIGURED | CONFIG_GAP | OK) per ASG with enumerated findings and specific remediation. Use when reviewing ASG configurations, checking launch-template wiring, validating ELB health checks, auditing Spot diversification, or hardening capacity posture.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). No AWS CLI required for offline ASG-config classification. Live-account audits use aws autoscaling describe-auto-scaling-groups, aws ec2 describe-launch-templates, and aws elbv2 describe-target-groups (AWS CLI v2, SSO or key-based credentials).
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  verdict_shape: MISCONFIGURED | CONFIG_GAP | OK
  when_to_use: Reviewing an ASG configuration before production deployment, checking launch-template or launch-configuration wiring, validating ELB health checks and grace-period timing, auditing Spot instance diversification, verifying capacity bounds, or investigating unhealthy-instance replacement loops.
  activation_triggers: audit this auto scaling group, check ASG health check, is my ASG misconfigured, launch template vs launch configuration, ELB health check no target group, spot single instance type, ASG capacity bounds, health check grace period too short, capacity rebalance spot, ASG infinite replacement loop
  invocation_schema: 'Input: either (a) an ASG configuration (launch template/config, capacity bounds, health check settings, mixed-instances policy, AZs), optionally paired with launch-template metadata, OR (b) an ASG name/ARN for live-account audit. Output: deterministic ASG/VERDICT/REASON/FINDINGS/ REMEDIATION block per group, where VERDICT is MISCONFIGURED, CONFIG_GAP, OK, or ERROR.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Auto Scaling, ASG, launch template, launch configuration, ELB health check, target group, mixed instances, Spot, capacity, unhealthy termination, IMDSv2, CapacityRebalance, HealthCheckGracePeriod, SpotAllocationStrategy, OnDemandPercentageAboveBaseCapacity, TerminationPolicies, AvailabilityZones, fleet split, ASG audit, auto scaling remediation
  tags: autoscaling, compute, launch-template, elb-health, spot, capacity, mixed-instances, audit
---

# Auto Scaling Group Auditor

## Mindset

**One-line takeaway:** the verdict is always the **worst** finding across all
dimensions, and three ASG misconfigurations are silent killers —
HealthCheckType=ELB with no target group (infinite replacement loop),
launch-configuration usage (locked out of IMDSv2 and mixed-instances), and a
single Spot instance type (one interruption takes down everything).

An Auto Scaling Group is the elasticity engine of EC2 workloads. Its
configuration sits at the intersection of launch infrastructure (templates,
AMIs, IMDSv2), health detection (ELB vs EC2 checks, grace periods), capacity
planning (min/max/desired bounds, Spot diversification), and failure recovery
(termination policies, capacity rebalance). A misconfiguration in any
dimension produces silent degradation — the ASG keeps running but instances
cycle, apps hang undetected, or Spot interruptions cascade.

- **ELB health check with no target group** is a **silent infinite loop**: the
  ASG launches, the ELB never reports health, the ASG terminates and relaunches
  — indefinitely. It looks like "high churn," not an obvious error.
- **Launch configuration** is a **technical-debt dead end**: deprecated for new
  creation (Dec 2023), incompatible with MixedInstancesPolicy, and cannot
  enforce IMDSv2.
- **Single Spot instance type** is a **total-outage vector**: one Spot
  interruption event affects 100% of Spot capacity.

## Quick reference — verdict thresholds

| Condition | Verdict | Rule |
|---|---|---|
| `HealthCheckType` includes ELB + no target group / LB attached | **MISCONFIGURED** | Step 3 |
| `LaunchConfigurationName` set (legacy LC) | **MISCONFIGURED** | Step 1 |
| `DesiredCapacity > MaxSize` or `< MinSize` | **MISCONFIGURED** | Step 2 |
| MIP with 1 instance type + Spot allocation (< 100% On-Demand) | **MISCONFIGURED** | Step 5 |
| Launch template `HttpTokens != required` | **CONFIG_GAP** | Step 1 |
| `HealthCheckGracePeriod < 60` + ELB health check | **CONFIG_GAP** | Step 3 |
| `HealthCheckType: EC2` + target group / LB attached | **CONFIG_GAP** | Step 4 |
| Spot allocation + `CapacityRebalance.Enabled != true` | **CONFIG_GAP** | Step 6 |
| Single AZ only (`AvailabilityZones` has 1 entry) | **CONFIG_GAP** | Step 7 |
| `MaxSize == DesiredCapacity` (no scale-out headroom) | **CONFIG_GAP** | Step 8 |
| All dimensions pass | **OK** | Step 9 |

See the ordered steps below for edge cases. Deep ASG lifecycle internals
(health-check evaluation pipeline, Spot rebalance timing, AZ rebalancing) are
in the [Deep reference](#deep-reference-auto-scaling-internals) section.

## Pre-flight: ASG metadata gate (run before classification)

Before evaluating the ASG configuration, classify the ASG's lifecycle state
and launch source. Several attributes short-circuit the audit —
misclassifying them produces false positives.

| Attribute | Value | Effect on audit |
|---|---|---|
| `LaunchConfigurationName` | set | **Legacy launch configuration.** Immediately MISCONFIGURED (Step 1). LCs are deprecated (no new creation since Dec 2023), cannot enforce IMDSv2, and are incompatible with MixedInstancesPolicy. |
| `LaunchTemplate` | set | Proceed with full audit. This is the modern path. |
| `MixedInstancesPolicy` | set | The ASG uses MIP — evaluate instance-type diversification (Step 5). MIP overrides the top-level `LaunchTemplate`. |
| `SuspendedProcesses` | includes `HealthCheck` | **Suspended health checks.** The ASG will not replace unhealthy instances. Flag as operational risk — but classify the rest of the config normally. |
| `SuspendedProcesses` | includes `Launch` / `Terminate` | **Scaling is frozen.** The ASG cannot launch or terminate. Flag as operational risk. |

**If the ASG configuration is malformed** (missing required fields like
`MinSize`, `MaxSize`, `HealthCheckType`), output:

```text
ASG: <name>
VERDICT: ERROR
REASON: ASG configuration is missing required fields — cannot classify.
REMEDIATION: Retrieve the canonical config with
  aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <name> --output json
  and re-audit.
```

## Process — Classification logic (apply in order, aggregate worst)

### Step 0: Expert knowledge — non-obvious ASG behaviors that change classification

Deep dive moved to [references/advanced-patterns.md](references/advanced-patterns.md)
(Step 0: non-obvious ASG behaviors) — load before classifying edge-case ASGs.

### Step 1: Launch template / configuration health

Evaluate the launch source:

- **MISCONFIGURED** if `LaunchConfigurationName` is set. Launch configurations
  are deprecated (no new creation since Dec 2023), cannot enforce IMDSv2, and
  are incompatible with MixedInstancesPolicy. This is a tech-debt dead end.

- **CONFIG_GAP** if `LaunchTemplate` is set but `MetadataOptions.HttpTokens`
  is not `"required"`. IMDSv2 is not enforced — the instance metadata service
  is accessible via IMDSv1, which is vulnerable to SSRF attacks. An attacker
  who can make the instance call `169.254.169.254` can steal IAM instance
  profile credentials.

- **OK** for this dimension if `LaunchTemplate` is set with
  `HttpTokens: "required"`.

### Step 2: Capacity configuration

Evaluate the min/max/desired bounds:

- **MISCONFIGURED** if `DesiredCapacity > MaxSize` or
  `DesiredCapacity < MinSize`. The ASG will immediately launch or terminate
  instances to reach desired, but the desired value is logically inconsistent
  with the bounds. `describe-auto-scaling-groups` may show the desired value
  the user set, but the ASG corrects it silently — relying on silent
  correction is a production hazard.

- **CONFIG_GAP** if `MinSize` is 0 for a production ASG. With MinSize=0, the
  ASG can scale to zero — the first scale-out has a cold start (AMI fetch +
  userdata + ELB registration: 3-5 minutes). For production workloads,
  MinSize >= 2 (one per AZ minimum) maintains baseline capacity.

### Step 3: ELB health check integrity

Evaluate the ELB health check wiring:

- **MISCONFIGURED** if `HealthCheckType` includes `"ELB"` AND both
  `TargetGroupARNs` and `LoadBalancerNames` are empty or missing. No ELB is
  attached to report health — instances are treated as Unhealthy from launch,
  creating an infinite replacement loop. This is the most costly silent
  misconfiguration in Auto Scaling.

- **CONFIG_GAP** if `HealthCheckType` includes `"ELB"` AND
  `HealthCheckGracePeriod < 60`. ELB target registration alone takes 30-60
  seconds. A grace period under 60 seconds gives the application near-zero
  time to boot and register before being evaluated — healthy instances get
  terminated prematurely.

### Step 4: Health check type appropriateness

Evaluate whether the health check type matches the traffic architecture:

- **CONFIG_GAP** if `HealthCheckType` is `"EC2"` (or does not include ELB) AND
  (`TargetGroupARNs` is non-empty OR `LoadBalancerNames` is non-empty). An ELB
  is attached but the ASG only checks EC2 status checks — a hung application
  (process alive but not serving) is not detected. Use `HealthCheckType: ELB`
  or `"ELB,EC2"` for ASGs that front traffic via a load balancer.

### Step 5: Mixed-instances policy evaluation

Evaluate Spot diversification and allocation:

- **MISCONFIGURED** if `MixedInstancesPolicy` exists AND the `Overrides` list
  has exactly 1 instance type AND Spot allocation is in use
  (`OnDemandPercentageAboveBaseCapacity < 100`). A single Spot instance type
  means the next Spot interruption affects 100% of Spot capacity. Diversify
  across 3+ instance types to survive pool-level interruptions.

- **CONFIG_GAP** if no `MixedInstancesPolicy` exists AND the ASG uses a
  `LaunchTemplate` (not LC). MIP provides instance-type flexibility, Spot
  cost optimization, and AZ-aware allocation — all unavailable with a bare
  launch template. This is a recommended-practice gap, not an active failure.

### Step 6: Capacity rebalance (Spot)

- **CONFIG_GAP** if Spot allocation is in use
  (`OnDemandPercentageAboveBaseCapacity < 100` within a `MixedInstancesPolicy`)
  AND `CapacityRebalance.Enabled` is not `true`. Without Capacity Rebalance,
  the ASG only reacts after a Spot instance is terminated — it does not
  proactively launch a replacement on the rebalance recommendation. This
  creates a capacity gap during the replacement window.

### Step 7: AZ diversity

- **CONFIG_GAP** if `AvailabilityZones` has exactly 1 entry (or
  `VPCZoneIdentifier` references subnets in a single AZ). A single-AZ ASG has
  no resilience — an AZ outage takes down the entire fleet. Minimum 2 AZs for
  production; 3+ for high availability.

### Step 8: Scale-out headroom

- **CONFIG_GAP** if `MaxSize == DesiredCapacity`. The ASG can only scale in,
  never out. If traffic spikes, there is zero elasticity. This may be
  intentional for fixed-size groups, but for auto-scaling workloads it defeats
  the purpose. Ensure `MaxSize > DesiredCapacity` for a meaningful scale-out
  margin.

### Step 9: Aggregation — worst finding wins

The final verdict is the **maximum severity** across all findings, where
MISCONFIGURED > CONFIG_GAP > OK:

```text
verdict = max(all_finding_severities)
```

If no findings (all dimensions pass), the verdict is **OK**.

## Output format (per ASG)

```text
ASG: <name>
VERDICT: MISCONFIGURED | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and its step number>
FINDINGS:
  - [MISCONFIGURED] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
  - [OK] <dimension that passed>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

### Worked example — Spot single instance type

```text
ASG: prod-spot-asg
VERDICT: MISCONFIGURED
REASON: MixedInstancesPolicy has 1 instance type (c5.large) with Spot
allocation (OnDemandPercentageAboveBaseCapacity=0) — a single Spot interruption
affects 100% of capacity (Step 5). CapacityRebalance is also disabled,
compounding the risk.
FINDINGS:
  - [MISCONFIGURED] Single Spot instance type (c5.large) with 0% On-Demand —
    no diversification against pool-level interruption (Step 5)
  - [CONFIG_GAP] CapacityRebalance.Enabled is false on a Spot-backed ASG —
    no proactive replacement on rebalance recommendation (Step 6)
  - [OK] Launch template with IMDSv2 required (Step 1)
REMEDIATION:
  1. Add 2+ instance types to Overrides (e.g., c5.large, c5a.large, m5.large)
     to diversify Spot pools.
  2. Set SpotAllocationStrategy to capacity-optimized to minimize
     interruptions.
  3. Enable CapacityRebalance:
     aws autoscaling create-or-update-tags --tags
       Key=capacity-rebalance,Value=true,...
     (or update via create-auto-scaling-group / update-auto-scaling-group
     with --capacity-rebalance)
```

## Anti-Patterns — NEVER

- NEVER classify `HealthCheckType: ELB` with no target group as anything other
  than MISCONFIGURED. Without an attached ELB, no health data is returned —
  every instance is Unhealthy from launch, creating an infinite replacement
  loop. This is not "suboptimal" — it is actively burning compute budget.

- NEVER treat a launch configuration as equivalent to a launch template. LCs
  are deprecated, cannot enforce IMDSv2, and are incompatible with
  MixedInstancesPolicy. Any ASG using `LaunchConfigurationName` is locked out
  of modern EC2 features.

- NEVER assume `HealthCheckGracePeriod` is measured from ELB registration. It
  is measured from instance **launch**. ELB registration takes 30-60s — a
  60s grace period gives the app near-zero warmup time. Treat < 60s with ELB
  checks as a CONFIG_GAP.

- NEVER classify a single Spot instance type in a MixedInstancesPolicy as
  CONFIG_GAP. With Spot allocation (`OnDemandPercentageAboveBaseCapacity <
  100`), a single instance type means one interruption event affects 100% of
  capacity. This is MISCONFIGURED — the ASG will lose all Spot capacity on
  the next pool drain.

- NEVER assume `HealthCheckType: EC2` detects application failure. EC2 status
  checks verify hypervisor-level health only. A hung application (process
  alive, port open, not serving requests) passes EC2 checks. If the ASG has
  a target group attached, the health check type should include ELB.

- NEVER treat `OnDemandPercentageAboveBaseCapacity` as the total On-Demand
  percentage. It applies **above** `OnDemandBaseCapacity`. Base=2, Percent=50
  means the first 2 instances are On-Demand, then 50% of the remainder. The
  effective On-Demand ratio depends on DesiredCapacity.

- NEVER set `SpotAllocationStrategy: capacity-optimized` and also set
  `SpotInstancePools`. `SpotInstancePools` only applies to `lowest-price`.
  With `capacity-optimized`, `SpotInstancePools` is dead configuration — it
  has no effect. Do not rely on it for diversification.

- NEVER assume `$Latest` launch template version is safe for production. When
  the template is updated, `$Latest` immediately redirects. New instances use
  the new version while old instances keep theirs — fleet split. If the new
  version is broken, new instances fail and cycle infinitely. Pin a specific
  version number for production ASGs.

- NEVER assume an ASG with `MaxSize == DesiredCapacity` can scale. It can only
  scale in. For auto-scaling workloads, ensure `MaxSize > DesiredCapacity`.
  This is CONFIG_GAP, not MISCONFIGURED — the ASG works, it just has no
  scale-out elasticity.

- NEVER assume Standby instances free up capacity. Standby instances count
  against `MaxSize` but not `DesiredCapacity`. If MaxSize is tight, Standby
  instances block scale-out. Check Standby count before scaling operations.

- NEVER modify an ASG's launch template without considering the instance
  refresh. Changing `$Latest` or pinning a new version does not automatically
  update existing instances — they keep their old version until replaced. Use
  `aws autoscaling start-instance-refresh` to roll out the change safely.

- NEVER ignore `SuspendedProcesses`. An ASG with `HealthCheck` suspended will
  not replace unhealthy instances. An ASG with `Launch` or `Terminate`
  suspended cannot scale at all. Always check suspended processes before
  classifying capacity or health behavior.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (UpdateAutoScalingGroup, StartInstanceRefresh, PutScalingPolicy,
  DetachLoadBalancerTargetGroups), the auditor MUST emit:
  `CONFIRM: About to <action> on ASG <name> in account <account>. This
  affects <consequence>. Proceed? (yes/no)`

- **Snapshot the current ASG config for rollback:**
  `aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names <name> --output json > /tmp/<name>-backup-$(date +%s).json`
  BEFORE any modification. ASG configs are not versioned — there is no undo
  without a backup.

- **Instance refresh safety.** Before starting an instance refresh to roll out
  a new launch template version, verify: (1) `MinHealthyPercentage` is set
  (default 90 — too high for small ASGs); (2) the new template version has
  been tested on a canary instance or non-prod ASG; (3) the ASG's health
  check grace period is long enough for the new AMI/userdata to complete
  boot. A failed instance refresh can take down the entire fleet.

- **Capacity bounds check.** Before changing MinSize/MaxSize/DesiredCapacity,
  verify the new values are internally consistent (MinSize <= DesiredCapacity
  <= MaxSize) and that the account has sufficient On-Demand or Spot capacity
  in the target AZs. Use
  `aws service-quotas get-service-quota --service-code autoscaling --quota-code L-...`
  to check ASG resource limits.

- **Spot allocation warning.** Before increasing Spot percentage or adding
  instance types, check
  `aws ec2 describe-spot-price-history` for recent price stability in the
  target AZs. A pool that was stable yesterday may be under pressure today.

## Remediation guidance

### For MISCONFIGURED — ELB health check with no target group (Step 3)

1. Attach the target group:
   `aws autoscaling attach-load-balancer-target-groups --auto-scaling-group-name <name> --target-group-arns <arn>`
2. Verify the target group has a configured health check:
   `aws elbv2 describe-target-groups --target-group-arns <arn>`
   The health check path, interval, and healthy threshold must match the
   application's boot time.
3. If the ASG should NOT use ELB health checks (e.g., background workers),
   switch: `aws autoscaling update-auto-scaling-group --auto-scaling-group-name <name> --health-check-type EC2`

### For MISCONFIGURED — legacy launch configuration (Step 1)

1. Create a launch template from the launch configuration:
   `aws ec2 create-launch-template --launch-template-name <name> --launch-template-data file://template.json`
2. Update the ASG to use the template:
   `aws autoscaling update-auto-scaling-group --auto-scaling-group-name <name> --launch-template LaunchTemplateId=<id>,Version=1`
3. Start an instance refresh to roll existing instances to the new template:
   `aws autoscaling start-instance-refresh --auto-scaling-group-name <name>`

### For MISCONFIGURED — single Spot instance type (Step 5)

1. Add 2+ instance types to the MIP Overrides. Choose types with similar
   vCPU/memory (e.g., c5.large, c5a.large, m5.large).
2. Set `SpotAllocationStrategy: capacity-optimized` to minimize interruptions.
3. Enable CapacityRebalance:
   `aws autoscaling update-auto-scaling-group --auto-scaling-group-name <name> --capacity-rebalance`

### For CONFIG_GAP — IMDSv2 not required (Step 1)

1. Update the launch template with a new version enforcing IMDSv2:
   `aws ec2 create-launch-template-version --launch-template-id <id> --launch-template-data '{"MetadataOptions":{"HttpTokens":"required"}}'`
2. Update the ASG to use the new version:
   `aws autoscaling update-auto-scaling-group --auto-scaling-group-name <name> --launch-template LaunchTemplateId=<id>,Version=<n>`
3. Start an instance refresh to enforce on existing instances.

### For CONFIG_GAP — short grace period (Step 3)

1. Increase `HealthCheckGracePeriod` to at least 300 seconds:
   `aws autoscaling update-auto-scaling-group --auto-scaling-group-name <name> --health-check-grace-period 300`

### For CONFIG_GAP — EC2 health check behind ELB (Step 4)

1. Switch to ELB health checks:
   `aws autoscaling update-auto-scaling-group --auto-scaling-group-name <name> --health-check-type ELB`
2. Verify the target group health check is configured correctly (path, port,
   interval, healthy threshold).

### For OK

1. No remediation required for the current posture.
2. Recommend enabling Instance Refresh warmup checks if not already configured.
3. Recommend setting `NewInstancesProtectedFromScaleIn: true` for stateful
   workloads to prevent scale-in from terminating new instances before they
   receive traffic.

## Deep reference: Auto Scaling internals

Internals moved to [references/advanced-patterns.md](references/advanced-patterns.md)
(health-check lifecycle, Spot rebalance timing, OnDemand/Spot math, AZ rebalancing) — load on demand.

## Recent AWS features (2024-2026)

Feature notes moved to [references/advanced-patterns.md](references/advanced-patterns.md).
Load when deciding whether a recent feature changes the audit.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 expert deep dive, Auto Scaling internals (health-check lifecycle, Spot rebalancing, capacity math, AZ rebalancing), recent AWS features

## Domain

AWS CloudOps / Compute Elasticity & Auto Scaling Health.

## AWS documentation

- **Amazon EC2 Auto Scaling User Guide** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/what-is-amazon-ec2-auto-scaling.html
- **Auto Scaling API Reference** — https://docs.aws.amazon.com/autoscaling/ec2/APIReference/
- **Auto Scaling Security** — https://docs.aws.amazon.com/autoscaling/ec2/userguide/security.html
- **Auto Scaling CLI Reference** — https://docs.aws.amazon.com/cli/latest/reference/autoscaling/
- **Blog: Instance maintenance policies** — https://aws.amazon.com/blogs/compute/proactively-manage-instance-maintenance-with-amazon-ec2-auto-scaling-instance-maintenance-policy/
