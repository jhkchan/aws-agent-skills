---
description: Audit an Auto Scaling Group for launch-template health, ELB health-check integrity, mixed-instances policy, capacity bounds, and unhealthy-termination behavior.
nl_triggers:
  - "audit this auto scaling group"
  - "check ASG configuration"
  - "ASG health check misconfigured"
  - "launch template vs launch configuration"
  - "ELB health check no target group"
  - "spot single instance type"
  - "ASG capacity bounds"
  - "health check grace period too short"
  - "capacity rebalance spot"
  - "ASG infinite replacement loop"
  - "mixed instances policy"
  - "ASG unhealthy instances"
  - "auto scaling audit"
  - "ASG misconfigured"
routes_to: autoscaling-group-auditor
---

# /aws:audit-autoscaling-group

Activate the `autoscaling-group-auditor` skill and audit one or more Auto
Scaling Group configurations for misconfigurations and gaps.

## What it does

Reads an ASG configuration (launch template/config, capacity bounds, health
check settings, mixed-instances policy, AZs) and applies the ordered
classification logic:

1. Launch template / configuration health — legacy LC is MISCONFIGURED;
   missing IMDSv2 is CONFIG_GAP.
2. Capacity configuration — DesiredCapacity outside [MinSize, MaxSize] is
   MISCONFIGURED.
3. ELB health check integrity — ELB health check with no target group is
   MISCONFIGURED (infinite replacement loop); grace period < 60s is
   CONFIG_GAP.
4. Health check type appropriateness — EC2 checks behind an ELB is
   CONFIG_GAP.
5. Mixed-instances policy — single Spot instance type is MISCONFIGURED.
6. Capacity rebalance — Spot without CapacityRebalance is CONFIG_GAP.
7. AZ diversity — single AZ is CONFIG_GAP.
8. Scale-out headroom — MaxSize == DesiredCapacity is CONFIG_GAP.
9. Aggregation — worst finding wins (MISCONFIGURED > CONFIG_GAP > OK).

Emits a deterministic VERDICT per ASG:

```text
ASG: <name>
VERDICT: MISCONFIGURED | CONFIG_GAP | OK
REASON: <1-2 sentences citing the worst finding and step number>
FINDINGS:
  - [MISCONFIGURED] <finding description (Step N)>
  - [CONFIG_GAP] <finding description (Step N)>
REMEDIATION: <specific action per finding, or "None required" if OK>
```

## When to invoke

Paste an ASG configuration and ask any of:

- "audit this auto scaling group"
- "is my ASG misconfigured?"
- "why are my instances cycling?"
- "check ASG health check wiring"
- "is my Spot diversification sufficient?"
- "should I use a launch template instead of a launch configuration?"

A bare ASG name + any audit verb ("audit this ASG", "check ASG config") also
routes here via the orchestrator.

## Inputs

- An ASG configuration: LaunchTemplate or LaunchConfigurationName, MinSize,
  MaxSize, DesiredCapacity, AvailabilityZones, HealthCheckType,
  HealthCheckGracePeriod, TargetGroupARNs, LoadBalancerNames,
  MixedInstancesPolicy, CapacityRebalance, TerminationPolicies.
- Launch template metadata: MetadataOptions (HttpTokens for IMDSv2 check).
- For live-account audits: an ASG name to query via
  `aws autoscaling describe-auto-scaling-groups`.

## Outputs

- One VERDICT block per ASG (multiple findings aggregate to the worst
  severity).
- Enumerated FINDINGS list with per-finding severity and step citation.
- Specific remediation: attach target group, migrate to launch template, add
  instance types, enable CapacityRebalance, increase grace period.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 2 Audit specialist for Compute elasticity).
- `/aws:audit-ec2-security-groups` for security group analysis of instances
  within the ASG.
