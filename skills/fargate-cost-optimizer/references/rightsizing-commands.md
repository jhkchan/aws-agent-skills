# Fargate Right-Sizing and Optimization Commands — Reference

Supplementary reference for the Fargate Cost Optimizer skill. The
canonical command script per optimization dimension.

## Universal first commands (run for any Fargate cost review)

```bash
# 1. List ECS services and their task definitions:
aws ecs describe-services \
  --cluster <cluster> \
  --services <service> \
  --query 'services[*].{name:serviceName,taskDef:taskDefinition,desired:desiredCount,providers:capacityProviderStrategy}'

# 2. Read the task definition CPU/memory/architecture:
aws ecs describe-task-definition \
  --task-definition <task-def> \
  --query 'taskDefinition.{cpu:cpu,memory:memory,arch:runtimePlatform.cpuArchitecture,family:family}'

# 3. Pull 14-day CPU utilization:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average Maximum

# 4. Pull 14-day Memory utilization:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average Maximum
```

## Dimension A: Right-size (CPU/memory combo change)

```bash
# Register a new task definition with downsized CPU/memory:
aws ecs register-task-definition \
  --family <family> \
  --cpu "1024" \
  --memory "2048" \
  --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX \
  --container-definitions '<json>'

# Update the service to use the new task definition:
aws ecs update-service \
  --cluster <cluster> \
  --service <service> \
  --task-definition <family>:<new-revision>
```

## Dimension B: Fargate Spot capacity provider

```bash
# Create a capacity provider with Spot:
aws ecs create-capacity-provider \
  --name FargateSpotProvider \
  --auto-scaling-group-provider <asg-arn>

# Or use the built-in FargateSpot capacity provider (no creation needed):
# Update the service with a capacity provider strategy:
aws ecs update-service \
  --cluster <cluster> \
  --service <service> \
  --capacity-provider-strategy \
    capacityProvider=FargateSpot,weight=4,base=0 \
    capacityProvider=Fargate,weight=1,base=1
```

## Dimension C: ARM64 migration

```bash
# Build a multi-arch image:
docker buildx build --platform linux/amd64,linux/arm64 \
  -t <repo>:<tag> --push

# Register a task definition with ARM64:
aws ecs register-task-definition \
  --family <family> \
  --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX \
  --cpu <cpu> --memory <memory> \
  --container-definitions '<json with arm64 image>'
```

## Dimension D: Auto scaling policy

```bash
# Register the scalable target:
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/<cluster>/<service> \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 20

# Create a target tracking scaling policy on CPU:
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/<cluster>/<service> \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":60.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ECSServiceAverageCPUUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":300}'
```

## Dimension E: Savings Plans

```bash
# Check current SP utilization:
aws ce get-savings-plans-utilization \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY

# Get Fargate spend:
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --metrics "UnblendedCost" \
  --filter '{"Dimensions":{"Key":"Service","Values":["Elastic Compute Cloud - CloudWatch"]}}'
```

## Verification commands (post-optimization)

```bash
# Monitor CPU after right-sizing:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 \
  --statistics Average Maximum

# Check service events for Spot interruptions:
aws ecs describe-services \
  --cluster <cluster> \
  --service <service> \
  --query 'services[0].events[:10]'
```

## Step 0: target capture commands (moved from SKILL.md)

```bash
# Describe the current task definition:
aws ecs describe-task-definition \
  --task-definition <task-def> \
  --query 'taskDefinition.{cpu:cpu,memory:memory,arch:runtimePlatform.cpuArchitecture,containerDefs:containerDefinitions[*].{name:name,cpu:cpu,memory:memory,memoryReservation:memoryReservation}}'

# Pull 14-day CPU and memory utilization:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 \
  --statistics Average Maximum \
  --query 'Datapoints[*].{time:Timestamp,avg:Average,max:Maximum}'
```

## Step 2: right-size diagnostic commands (moved from SKILL.md)

**Diagnostic commands:**

```bash
# 14-day CPU utilization (hourly avg + max):
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum

# 14-day Memory utilization:
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ClusterName,Value=<cluster> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 3600 --statistics Average Maximum
```

## Step 5: auto scaling policy command (moved from SKILL.md)

**Auto scaling policy recommendation:**

```bash
# Create a target tracking scaling policy on CPU utilization:
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/<cluster>/<service> \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 20

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/<cluster>/<service> \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name cpu-target-tracking \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration \
    '{"TargetValue":60.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"ECSServiceAverageCPUUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":300}'
```

## Step 6: Savings Plans diagnostic commands (moved from SKILL.md)

**Diagnostic commands:**

```bash
# Check current Savings Plans utilization and coverage:
aws ce get-savings-plans-utilization \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY

# Get Fargate spend by service:
aws ce get-cost-and-usage \
  --time-period Start=2026-07-01,End=2026-08-01 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"Service","Values":["Elastic Compute Cloud - CloudWatch"]}}' \
  --metrics "UsageQuantity" "UnblendedCost" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE
```
