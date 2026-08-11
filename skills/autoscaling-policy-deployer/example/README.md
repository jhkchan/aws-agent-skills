# End-to-End Example: Auto Scaling Policy Deployment (Spot-backed ASG)

A walkthrough showing how to use the `autoscaling-policy-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are configuring scaling for a Spot-backed async worker ASG that
previously lost capacity to Spot Instance interruptions. The team wants:

- Mixed Instances Policy with 3 instance type overrides (capacity-optimized)
- 30% On-Demand above a base of 1, rest Spot
- Capacity rebalance enabled (proactive Spot replacement)
- Warm pool of 2 Stopped instances with ReuseOnScaleIn
- Target tracking on CPU at 60%
- Instance refresh with checkpoints for the next template rollout

ASG: `spot-worker-asg`
Region: `us-east-1`
Account: `111111111111`
Launch template: `worker-template` v2

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-autoscaling-policy
```

Then paste the scaling requirements.

### Option B: Natural language

> Configure scaling for spot-worker-asg: capacity-optimized MIP with 3
> types, 30% On-Demand above base 1, capacity rebalance on, warm pool
> of 2 Stopped with reuse, CPU target tracking at 60%, and instance
> refresh with checkpoints at 50 and 100.

---

## Step 2 — Skill pre-flight

The skill validates prerequisites:

1. ASG exists and is multi-AZ (3 subnets in VPCZoneIdentifier)
2. Launch template `worker-template` v2 is valid
3. ELB health checks configured (required for any ALB-based metric)
4. Min=2 Desired=4 Max=10 — bounds are consistent
5. No existing scaling policy on CPU (no dual-policy conflict)
6. AWSServiceRoleForAutoScaling present

All prerequisites pass.

---

## Step 3 — Expected output

```text
POLICY_SPEC: spot-worker-asg
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] ASG baseline: multi-AZ (3 AZs), EC2 health checks, Min=2 Desired=4 Max=10
  [✓] Scaling policy type(s): target tracking (CPU) — single policy, no dual-policy
  [✓] Target tracking: ASGAverageCPUUtilization target 60.0 (alarm aws-managed)
  [OPTIONAL] Step scaling: not configured (target tracking on CPU is sufficient)
  [OPTIONAL] Scheduled scaling: not configured
  [✓] Warm pool: Stopped min 2 (ReuseOnScaleIn=true)
  [✓] Instance refresh: Rolling checkpoints [50,100] MinHealthyPercentage 50
  [✓] Advanced: capacity rebalance on | MIP capacity-optimized (3 types)
VERIFICATION_COMMANDS:
  aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names spot-worker-asg
  aws autoscaling describe-policies --auto-scaling-group-names spot-worker-asg
  aws autoscaling describe-warm-pool --auto-scaling-group-name spot-worker-asg
  aws autoscaling describe-instance-refreshes --auto-scaling-group-name spot-worker-asg
  aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names spot-worker-asg --query 'AutoScalingGroups[].{CapRebal:CapacityRebalance,MIP:MixedInstancesPolicy.InstancesDistribution.SpotAllocationStrategy}'
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=AutoScalingGroupName,Value=spot-worker-asg --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) --period 300 --statistics Average
```

---

## Step 4 — Provisioning commands

```bash
# Mixed Instances Policy (capacity-optimized with 3 types)
aws autoscaling update-auto-scaling-group \
  --auto-scaling-group-name spot-worker-asg \
  --mixed-instances-policy '{
    "LaunchTemplate": {
      "LaunchTemplateSpecification": {"LaunchTemplateName": "worker-template", "Version": "2"},
      "Overrides": [{"InstanceType": "m5.large"}, {"InstanceType": "m5a.large"}, {"InstanceType": "m4.large"}]
    },
    "InstancesDistribution": {
      "OnDemandBaseCapacity": 1,
      "OnDemandPercentageAboveBaseCapacity": 30,
      "SpotAllocationStrategy": "capacity-optimized"
    }
  }'

# Capacity rebalance
aws autoscaling update-auto-scaling-group --auto-scaling-group-name spot-worker-asg --capacity-rebalance

# Warm pool
aws autoscaling put-warm-pool \
  --auto-scaling-group-name spot-worker-asg \
  --pool-state Stopped --min-size 2 \
  --instance-reuse-policy '{"ReuseOnScaleIn": true}'

# Target tracking on CPU at 60%
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name spot-worker-asg --policy-name cpu-target-60 \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{"PredefinedMetricSpecification":{"PredefinedMetricType":"ASGAverageCPUUtilization"},"TargetValue":60.0,"ScaleOutCooldown":60,"ScaleInCooldown":300}'
```

---

## Step 5 — Post-deployment verification

```bash
# All policies attached
aws autoscaling describe-policies --auto-scaling-group-names spot-worker-asg

# Warm pool state
aws autoscaling describe-warm-pool --auto-scaling-group-name spot-worker-asg

# Capacity rebalance + MIP confirmed
aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names spot-worker-asg \
  --query 'AutoScalingGroups[].{CapRebal:CapacityRebalance,SpotStrategy:MixedInstancesPolicy.InstancesDistribution.SpotAllocationStrategy,OnDemandPct:MixedInstancesPolicy.InstancesDistribution.OnDemandPercentageAboveBaseCapacity}'

# CloudWatch datapoints for CPU (target tracking must see live data)
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 --metric-name CPUUtilization \
  --dimensions Name=AutoScalingGroupName,Value=spot-worker-asg \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Average --query 'Datapoints | length'
```

---

## Common pitfalls to verify after deployment

1. **Capacity rebalance is no-op without Spot capacity.** Verify the MIP
   is applied and the Spot allocation strategy is `capacity-optimized`
   with >= 2 instance type overrides.
2. **Warm pool `MinSize` is the buffer for both scale-out AND Spot
   replacement.** A Spot interruption drains the warm pool; if MinSize=0,
   the next scale-out falls back to cold start. Keep MinSize >= 1 on
   Spot-backed ASGs.
3. **Single reactive policy per metric.** If someone later adds a step
   scaling policy on CPU, the dual-policy trap will cause oscillation.
   Alarm on the dual-policy condition: two policies on the same ASG
   keyed on the same metric.
4. **Instance refresh requires checkpoints.** When the next template
   version ships, trigger with `CheckpointPercentages: [50, 100]` so the
   refresh pauses at 50% for evaluation before completing.
