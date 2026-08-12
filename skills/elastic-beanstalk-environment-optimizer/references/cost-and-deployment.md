# Cost and Deployment — Elastic Beanstalk Environment Optimizer

Deep reference on cost analysis (single-instance vs load-balanced
breakdown, NAT Gateway elimination, RDS cost models), deployment policy
selection (All at Once, Rolling, Immutable, Traffic Splitting cost
trade-offs), and managed platform update scheduling. Loaded on demand by
the skill — kept out of the main SKILL.md body so the optimization
procedure stays scannable.

## Single-instance vs load-balanced cost breakdown

### Full cost comparison (us-east-1, on-demand Linux pricing)

| Component | Load-balanced (2 instances) | Single-instance |
|---|---|---|
| t3.small instances (2 vs 1) | $30.36/mo (2x $15.18) | $15.18/mo |
| Application Load Balancer | $18.00/mo (base + LCUs) | $0 (no ELB) |
| NAT Gateway | $32.40/mo (base per AZ) | $0 (uses IGW) |
| Data processing (NAT) | ~$5.00/mo (dev traffic) | $0 |
| **Total** | **~$85.76/mo** | **~$15.18/mo** |

**Savings by switching to single-instance: ~$70.58/mo (~82%)**

```text
Cost waterfall (load-balanced → single-instance):
  $85.76/mo (load-balanced)
    - $15.18 (remove 1 instance: 2 → 1)
    - $18.00 (remove ALB)
    - $32.40 (remove NAT Gateway)
    - $5.00 (remove NAT data processing)
  = $15.18/mo (single-instance)
```

### When single-instance is appropriate

- Dev or staging environment (not customer-facing)
- Brief downtime during deploy is acceptable (seconds to minutes)
- No need for horizontal auto-scaling
- No need for multi-AZ high availability
- Single instance is sufficient for the workload

### When load-balanced is required

- Production environment serving live traffic
- Zero-downtime deployment required
- Horizontal auto-scaling needed (traffic spikes)
- Multi-AZ high availability required (SLA)
- Canary or traffic-splitting deployment strategy needed

## NAT Gateway cost analysis

### NAT Gateway pricing

| Component | Cost |
|---|---|
| Hourly (per NAT Gateway) | $0.045/hr |
| Monthly (base) | $32.40/mo |
| Data processing | $0.045/GB (first 10TB/month) |
| Typical dev data processing | ~50GB/mo = ~$2.25 |
| **Total for one NAT Gateway** | **~$34.65/mo** |

### When NAT Gateway can be eliminated

```text
NAT Gateway elimination checklist:
  [✓] Environment is single-instance (not load-balanced)
  [✓] Instance is in a public subnet (has direct IGW route)
  [✓] Instance has a public IP or Elastic IP
  [✓] Security group allows outbound on required ports (80, 443)
  [✓] Environment is dev/staging (not production)
  → Safe to eliminate NAT Gateway

If any check fails → keep the NAT Gateway
```

### NAT Gateway elimination procedure

```bash
# Step 1: Verify instance has a public IP
aws ec2 describe-instances \
  --filters Name=tag:elasticbeanstalk:environment-name,Values=my-dev-env \
  --query 'Reservations[*].Instances[*].{PublicIp:PublicIpAddress,Subnet:SubnetId}' \
  --output table --region us-east-1

# Step 2: Verify the route table has an IGW route for 0.0.0.0/0
aws ec2 describe-route-tables \
  --filters Name=tag:elasticbeanstalk:environment-name,Values=my-dev-env \
  --query 'RouteTables[0].Routes[?DestinationCidrBlock==`0.0.0.0/0`]' \
  --output table --region us-east-1

# Step 3: Delete the NAT Gateway
aws ec2 delete-nat-gateway \
  --nat-gateway-id nat-xxx \
  --region us-east-1

# Step 4: Verify no resources depend on the NAT Gateway
# (check other route tables, other environments in the same VPC)
aws ec2 describe-route-tables \
  --filters Name=vpc-id,Values=vpc-xxx \
  --query 'RouteTables[*].{Id:RouteTableId,NAT:Routes[?NatGatewayId!=`null`].{Dest:DestinationCidrBlock,NAT:NatGatewayId}}' \
  --output table --region us-east-1
```

**Critical:** verify no other environments or resources in the VPC
depend on the NAT Gateway before deleting it. Shared VPCs may have
other environments routing through the same NAT Gateway.

## Deployment policy cost analysis

### Deployment policy comparison

| Policy | Extra instances during deploy | Downtime | Best for |
|---|---|---|---|
| All at Once | 0 (same instances) | Yes (all updated at once) | Dev/staging |
| Rolling | 0 (batch in place) | No (reduced capacity) | Staging/light prod |
| Rolling + Additional Batch | +1 batch | No (full capacity) | Production |
| Immutable | +1 full ASG (2x) | No (zero downtime) | Critical production |
| Traffic Splitting | +1 canary batch | No | Production with canary |

### Immutable deployment cost calculation

```text
Immutable deploy cost formula:
  extra_instances = current instance count
  deploy_duration = time to deploy (minutes)
  instance_hourly_rate = instance type hourly cost

  Extra cost = extra_instances × instance_hourly_rate × (deploy_duration / 60)

Example:
  Environment: 3x m5.large ($0.096/hr each)
  Deploy duration: 20 minutes
  Extra cost = 3 × $0.096 × (20/60) = $0.096 per deploy

  At 10 deploys/day for dev: $0.96/day = ~$29/mo
  At 1 deploy/week for prod: $0.10/week = ~$0.40/mo
```

**Key insight:** Immutable deployment cost is negligible for production
(few deploys, critical uptime) but significant for dev (frequent
deploys, downtime acceptable). Use All at Once for dev.

## Managed platform update scheduling

### Update levels

| Level | Description | Risk | Recommended for |
|---|---|---|---|
| `minor` | Patch and minor version updates | Very low (backward compatible) | All environments |
| `patch` | Security patches only | Very low | Conservative environments |
| `major` | Major version updates | Medium (may break compatibility) | Only after testing in staging |

### Scheduling best practices

```bash
# Enable managed updates with off-peak schedule
aws elasticbeanstalk update-environment \
  --environment-name my-prod-app \
  --option-settings \
    Namespace=aws:elasticbeanstalk:managedactions,OptionName=ManagedActionsEnabled,Value=true \
    Namespace=aws:elasticbeanstalk:managedactions,OptionName=PreferredStartTime,Value=Sun:04:00 \
    Namespace=aws:elasticbeanstalk:managedactions:platformupdate,OptionName=UpdateLevel,Value=minor \
    Namespace=aws:elasticbeanstalk:managedactions:platformupdate,OptionName=InstanceRefreshEnabled,Value=true \
  --region us-east-1
```

### Maintenance window selection

| Application peak | Recommended window | Timezone |
|---|---|---|
| Business hours (09:00-18:00) | Sun:04:00-06:00 | UTC |
| Evening peak (18:00-23:00) | Sun:06:00-08:00 | UTC |
| 24/7 (global) | Sun:04:00-06:00 | UTC (pick lowest traffic) |

### Instance refresh

`InstanceRefreshEnabled=true` uses Elastic Beanstalk's instance refresh
feature, which replaces instances one at a time in a rolling fashion.
This provides zero-downtime updates for load-balanced environments.

For single-instance environments, managed updates cause brief downtime
(the single instance is replaced). Schedule these during acceptable
downtime windows.

## RDS cost models

### Attached vs external RDS

| Feature | Attached (environment) | External (standalone) |
|---|---|---|
| Lifecycle | Deleted with environment | Independent |
| Cost | Same as standalone | Same as standalone |
| Convenience | Auto-provisioned | Manual setup |
| Safety | Risk of data loss on termination | Safe from environment deletion |
| Sharing | One per environment | Can share across environments |

### RDS instance class cost comparison (dev)

| Instance class | Cost/mo | CPU | Memory | Architecture |
|---|---|---|---|---|
| db.t3.micro | $11.00 | 2 vCPU | 1 GB | x86 |
| db.t3.small | $22.00 | 2 vCPU | 2 GB | x86 |
| db.t3.medium | $44.00 | 2 vCPU | 4 GB | x86 |
| db.t4g.micro | $9.00 | 2 vCPU | 1 GB | ARM (Graviton) |
| db.t4g.small | $18.00 | 2 vCPU | 2 GB | ARM (Graviton) |
| db.t4g.medium | $36.00 | 2 vCPU | 4 GB | ARM (Graviton) |

**Graviton advantage:** t4g instances are ~18% cheaper than t3 and
offer ~20% better price-performance for supported database engines
(PostgreSQL, MySQL, MariaDB).

### Shared RDS across environments

```text
Shared RDS strategy (for dev environments):
  1x db.t4g.medium instance with 3 separate databases:
    - dev_app_1 (for my-dev-app-1)
    - dev_app_2 (for my-dev-app-2)
    - dev_app_3 (for my-dev-app-3)

  Cost: $36.00/mo (1 instance, 3 databases)
  vs:   $132.00/mo (3x db.t3.medium)
  Savings: $96.00/mo (73%)
```

## Terraform cost-optimized example

```hcl
# Dev environment — single-instance, no ELB, no NAT
resource "aws_elastic_beanstalk_environment" "dev" {
  name                = "my-dev-app"
  application         = aws_elastic_beanstalk_application.app.name
  solution_stack_name = "64bit Amazon Linux 2023 v6.0.0 running Node.js 20"
  cname_prefix        = "my-dev-app"

  setting {
    namespace = "aws:elasticbeanstalk:environment"
    name      = "EnvironmentType"
    value     = "SingleInstance"
  }

  setting {
    namespace = "aws:autoscaling:launchconfiguration"
    name      = "InstanceType"
    value     = "t3.small"
  }

  setting {
    namespace = "aws:elasticbeanstalk:command"
    name      = "DeploymentPolicy"
    value     = "AllAtOnce"
  }

  setting {
    namespace = "aws:elasticbeanstalk:managedactions"
    name      = "ManagedActionsEnabled"
    value     = "true"
  }

  setting {
    namespace = "aws:elasticbeanstalk:managedactions"
    name      = "PreferredStartTime"
    value     = "Sun:04:00"
  }

  setting {
    namespace = "aws:elasticbeanstalk:managedactions:platformupdate"
    name      = "UpdateLevel"
    value     = "minor"
  }
}
```
