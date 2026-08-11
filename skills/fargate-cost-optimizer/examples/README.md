# End-to-end usage scenario: fargate-cost-optimizer

A walkthrough showing the skill optimizing an over-provisioned Fargate
task with Spot and ARM64 stacking. This exercises Step 2 (RIGHT_SIZE),
Step 3 (SPOT), Step 4 (ARM64), and the estimated savings calculation.

## Input (user prompt)

> My `order-processor:42` ECS service on Fargate has 10 tasks running
> 24/7. Task definition: 2 vCPU / 4 GB, x86_64, Java 21. CloudWatch
> shows CPUUtilization avg 18%, max 35%; MemoryUtilization avg 42%,
> max 55%. No Spot, no Savings Plans. Cost Explorer shows $636/month.

## Skill output

```text
TARGET: order-processor:42 (service order-processor on cluster prod)
VERDICT: OPPORTUNITY_FOUND
REASON: Task is over-provisioned (CPU avg 18%, max 35% on 2 vCPU / 4
GB); workload is stateless behind ALB (Spot eligible); Java 21 runtime
is ARM64 compatible.
RECOMMENDATION:
  1. RIGHT_SIZE: drop from 2 vCPU / 4 GB to 1 vCPU / 2 GB (CPU avg 18%
     on 2 vCPU = 0.36 vCPU actual; 1 vCPU at ~36% avg, ~70% max — safe)
  2. SPOT: add capacity provider strategy: FargateSpot weight 4 base 0,
     Fargate weight 1 base 1 (workload is stateless, retriable)
  3. ARM64: rebuild image for linux/arm64; set
     runtimePlatform.cpuArchitecture = ARM64 (Java 21 is compatible)
ESTIMATED_SAVINGS: ~$470/month ($5,640/year)
  - Right-size: 10 tasks × ($63.51 - $31.39) = $321/month
  - Spot: 80% Spot on optimized base = ~$91/month additional
  - ARM64: 20% off the Spot rate = ~$58/month additional
MIGRATION_STEPS:
  1. Register new task definition order-processor:43 with cpu=1024,
     memory=2048, runtimePlatform.cpuArchitecture=ARM64
  2. Build multi-arch image:
     docker buildx build --platform linux/amd64,linux/arm64
       -t <repo>:v43 --push
  3. Create or verify FargateSpot capacity provider on the cluster
  4. Update service with capacity provider strategy:
     aws ecs update-service --cluster prod
       --service order-processor
       --task-definition order-processor:43
       --capacity-provider-strategy
         capacityProvider=FargateSpot,weight=4,base=0
         capacityProvider=Fargate,weight=1,base=1
  5. Monitor CPUUtilization for 7 days; revert if avg > 70%
```

## What the skill caught that a generic assistant misses

1. **The combo-floor rule.** A generic assistant says "reduce CPU" but
   does not know the Fargate allowed-combination table constrains the
   memory range per CPU tier. The skill identifies the exact target
   combo (1 vCPU / 2 GB) and verifies it is a valid combination.

2. **The stacking math.** A generic assistant recommends "Spot" or
   "ARM64" independently. The skill stacks all three dimensions:
   right-size reduces the base, Spot takes 70% off the base, ARM64
   takes another 20% off the Spot price. The combined savings are
   multiplicative, not additive.

3. **The JVM memory check.** A generic assistant might not check the
   `-XX:MaxRAMPercentage` flag. The skill verifies the Java memory
   configuration before recommending a memory reduction — preventing
   OOMKill after the right-size.

4. **The Spot eligibility assessment.** A generic assistant might
   recommend Spot without checking if the workload is fault-tolerant.
   The skill reads the workload description (stateless behind ALB,
   retriable) and confirms Spot is safe.

## Slash-command invocation

```
/aws:optimize-fargate-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "order-processor Fargate service at 18% CPU, 10 tasks, $636/month — optimise"
```

The orchestrator emits `[Phase: Optimize | Skills routed:
fargate-cost-optimizer]` and hands off to this skill for the VERDICT.

## Live-account diagnostic flow (requires AWS CLI)

When the operator has AWS credentials:

```bash
# Read the current task definition.
aws ecs describe-task-definition \
  --task-definition order-processor:42 \
  --query 'taskDefinition.{cpu:cpu,memory:memory,arch:runtimePlatform.cpuArchitecture}'

# Pull 14-day CPU and memory utilization.
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=prod Name=ServiceName,Value=order-processor \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date +%u -d 'now' +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# Register the optimized task definition.
aws ecs register-task-definition \
  --family order-processor \
  --cpu 1024 --memory 2048 \
  --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX \
  --container-definitions '<updated-json>'

# Update the service with Spot capacity provider strategy.
aws ecs update-service \
  --cluster prod \
  --service order-processor \
  --task-definition order-processor:43 \
  --capacity-provider-strategy \
    capacityProvider=FargateSpot,weight=4,base=0 \
    capacityProvider=Fargate,weight=1,base=1
```

The 18% CPU utilization on 2 vCPU (0.36 vCPU actual) plus 42% memory
on 4 GB (1.68 GB actual) confirms the task can safely drop to 1 vCPU /
2 GB. Spot eligibility is confirmed by the stateless workload
description.
