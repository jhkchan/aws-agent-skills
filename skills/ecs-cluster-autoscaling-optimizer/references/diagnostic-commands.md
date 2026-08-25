# Diagnostic Commands (load on demand) — ECS Cluster Autoscaling Optimizer

Data-source listings, per-step detection and tuning CLI, and pre-flight safety checks moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight data gate — required data sources (moved from SKILL.md)

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

## Step 1 — strategy prose, parameters JSON (moved from SKILL.md)

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

## Step 1 — create spot capacity provider CLI (moved from SKILL.md)

**Create a spot capacity provider:**
```bash
aws ecs create-capacity-provider \
  --name spot-cp \
  --auto-scaling-group-provider autoScalingGroupArn=<asg-arn>,managed-scaling.status=ENABLED,managed-scaling.target-capacity=100
```

## Step 2 — migration prose and detection CLI (moved from SKILL.md)

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

## Step 2 — enable managed scaling CLI (moved from SKILL.md)

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

## Step 4 — cooldown tuning CLI (moved from SKILL.md)

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

## Step 5 — empty host detection, ratio math, resolution (moved from SKILL.md)

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

## Step 7 — warm-up tuning CLI (moved from SKILL.md)

**Tune warm-up:**
```bash
aws ecs update-capacity-provider \
  --name <cp-name> \
  --auto-scaling-group-provider managedScaling.status=ENABLED,instanceWarmupPeriod=60
```

## Step 8 — drain monitoring CLI and resolution (moved from SKILL.md)

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

## Step 9 — desired vs running gap detection CLI (moved from SKILL.md)

**Detection:**
```bash
aws ecs describe-services \
  --cluster <cluster> \
  --services <service-name> \
  --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}' \
  --output json
```

## Step 10 — switch to binpack CLI (moved from SKILL.md)

**Switch to binpack:**
```bash
aws ecs update-service \
  --cluster <cluster> \
  --service <service> \
  --placement-strategy type=binpack,field=memory type=spread,field=attribute:ecs.availability-zone
```

This strategy: binpack by memory first, then spread across AZs for
availability.

## Step 11 — scheduled scaling CLI (moved from SKILL.md)

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

## Pre-flight safety checks (moved from SKILL.md)

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
