# ECS Autoscaling Configuration and Pricing Reference

Supplementary reference for the ECS Cluster Autoscaling Optimizer skill.
Loaded on-demand when detailed capacity provider JSON schemas, pricing
tables, target tracking metric guidance, or spot discount data are needed.

## EC2 instance pricing (us-east-1, 2026, USD)

### Common ECS instance types (on-demand vs spot)

| Instance type | vCPU | RAM (GB) | On-demand $/h | Spot $/h | Spot discount |
|---|---|---|---|---|---|
| m5.large | 2 | 8 | $0.096 | $0.029 | 70% |
| m5.xlarge | 4 | 16 | $0.192 | $0.058 | 70% |
| m5.2xlarge | 8 | 32 | $0.384 | $0.115 | 70% |
| m5.4xlarge | 16 | 64 | $0.768 | $0.230 | 70% |
| c5.large | 2 | 4 | $0.085 | $0.026 | 69% |
| c5.xlarge | 4 | 8 | $0.170 | $0.051 | 70% |
| c5.2xlarge | 8 | 16 | $0.340 | $0.102 | 70% |
| r5.large | 2 | 16 | $0.126 | $0.038 | 70% |
| r5.xlarge | 4 | 32 | $0.252 | $0.076 | 70% |
| r5.2xlarge | 8 | 64 | $0.504 | $0.151 | 70% |

### Fargate pricing

| Resource | Rate | Notes |
|---|---|---|
| vCPU per hour | $0.04048 | Per-task, per-second billing |
| GB memory per hour | $0.004445 | Per-task, per-second billing |
| Fargate vs EC2 premium | ~20% | Fargate costs ~20% more than equivalent EC2 for steady-state |

**Fargate cost example:** 4 vCPU + 16 GB task running 24/7:
`(4 × $0.04048 + 16 × $0.004445) × 730 = $162.18/month`

Equivalent EC2 (m5.xlarge, on-demand): `$0.192 × 730 = $140.16/month`
Fargate premium: ~16% (justified by zero capacity management).

## Capacity provider strategy JSON schema

### Capacity provider strategy for a service

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

| Field | Description | Effect |
|---|---|---|
| `capacityProvider` | Name of the capacity provider | Must exist on the cluster |
| `weight` | Relative distribution ratio | on-demand:spot = 1:4 means 20% on-demand, 80% spot (after base) |
| `base` | Minimum tasks on this provider | `base=2` guarantees 2 tasks always on on-demand |

**How base + weight works:**
1. `base` tasks go to the specified provider first (floor).
2. Remaining tasks distribute by `weight` ratio across all providers.

Example: 12 desired tasks, on-demand base=2 weight=1, spot weight=4:
- 2 tasks go to on-demand (base).
- 10 remaining: on-demand gets 10 × (1/5) = 2, spot gets 10 × (4/5) = 8.
- Total: 4 on-demand, 8 spot.

### Managed scaling configuration

```json
{
  "autoScalingGroupProvider": {
    "autoScalingGroupArn": "arn:aws:autoscaling:...",
    "managedScaling": {
      "status": "ENABLED",
      "targetCapacity": 100,
      "minimumScalingStepSize": 1,
      "maximumScalingStepSize": 100
    },
    "managedTermination": "ENABLED",
    "instanceWarmupPeriod": 60
  }
}
```

| Field | Default | Description |
|---|---|---|
| `managedScaling.status` | DISABLED | Enable native ECS managed scaling |
| `managedScaling.targetCapacity` | 100 | Target % of registered capacity to maintain |
| `managedScaling.minimumScalingStepSize` | 1 | Minimum instances to add per scale-out |
| `managedScaling.maximumScalingStepSize` | 10000 | Maximum instances to add per scale-out |
| `managedTermination` | DISABLED | Allow ECS to terminate instances during scale-in |
| `instanceWarmupPeriod` | 15 | Seconds before a new instance is considered available |

## Target tracking metric guide

| Predefined metric type | CloudWatch namespace | Description | Use case |
|---|---|---|---|
| `ECSServiceAverageCPUUtilization` | AWS/ECS | Avg CPU across all tasks in service | CPU-bound workloads |
| `ECSServiceAverageMemoryUtilization` | AWS/ECS | Avg memory across all tasks in service | Memory-bound (JVM, caching) |
| `ALBRequestCountPerTarget` | AWS/ApplicationELB | Requests per target per minute | Request-driven services |

**Custom metrics:** Use `CustomizedMetricSpecification` for DynamoDB
consumed capacity, SQS backlog, or business-specific signals.

**Dual-metric scaling (2025 feature):** A service can have both CPU and
memory target-tracking policies. The auto-scaler scales out if either
breaches its target; scales in only if both are below their targets.

### Recommended target values

| Metric | Target value | Rationale |
|---|---|---|
| CPU (CPU-bound) | 50-70% | Headroom for spikes without over-scaling |
| Memory (memory-bound) | 60-75% | Buffer before OOM risk |
| ALB RequestCountPerTarget | 1000-5000 | Depends on task processing capacity |

## Scale-in cooldown guidance

| Traffic CV (coefficient of variation) | Recommended cooldown | Rationale |
|---|---|---|
| < 0.3 (steady) | 300 s (default) | Prevents flapping on minor dips |
| 0.3-0.5 (moderate) | 180 s | Balanced |
| > 0.5 (spiky) | 60-120 s | Fast scale-in to eliminate waste |

**Minimum safe cooldown: 60 s.** Sub-60 s causes flapping — instances
scale in before warm-up completes, then immediately scale back out.

## EC2 instance warm-up reference

| AMI type | Boot + agent registration | Recommended `instanceWarmupPeriod` |
|---|---|---|
| Amazon Linux 2023 (ECS-optimized) | 30-60 s | 60 |
| Bottlerocket | 15-30 s | 30 |
| Custom AMI with userData | 60-120 s | 120 |
| Ubuntu 22.04 with ECS agent | 45-90 s | 90 |

## Spot instance lifecycle in ECS

| State | Description | Duration |
|---|---|---|
| RUNNING | Normal operation | Until interruption notice |
| INTERRUPTION_NOTICE | 2-minute warning from EC2 | 120 s |
| DRAINING | ECS reschedules tasks to other instances | 30-120 s |
| DEPROVISIONING | Instance terminated | < 30 s |

**Spot interruption handler (2024-2025):** ECS automatically:
1. Receives the 2-minute notice via EventBridge.
2. Moves the instance to DRAINING.
3. Reschedules tasks to other capacity providers.
4. Prevents new task placement on the draining instance.

## Regional pricing multipliers

Approximate multiplier vs us-east-1 for EC2 on-demand and spot rates.

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| us-west-1 | 1.05x | Slight premium |
| eu-west-1, eu-west-2, eu-central-1 | 1.10-1.15x | EU premium |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | APAC premium |
| ap-northeast-1 (Tokyo) | 1.10-1.15x | |
| ap-south-1 (Mumbai) | 1.15-1.25x | |
| sa-east-1 (São Paulo) | 1.35-1.50x | Highest premium |

Always re-check via the AWS Pricing API for production estimates.

## CLI quick reference

### Describe cluster + capacity providers
```bash
aws ecs describe-clusters --clusters <name> --include ATTACHMENTS \
  --query 'clusters[0].{status:status,capacityProviders:capacityProviders,runningTasks:runningTasksCount,registeredContainerInstances:registeredContainerInstancesCount}' \
  --output json

aws ecs describe-capacity-providers --cluster <name> \
  --query 'capacityProviders[].{name:name,managedScaling:autoScalingGroupProvider.managedScaling.status,managedTermination:autoScalingGroupProvider.managedTermination}' \
  --output json
```

### Describe container instances (empty host detection)
```bash
aws ecs list-container-instances --cluster <name> --output text

aws ecs describe-container-instances \
  --cluster <name> \
  --container-instances <arn1> <arn2> \
  --query 'containerInstances[].{id:ec2InstanceId,status:status,running:runningTasksCount,cpu:remainingResources[?name==`CPU`].integerValue|[0],memory:remainingResources[?name==`MEMORY`].integerValue|[0]}' \
  --output table
```

### Update service capacity provider strategy + placement
```bash
aws ecs update-service \
  --cluster <name> \
  --service <service> \
  --capacity-provider-strategy \
    capacityProvider=on-demand-cp,weight=1,base=2 \
    capacityProvider=spot-cp,weight=4,base=0 \
  --placement-strategy \
    type=binpack,field=memory \
    type=spread,field=attribute:ecs.availability-zone
```

### Enable managed scaling on capacity provider
```bash
aws ecs update-capacity-provider \
  --name <cp-name> \
  --auto-scaling-group-provider \
    managedScaling.status=ENABLED,managedScaling.targetCapacity=100,managedScaling.minimumScalingStepSize=1,managedScaling.maximumScalingStepSize=100,managedTermination=ENABLED,instanceWarmupPeriod=60
```

### CloudWatch metrics
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=<name> Name=ServiceName,Value=<service> \
  --start-time $(date -u -d '-30 days' +%FT%TZ) \
  --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json
```

---

## Step 12 — impact estimation formula (moved from SKILL.md)

Compute the utilization improvement for each recommendation:

```
current_host_count = describe-container-instances count
current_avg_utilization = avg(CPUUtilization or MemoryUtilization)
projected_host_count = current_host_count × (current_avg_utilization / target_utilization)
host_savings = current_host_count - projected_host_count
monthly_savings = host_savings × 730 hours × $/hour

# For spot migration:
spot_savings = on_demand_hours_converted × 730 × (on_demand_rate - spot_rate)
```

Always state assumptions: target utilization, spot discount rate (70%
typical), node type, and region.
