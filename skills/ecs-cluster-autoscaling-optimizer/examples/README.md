# Example usage: ecs-cluster-autoscaling-optimizer

A walkthrough showing the skill optimizing an ECS cluster running legacy
cluster-autoscaler with spread placement on all on-demand hosts,
demonstrating the managed scaling migration, spot capacity provider
addition, binpack placement switch, and the host reduction math.

## Input (user prompt)

> Review our ECS production cluster before the Q4 FinOps review. It's
> running on all on-demand instances with the legacy cluster-autoscaler
> and CPU is low. Help me optimize the autoscaling configuration.

```text
ClusterName: ecs-prod-cluster
Launch type: EC2 (1 capacity provider: on-demand)
Capacity provider strategy: on-demand weight=1, base=0
Managed scaling: disabled (using legacy cluster-autoscaler)
Placement strategy: spread by host
Scale-in cooldown: 300 s (default)
Target tracking: ECSServiceAverageCPUUtilization = 60%

Metrics (last 30 days):
  - CPUUtilization avg: 35%, p95: 55%
  - MemoryUtilization avg: 28%, p95: 45%
  - RunningEC2Tasks avg: 40, DesiredTasks avg: 40
  - Container instances: 20 total, 8 with runningTasksCount=0 (40% empty)
  - CapacityProviderReservation: not configured (managed scaling off)

EC2 instances: m5.2xlarge, 20 instances, avg age 45 days
Services: 6 (all stateless microservices, burst-tolerant)

Workload context: stateless microservices (API, worker, scheduler).
No stateful workloads. Traffic is bursty during business hours.
Legacy cluster-autoscaler has known scale-out lag of 3-5 minutes.
```

## Skill output

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
    on-demand reduction: 8 hosts × 730 h × $0.384/h = $2,242.56
    spot hosts added: 2 spot × 730 h × $0.115/h = $167.84 (spot for burst)
    net: 8 on-demand removed - 2 spot added = $2,074.72 net saved
    (conservatively $2,120.00 with rounding for partial utilization)
  Assumptions: m5.2xlarge at $0.384/h on-demand, $0.115/h spot (us-east-1),
    target utilization 60% CPU, 70% spot discount.
MIGRATION_STEPS:
  1. Create spot capacity provider:
     aws ecs create-capacity-provider --name spot-cp \
       --auto-scaling-group-provider autoScalingGroupArn=<spot-asg-arn>,managedScaling.status=ENABLED,managedScaling.targetCapacity=100
  2. Update service with new strategy + binpack:
     aws ecs update-service --cluster ecs-prod-cluster --service api-service \
       --capacity-provider-strategy capacityProvider=on-demand-cp,weight=1,base=2 capacityProvider=spot-cp,weight=4,base=0 \
       --placement-strategy type=binpack,field=memory type=spread,field=attribute:ecs.availability-zone
  3. Enable managed scaling on the on-demand CP:
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

## What the skill caught that a generic assistant misses

1. **Managed scaling + spot + binpack is a three-part paired
   recommendation.** A generic assistant says "enable managed scaling."
   The skill identifies that managed scaling alone leaves value on the
   table — spot captures the 70% discount, and binpack eliminates the
   40% empty hosts. All three stack together.

2. **Spot base + on-demand weight is the cost-optimal hybrid.** The
   skill recommends `on-demand base=2, spot weight=4` — the pattern that
   guarantees availability (base floor) while maximizing spot savings
   (weight ratio). A generic assistant says "use spot" without the base+
   weight strategy.

3. **Binpack placement is paired with AZ spread.** The skill never
   recommends pure binpack — always `binpack by memory + spread by az`
   to maintain availability. A generic assistant switches to binpack
   without the AZ spread, risking all tasks on one AZ.

4. **Host reduction is quantified with spot cost offset.** The skill
   calculates the savings from removing 8 on-demand hosts AND the cost
   of adding 2 spot hosts for burst. A generic assistant says "this
   will save money" without showing the math.

5. **Scale-in cooldown is tuned for the traffic pattern.** The skill
   identifies the workload as spiky (CV > 0.5) and recommends 120 s
   cooldown instead of the 300 s default. A generic assistant leaves
   the default, leaving hosts alive 5 minutes after a burst ends.

6. **Legacy cluster-autoscaler conflict is flagged.** The skill warns to
   disable the legacy autoscaler before enabling managed scaling to
   avoid race conditions. A generic assistant doesn't know about the
   conflict.

## Slash-command invocation

```
/aws:optimize-ecs-autoscaling
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our ECS cluster autoscaling for the Q4 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: ecs-cluster-autoscaling-optimizer]`
and hands off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new configuration:

```bash
# Confirm managed scaling + capacity providers landed
aws ecs describe-capacity-providers --cluster ecs-prod-cluster \
  --query 'capacityProviders[].{name:name,managedScaling:autoScalingGroupProvider.managedScaling.status,target:autoScalingGroupProvider.managedScaling.targetCapacity}' \
  --output table

# Monitor host count for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/ECS \
  --metric-name ContainerInstanceCount \
  --dimensions Name=ClusterName,Value=ecs-prod-cluster \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

# Monitor CapacityProviderReservation (should stabilize near 95-100%)
aws cloudwatch get-metric-statistics --namespace AWS/ECS \
  --metric-name CapacityProviderReservation \
  --dimensions Name=ClusterName,Value=ecs-prod-cluster Name=CapacityProviderName,Value=spot-cp \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

# Check for empty container instances (should be 0)
aws ecs describe-container-instances \
  --cluster ecs-prod-cluster \
  --container-instances $(aws ecs list-container-instances --cluster ecs-prod-cluster --output text --query 'containerInstanceArns') \
  --query 'containerInstances[?runningTasksCount==`0`].ec2InstanceId' \
  --output text
```

If host count drops to 12, CapacityProviderReservation stabilizes above
90%, and empty instances are 0, the optimization is confirmed.

## Fleet-wide extension

For a fleet of N ECS clusters:

1. Pull all clusters with `aws ecs describe-clusters`.
2. Filter to clusters with `registeredContainerInstancesCount > 0` (EC2
   clusters, not Fargate-only).
3. Pull capacity providers and container instances for each.
4. For each cluster with managed scaling DISABLED: flag for migration.
5. For each cluster with all on-demand CP: flag for spot evaluation.
6. For each cluster with spread-by-host placement: flag for binpack.
7. Sort by estimated monthly savings (largest first).
8. Slice into batches of 3 clusters.
9. For each batch: emit per-cluster MIGRATION_STEPS, then a single
   CONFIRM for the batch.
10. Verify each batch before proceeding to the next.
