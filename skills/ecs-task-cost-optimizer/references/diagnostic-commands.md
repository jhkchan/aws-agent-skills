# Diagnostic Commands (load on demand) — ECS Task Cost Optimizer

Data-source listings, per-step migration CLI, and pre-flight safety checks moved verbatim from SKILL.md. Loaded on demand.

---

## Pre-flight data gate — required data sources (moved from SKILL.md)

1. Service/task configuration: `aws ecs describe-services`, `aws ecs describe-task-definition`
2. CPU + Memory utilization (14-30 day window): `aws cloudwatch get-metric-statistics --namespace ECS/ContainerInsights`
3. Capacity providers: `aws ecs describe-capacity-providers`
4. Running task count: `aws cloudwatch get-metric-statistics --metric-name RunningTaskCount`
5. EC2 instance utilization (if EC2-backed): `aws cloudwatch get-metric-statistics --namespace AWS/EC2`
6. Savings Plan coverage: `aws savingsplans describe-savings-plans-coverage`
7. Cost Explorer breakdown: `aws ce get-cost-and-usage --service Amazon Elastic Container Service`

## Step 1 — capacity provider for launch type migration CLI (moved from SKILL.md)

**Capacity provider for launch type migration:**
```bash
# Create a capacity provider with EC2 ASG backing
aws ecs create-capacity-provider \
  --name ec2-cap-provider \
  --auto-scaling-group-provider \
    autoScalingGroupArn=<asg-arn>,managedScaling=...
```

## Step 2 — migrating to arm64 CLI (moved from SKILL.md)

**Migrating to arm64:**
```bash
# Register a new task definition with arm64 runtimePlatform
aws ecs register-task-definition \
  --family order-api \
  --runtime-platform cpuArchitecture=ARM64,operatingSystemFamily=LINUX \
  --container-definitions file://containers-arm64.json

# Update the service to use the new revision
aws ecs update-service \
  --cluster prod-cluster \
  --service order-api-prod \
  --task-definition order-api:43
```

## Step 4 — spot capacity provider setup CLI (moved from SKILL.md)

**Spot capacity provider setup:**
```bash
# Create a spot-backed capacity provider
aws ecs create-capacity-provider \
  --name spot-cap-provider \
  --auto-scaling-group-provider \
    autoScalingGroupArn=<spot-asg-arn>,\
    managedScaling=status=ENABLED,targetCapacity=70,\
    managedTerminationProtection=DISABLED

# Assign the strategy to the cluster
aws ecs put-cluster-capacity-providers \
  --cluster prod-cluster \
  --capacity-providers spot-cap-provider on-demand-cap-provider \
  --default-capacity-provider-strategy \
    capacityProvider=spot-cap-provider,weight=70,base=2,\
    capacityProvider=on-demand-cap-provider,weight=30
```

## Step 5 — Savings Plan coverage analysis CLI (moved from SKILL.md)

**Coverage analysis:**
```bash
# Check current SP coverage
aws savingsplans describe-savings-plans-coverage \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --granularity MONTHLY \
  --filter '{"Dimensions":{"Key":"Service","Values":["Amazon Elastic Container Service","AmazonEC2"]}}'

# Check SP utilization (are you using what you committed to?)
aws savingsplans describe-savings-plans-utilization \
  --time-period Start=2026-07-01,End=2026-07-31 \
  --granularity MONTHLY
```

## Step 6 — bin-pack placement CLI (moved from SKILL.md)

**Bin-pack placement for EC2 density:**
```bash
aws ecs create-service \
  --cluster prod-cluster \
  --service-name order-api-prod \
  --task-definition order-api:43 \
  --scheduling-strategy REPLICA \
  --placement-strategy type=binpack,field=memory \
  --placement-constraints type=distinctInstance
```

## Step 7 — scheduled scaling CLI (moved from SKILL.md)

**Scheduled scaling for known patterns:**
For workloads with predictable traffic (e.g., business-hours spike),
scheduled scaling is cheaper than reactive target tracking because it
pre-provisions before the load arrives:

```bash
aws application-autoscaling put-scheduled-action \
  --service-namespace ecs \
  --resource-id service/prod-cluster/order-api-prod \
  --scalable-dimension ecs:service:DesiredCount \
  --scheduled-action-name BusinessHoursScaleUp \
  --schedule "cron(0 9 ? * MON-FRI *)" \
  --scalable-target-action MinCapacity=10,MaxCapacity=20
```

## Pre-flight safety checks (moved from SKILL.md)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Canary deployments for task definition changes.** Never roll to 100%
  at once. Use CodeDeploy canary (10% → 50% → 100%) or weighted targets.
- **Graviton migration requires arm64 container image.** Verify the
  registry image is multi-arch or arm64-native before updating.
- **Right-sizing changes can cause OOM.** Monitor MemoryUtilization for
  24-48 hours after reducing memory. Roll back immediately on OOM.
- **Capacity provider changes trigger task replacement.** New tasks
  launch on the new infrastructure; existing tasks may be drained.
- **Spot capacity provider requires drain hook.** Application must handle
  SIGTERM; stopTimeout >= 30 seconds for graceful connection draining.
- **Savings Plan purchases are irreversible.** A 1-3 year commitment
  cannot be cancelled. Verify the spend baseline is stable first.
- **Auto-scaling changes can cause flapping.** Change target tracking
  in small increments (5-10% at a time).
- **Bulk-operation limit:** Process at most 5 services per batch. Sort
  by estimated savings, verify each batch. Abort on errors or latency.
