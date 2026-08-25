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

## Expert heuristic: single-instance savings breakdown (from SKILL.md)

A baseline model says "use smaller instances." The correct heuristic
recognizes that the topology choice (single-instance vs load-balanced)
has a larger cost impact than instance size.

```text
Load-balanced dev environment (2 instances + ELB + NAT):
  2x t3.small instances     = $30.36/mo (2 × $15.18)
  Application Load Balancer = $18.00/mo (base + LCUs)
  NAT Gateway               = $32.00/mo (base, per AZ)
  Data processing (NAT)     = ~$5.00/mo (dev traffic)
  ─────────────────────────────────────
  Total                     ≈ $85.36/mo

Single-instance dev environment (1 instance, no ELB, no NAT):
  1x t3.small instance      = $15.18/mo
  (no ELB)                  = $0.00
  (no NAT Gateway)          = $0.00
  (IGW for outbound)        = $0.00
  ─────────────────────────────────────
  Total                     ≈ $15.18/mo

Savings: $70.18/mo (~82% reduction for dev/staging)
```

**Key implication:** for dev/staging environments, switching from
load-balanced to single-instance is the single most impactful cost
optimization. The instance size is secondary.

## Expert heuristic: deployment policy cost analysis (from SKILL.md)

Elastic Beanstalk supports multiple deployment policies, each with
different cost and downtime characteristics.

```text
Deployment policy cost comparison (for a load-balanced environment):

  All at Once:
    Instances used during deploy: same (no new instances)
    Downtime: YES (all instances updated simultaneously)
    Extra cost during deploy: $0
    Best for: dev/staging (brief downtime acceptable)

  Rolling:
    Instances used during deploy: same (batch updates in place)
    Downtime: NO (some instances always serve traffic)
    Extra cost during deploy: $0 (uses existing capacity)
    Best for: production with tolerance for reduced capacity

  Rolling with Additional Batch:
    Instances used during deploy: existing + 1 batch
    Downtime: NO
    Extra cost during deploy: ~1 batch of instances (temporary)
    Best for: production needing full capacity during deploy

  Immutable:
    Instances used during deploy: full duplicate ASG
    Downtime: NO
    Extra cost during deploy: ~2x instance cost during deploy window
    Best for: production zero-downtime, critical applications

  Traffic Splitting ( Canary ):
    Instances used during deploy: existing + canary instances
    Downtime: NO
    Extra cost during deploy: canary instances (temporary)
    Best for: production with canary testing
```

**Key implication:** Immutable deployment effectively doubles your
compute cost during the deployment window. For a 20-minute deploy on a
2-instance t3.medium environment, that is ~$0.04 extra. Negligible per-
deploy, but significant if deployments are frequent. For dev/staging,
"All at Once" is free.

## Expert heuristic: managed platform update scheduling (from SKILL.md)

Managed platform updates keep the environment on the latest platform
version. AWS applies them during a configurable maintenance window.
Scheduling updates during off-peak hours minimizes user impact.

```text
Managed update scheduling:
  Update level: minor (patch) | major (breaking changes possible)
  Maintenance window: configure weekly recurring window
    Example: Sunday 04:00-06:00 UTC (lowest traffic)

  Update instance selection:
    └── Elastic Beanstalk replaces instances one at a time
        during the maintenance window
        └── For single-instance: brief downtime during update
        └── For load-balanced: rolling update, no downtime
```

**Key implication:** managed platform updates during off-peak hours
reduce user impact to near zero. Leaving updates unscheduled means AWS
may apply them at any time, potentially during peak traffic.

## Opt 1 — update instance type command (from SKILL.md)

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.small \
  --region us-east-1
```

## Opt 2 — when to use single-instance vs load-balanced (from SKILL.md)

- Dev or staging environment (not production)
- Brief downtime during deploy is acceptable
- No need for horizontal auto-scaling
- No need for multi-AZ high availability

**When to use load-balanced:**
- Production environment
- Zero-downtime deployment required
- Horizontal auto-scaling needed
- Multi-AZ high availability required

## Opt 2 — switch to single-instance command (from SKILL.md)

```bash
# Change the environment to single-instance
aws elasticbeanstalk update-environment \
  --environment-name my-dev-env \
  --option-settings \
    Namespace=aws:elasticbeanstalk:environment,OptionName=EnvironmentType,Value=SingleInstance \
  --region us-east-1

# This removes the ELB and reduces to 1 instance
# NOTE: this causes a brief environment restart
```

## Opt 2 — topology switch cost impact (from SKILL.md)

**Cost impact:**

```text
Before (load-balanced, 2x t3.small):
  2x t3.small ($30.36) + ELB ($18.00) + NAT ($32.00) = $80.36/mo

After (single-instance, 1x t3.small):
  1x t3.small ($15.18) = $15.18/mo

Savings: $65.18/mo (~81%)
```

## Opt 3 — switch to burstable instance command (from SKILL.md)

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-dev-env \
  --option-settings Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t4g.small \
  --region us-east-1
```

## Opt 4 — change deployment policy commands (from SKILL.md)

```bash
# For single-instance: only "all at once" is available
# For load-balanced dev: rolling (cheapest, minor capacity reduction)
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings \
    Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Rolling \
    Namespace=aws:elasticbeanstalk:command,OptionName=RollingEnabled,Value=true \
    Namespace=aws:elasticbeanstalk:command,OptionName=RollingUpdateType,Value=Time \
    Namespace=aws:elasticbeanstalk:command,OptionName=RollingUpdateTime,Value=5 \
  --region us-east-1

# For load-balanced production: immutable (zero-downtime, 2x cost during deploy)
aws elasticbeanstalk update-environment \
  --environment-name my-prod-env \
  --option-settings \
    Namespace=aws:elasticbeanstalk:command,OptionName=DeploymentPolicy,Value=Immutable \
  --region us-east-1
```

## Opt 4 — deployment policy cost recommendation (from SKILL.md)

**Cost optimization recommendation:**

```text
Production (zero-downtime required):
  Immutable — accept 2x cost during deploy (~20 min window)

Dev/Staging (downtime acceptable):
  All at Once (single-instance) — $0 extra deploy cost
  Rolling (load-balanced) — $0 extra deploy cost

Cost difference per deploy:
  Immutable (2x t3.medium for 20 min): ~$0.04/deploy
  All at Once: $0.00/deploy

For 10 deploys/day on dev: $0.40/day = $12/mo saved by using All at Once
```

## Opt 5 — schedule managed updates off-peak command (from SKILL.md)

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings \
    Namespace=aws:elasticbeanstalk:managedactions,OptionName=ManagedActionsEnabled,Value=true \
    Namespace=aws:elasticbeanstalk:managedactions,OptionName=PreferredStartTime,Value=Sun:04:00 \
    Namespace=aws:elasticbeanstalk:managedactions:platformupdate,OptionName=UpdateLevel,Value=minor \
    Namespace=aws:elasticbeanstalk:managedactions:platformupdate,OptionName=InstanceRefreshEnabled,Value=true \
  --region us-east-1
```

## Opt 5 — update level options and key recommendation (from SKILL.md)

**Update level options:**

| Level | Description | When to use |
|---|---|---|
| `minor` | Patch and minor version updates | Always (backward compatible) |
| `patch` | Security patches only | Conservative environments |
| `major` | Major version updates | Only after testing |

**Key recommendation:** schedule updates for Sunday 04:00 UTC (or the
lowest-traffic window for your application). Enable `InstanceRefreshEnabled`
to use Elastic Beanstalk's instance refresh for zero-downtime updates on
load-balanced environments.

## Opt 6 — common .ebextensions optimizations (from SKILL.md)

- Remove unused `Resources:` blocks (e.g., test S3 buckets, old SQS
  queues).
- Consolidate duplicate `files:` or `packages:` entries.
- Move static configurations to `.platform/` (for Amazon Linux 2/2023).
- Remove `commands:` that were one-time setup (e.g., creating a database
  that already exists).

## Opt 8 — NAT Gateway cost breakdown (from SKILL.md)

**NAT Gateway cost breakdown:**

```text
NAT Gateway cost (per AZ):
  Base hourly charge:  $0.045/hr = $32.40/mo
  Data processing:     $0.045/GB (first 10TB)
  ────────────────────────────────
  Minimum cost:        ~$32.40/mo per NAT Gateway

For a dev environment with 1 NAT Gateway:
  Monthly cost: ~$32.40 (base) + ~$2.25 (50GB processing)
  = ~$34.65/mo

Eliminating NAT Gateway: saves ~$34.65/mo
```

## Opt 8 — eliminate NAT Gateway commands (from SKILL.md)

```bash
# WARNING: verify the instance has a public IP first
# Delete the NAT Gateway
aws ec2 delete-nat-gateway --nat-gateway-id nat-xxx --region us-east-1

# Update the route table to use IGW instead of NAT for 0.0.0.0/0
aws ec2 replace-route \
  --route-table-id rtb-private-1 \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id igw-xxx \
  --region us-east-1

# NOTE: the subnet must be a PUBLIC subnet for this to work
# If the instance is in a private subnet, move it to a public subnet first
```

## Opt 9 — detach RDS from environment commands (from SKILL.md)

```bash
# Move RDS to external (outside of Elastic Beanstalk)
# 1. Create a snapshot of the environment-attached RDS
aws rds create-db-snapshot \
  --db-instance-identifier aa1xmpexample \
  --db-snapshot-identifier my-env-db-snapshot \
  --region us-east-1

# 2. Restore as a standalone RDS instance
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier my-standalone-db \
  --db-snapshot-identifier my-env-db-snapshot \
  --db-instance-class db.t3.micro \
  --region us-east-1

# 3. Update the environment to use the external RDS endpoint
# (update the RDS_HOSTNAME environment property)
```
