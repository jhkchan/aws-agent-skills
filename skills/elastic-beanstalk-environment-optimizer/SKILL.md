---
name: elastic-beanstalk-environment-optimizer
description: Optimizes AWS Elastic Beanstalk environments for cost and performance. Covers instance type right-sizing (single-instance vs load-balanced), t3/t4g burstable instances for dev, managed platform update scheduling, .ebextensions cleanup, deployment policy selection (immutable for zero-downtime but 2x cost during deploy), worker tier, health check tuning, auto-scaling policy tuning, RDS integration cost (shared vs dedicated), NAT Gateway elimination for single- instance, and termination protection cleanup. Emits an OPTIMIZED assessment with cost savings estimates or FURTHER_OPTIMIZATION_AVAILABLE with specific recommendations. Use when optimizing Beanstalk cost, right-sizing EB instances, reducing deployment cost, tuning auto-scaling, eliminating NAT Gateway for dev, or scheduling managed platform updates. Triggers - optimize elastic beanstalk, eb cost optimization, beanstalk right-size, single-instance vs load-balanced, immutable deployment cost, nat gateway elimination, ebextensions cleanup, rds shared cost.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live optimization - AWS CLI v2 with elasticbeanstalk, ec2, rds, elasticloadbalancing, and cloudwatch access. Works with Terraform aws_elastic_beanstalk_environment resources and CloudFormation AWS::ElasticBeanstalk templates.
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Compute
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, elastic-beanstalk, cost-optimization, cloudops, optimize, compute, right-sizing, auto-scaling, deployment-policy, managed-platform, nat-gateway, ebextensions
  dependencies: aws-orchestrator
  keywords: aws, elastic beanstalk, cost optimization, instance right-sizing, single-instance, load-balanced, t3 burstable, t4g burstable, managed platform update, ebextensions, deployment policy, immutable deploy, rolling deploy, worker tier, auto-scaling, nat gateway, rds, health check, cloudops, optimize
  when_to_use: Invoke when the user wants to optimize Elastic Beanstalk environments for cost, right-size instance types, choose single-instance vs load- balanced topology, reduce deployment costs, tune auto-scaling policies, eliminate NAT Gateway for dev/staging, schedule managed platform updates, clean up .ebextensions, or optimize RDS integration costs. Do NOT invoke for ECS/EKS optimization, Lambda optimization, or EC2 Auto Scaling Groups (non-Beanstalk).
---

# Elastic Beanstalk Environment Optimizer

An AWS CloudOps agent skill that optimizes Elastic Beanstalk
environments for cost and performance with methodical analysis. The
skill walks the operator through instance type right-sizing, single-
instance vs load-balanced topology, deployment policy cost trade-offs,
managed platform update scheduling, auto-scaling policy tuning, NAT
Gateway elimination, RDS cost optimization, .ebextensions cleanup, and
health check tuning, captures environment configuration, explains why
each optimization matters, and emits an OPTIMIZED assessment with cost
savings estimates or FURTHER_OPTIMIZATION_AVAILABLE with specific
recommendations.

## Activation keywords

Optimize Elastic Beanstalk, EB cost optimization, Beanstalk right-size
instances, single-instance vs load-balanced, immutable deployment cost,
managed platform update schedule, NAT Gateway elimination, ebextensions
cleanup, Beanstalk auto-scaling tune, RDS shared cost.

## STRICT output contract

When this skill is invoked with an Elastic Beanstalk optimization
request (cost reduction, right-sizing, deployment policy, auto-scaling,
NAT Gateway, managed updates, or a partial configuration), the agent
MUST respond with the OPTIMIZED assessment block defined in the
"Output format" section using the literal all-caps labels `EB_ENV:`,
`VERDICT:`, `OPTIMIZATIONS:`, `COST_IMPACT:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the assessment with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
optimization pipelines rely on; deviating from the literal labels breaks
automation silently.

If further optimizations are available, the verdict is
`FURTHER_OPTIMIZATION_AVAILABLE` with specific recommendations in the
optimizations list (marked `[~]`), and `OPTIMIZED` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Optimization prerequisites | Always — gather before optimizing |
| Opt 1 — Instance type right-sizing | Instance selection |
| Opt 2 — Single-instance vs load-balanced | Topology decision |
| Opt 3 — t3/t4g burstable instances for dev | Dev/staging cost |
| Opt 4 — Deployment policy selection | Deploy cost vs downtime |
| Opt 5 — Managed platform update scheduling | Update impact |
| Opt 6 — .ebextensions optimization | Config cleanup |
| Opt 7 — Auto-scaling policy tuning | Capacity efficiency |
| Opt 8 — NAT Gateway elimination | Network cost |
| Opt 9 — RDS integration cost | Database cost |
| Opt 10 — Health check tuning | Alert false positives |
| Opt 11 — Termination protection cleanup | Safety vs cost |
| NEVER do these things | Review before signing off |
| Output format | The literal assessment template |
| references/cost-and-deployment.md | Cost + deployment detail |
| references/autoscaling-and-health.md | Auto-scaling + health detail |

## Mindset

**One-line takeaway:** A dev/staging Elastic Beanstalk environment on a
single-instance topology (no ELB, no NAT Gateway) saves approximately
60% compared to a load-balanced topology. Immutable deployments double
capacity temporarily during deploy. Managed platform updates should be
scheduled during off-peak hours.

Three misconceptions dominate Elastic Beanstalk cost optimization:

- **"Load-balanced is always the right choice."** It is NOT. For dev and
  staging environments, a single-instance topology eliminates the ELB
  (~$18/month), the NAT Gateway (~$32/month), and reduces instance count
  from 2+ to 1. This saves approximately 60% of the monthly running cost.
  Load-balanced is only necessary for production environments that need
  high availability, rolling deployments, or horizontal scaling.

- **"Immutable deployment is free."** It is NOT. Immutable deployment
  spins up a full set of new instances in an Auto Scaling Group, deploys
  the new version, and then swaps. During the deployment, you pay for
  BOTH the old and new instances simultaneously — effectively 2x compute
  cost during the deploy window. For dev/staging, rolling deployments
  with brief downtime are cheaper. Immutable is for production zero-
  downtime requirements.

- **"NAT Gateway is required for all VPC environments."** It is NOT. For
  single-instance environments where the instance has a public IP and
  security groups are properly configured, the instance can download
  dependencies (package updates, application gems/npm packages) directly
  via the Internet Gateway — no NAT Gateway needed. Eliminating the NAT
  Gateway saves ~$32/month per AZ plus data processing charges.

## Configuration dependency graph (novel heuristic)

Elastic Beanstalk optimizations are interconnected. Changing the
topology (single-instance vs load-balanced) affects instance count, ELB
cost, NAT Gateway necessity, and deployment policy options. Use this
graph to understand the cascading impact of each optimization.

| Optimization | Direct savings | Cascading impact | Trade-off |
|---|---|---|---|
| Single-instance topology | ELB (~$18/mo), extra instances | Eliminates NAT Gateway need (if public IP) | No HA, brief deploy downtime |
| NAT Gateway elimination | ~$32/mo per AZ + data processing | Requires public IP on instance | No private subnet outbound |
| Instance right-sizing | Instance cost delta | May change burstable vs fixed | Right-size for steady-state, not peak |
| Immutable → Rolling deploy | 2x cost during deploy → 1x | Less availability during deploy | Brief downtime (rolling) |
| Managed updates off-peak | No direct savings | Reduces user impact | Requires maintenance window |
| .ebextensions cleanup | No direct savings | Faster deployments, fewer resources | Requires config audit |
| Auto-scaling tune | Right-size min/max/desired | Reduces over-provisioning | Requires traffic analysis |

**The single-instance row is the one a baseline model misses.** Moving
from load-balanced to single-instance for dev/staging saves ~60% total
(monthly cost). The NAT Gateway elimination is the second-biggest win
(~$32/month). Together they transform a $150/month dev environment into
a ~$60/month environment.

**Cross-dependency gotchas:**
- Single-instance topology disables rolling and immutable deployments.
  Only "all at once" deployment is available (brief downtime during
  deploy).
- NAT Gateway elimination requires the instance to be in a public subnet
  with a public IP. This is fine for dev/staging but not recommended for
  production.
- Right-sizing instances must account for the application's steady-state
  resource usage, not peak bursts. Use CloudWatch metrics to determine
  average CPU and memory usage.
- Managed platform updates and deployment windows can conflict. Schedule
  them at different times to avoid simultaneous environment changes.
- Worker tier environments do not need an ELB (they use SQS). The
  single-instance vs load-balanced decision applies differently.

## Expert heuristic: single-instance savings breakdown

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

## Expert heuristic: deployment policy cost analysis

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

## Expert heuristic: managed platform update scheduling

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

## Optimization prerequisites (gather before optimizing)

Before emitting optimization recommendations, gather these prerequisites.
If critical data is missing, the assessment may be incomplete.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Environment name and ID | Identifies the environment | `aws elasticbeanstalk describe-environments` |
| Environment tier (web server or worker) | Determines applicable optimizations | `describe-environments --query` |
| Current instance type(s) | Baseline for right-sizing | `describe-configuration-settings` |
| Min/max/desired capacity | Auto-scaling baseline | `describe-configuration-settings` |
| Deployment policy | Deploy cost analysis | `describe-configuration-settings` |
| Load balancer type (if any) | ELB cost | `describe-configuration-settings` |
| VPC and subnet config | NAT Gateway analysis | `describe-configuration-settings` |
| Managed updates config | Update scheduling | `describe-configuration-settings` |
| .ebextensions count | Config audit | Check `.ebextensions/` directory |
| CloudWatch CPU utilization average | Right-sizing data | `aws cloudwatch get-metric-statistics` |
| Environment purpose (prod or dev/staging) | Topology decision | Ask the operator or check tags |

If any critical prerequisite is missing, note it in the assessment and
recommend gathering the data.

## Opt 1 — Instance type right-sizing

Instance right-sizing selects the smallest instance type that meets
steady-state resource requirements. Over-provisioned instances waste
money; under-provisioned instances degrade performance.

**Analyze CloudWatch metrics for right-sizing:**

```bash
# Get average CPU utilization over 14 days
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Values=i-aaa111222 \
  --start-time $(date -u -d '14 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Average Maximum \
  --output table --region us-east-1

# Right-sizing heuristic:
#   Average CPU < 20%  → instance is 2x+ over-provisioned (downsize)
#   Average CPU 20-40% → some room to downsize (one size smaller)
#   Average CPU 40-70% → well-provisioned (keep)
#   Average CPU > 70%  → under-provisioned (upsize)
```

**Right-sizing decision matrix:**

| Current type | Avg CPU | Recommended | Savings/mo |
|---|---|---|---|
| t3.medium | < 20% | t3.micro or t3.small | $15-23 |
| t3.large | < 20% | t3.small | $30 |
| m5.large | < 20% | t3.medium | $17 |
| m5.xlarge | < 30% | t3.large or m5.large | $31-62 |
| c5.xlarge | < 30% | t3.medium | $20 |

**Update instance type:**

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t3.small \
  --region us-east-1
```

## Opt 2 — Single-instance vs load-balanced

The topology choice (single-instance vs load-balanced) is the most
impactful cost optimization for dev/staging environments.

**When to use single-instance:**
- Dev or staging environment (not production)
- Brief downtime during deploy is acceptable
- No need for horizontal auto-scaling
- No need for multi-AZ high availability

**When to use load-balanced:**
- Production environment
- Zero-downtime deployment required
- Horizontal auto-scaling needed
- Multi-AZ high availability required

**Switch from load-balanced to single-instance:**

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

**Cost impact:**

```text
Before (load-balanced, 2x t3.small):
  2x t3.small ($30.36) + ELB ($18.00) + NAT ($32.00) = $80.36/mo

After (single-instance, 1x t3.small):
  1x t3.small ($15.18) = $15.18/mo

Savings: $65.18/mo (~81%)
```

**Critical:** switching to single-instance also eliminates the need for
a NAT Gateway (the instance can use a public IP + IGW). Remove the NAT
Gateway separately after confirming the instance has a public IP.

## Opt 3 — t3/t4g burstable instances for dev

Burstable instances (t3, t4g) are ideal for dev/staging environments
with intermittent workloads. They accumulate CPU credits during idle
periods and burst during active periods.

| Instance | vCPU | Memory | Cost/mo (Linux) | Best for |
|---|---|---|---|---|
| t3.micro | 2 | 1 GB | $7.59 | Lightweight dev |
| t3.small | 2 | 2 GB | $15.18 | Standard dev |
| t3.medium | 2 | 4 GB | $30.37 | Dev with moderate load |
| t4g.micro | 2 | 1 GB | $6.04 | ARM-based dev (Graviton) |
| t4g.small | 2 | 2 GB | $12.07 | ARM-based dev (Graviton) |
| t4g.medium | 2 | 4 GB | $24.14 | ARM-based dev (Graviton) |

**Graviton (t4g) cost advantage:** t4g instances are ~20% cheaper than
t3 instances and offer ~20% better price-performance. Use t4g if the
application supports ARM (most modern runtimes do).

**Switch to a burstable instance:**

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-dev-env \
  --option-settings Namespace=aws:autoscaling:launchconfiguration,OptionName=InstanceType,Value=t4g.small \
  --region us-east-1
```

**Unlimited mode vs standard:** for dev environments, standard burst
mode is sufficient. Unlimited mode charges for CPU credits beyond the
accumulated balance — not worth it for dev.

## Opt 4 — Deployment policy selection

The deployment policy affects both downtime and cost during deploys.

**Check current deployment policy:**

```bash
aws elasticbeanstalk describe-configuration-settings \
  --environment-name my-env \
  --query 'ConfigurationSettings[0].OptionSettings[?Namespace==`aws:elasticbeanstalk:command`]' \
  --output table --region us-east-1
```

**Change deployment policy:**

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

## Opt 5 — Managed platform update scheduling

Managed platform updates keep the environment on the latest platform
version. Schedule them during off-peak hours to minimize impact.

**Check current managed update config:**

```bash
aws elasticbeanstalk describe-configuration-settings \
  --environment-name my-env \
  --query 'ConfigurationSettings[0].OptionSettings[?Namespace==`aws:elasticbeanstalk:managedactions`]' \
  --output table --region us-east-1
```

**Schedule managed updates during off-peak:**

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

## Opt 6 — .ebextensions optimization

`.ebextensions` files contain YAML configuration that Elastic Beanstalk
applies during environment creation and deployment. Unused or redundant
configurations slow down deployments and can create unnecessary
resources.

**Audit .ebextensions:**

```bash
# List all .ebextensions files
ls -la .ebextensions/

# Check each file for unused resources
for f in .ebextensions/*.config; do
  echo "=== $f ==="
  grep -E "Resources:|files:|packages:|services:|commands:" "$f"
done

# Common issues:
# - Resources created for testing but never removed
# - Duplicate files: blocks across multiple config files
# - Commands that are no longer needed
# - Packages installed but not used by the application
```

**Common .ebextensions optimizations:**
- Remove unused `Resources:` blocks (e.g., test S3 buckets, old SQS
  queues).
- Consolidate duplicate `files:` or `packages:` entries.
- Move static configurations to `.platform/` (for Amazon Linux 2/2023).
- Remove `commands:` that were one-time setup (e.g., creating a database
  that already exists).

## Opt 7 — Auto-scaling policy tuning

Auto-scaling policies determine how the environment scales in response
to load. Over-provisioned auto-scaling wastes money; under-provisioned
scales too slowly.

**Check current auto-scaling config:**

```bash
aws elasticbeanstalk describe-configuration-settings \
  --environment-name my-env \
  --query 'ConfigurationSettings[0].OptionSettings[?Namespace==`aws:autoscaling:asg` || Namespace==`aws:autoscaling:trigger`]' \
  --output table --region us-east-1
```

**Right-size capacity:**

```bash
# Set min/max/desired capacity based on traffic analysis
# For dev: min=1, max=1, desired=1 (no scaling)
# For staging: min=1, max=2, desired=1 (limited scaling)
# For prod: min=2, max=N (based on peak traffic)
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings \
    Namespace=aws:autoscaling:asg,OptionName=MinSize,Value=2 \
    Namespace=aws:autoscaling:asg,OptionName=MaxSize,Value=6 \
    Namespace=aws:autoscaling:asg,OptionName=DesiredCapacity,Value=2 \
  --region us-east-1
```

**Tune scaling triggers:**

```bash
# Use CPU utilization as the scaling trigger (default)
# Adjust thresholds based on steady-state CPU patterns
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings \
    Namespace=aws:autoscaling:trigger,OptionName=MeasureName,Value=CPUUtilization \
    Namespace=aws:autoscaling:trigger,OptionName=Statistic,Value=Average \
    Namespace=aws:autoscaling:trigger,OptionName=Unit,Value=Percent \
    Namespace=aws:autoscaling:trigger,OptionName=LowerThreshold,Value=20 \
    Namespace=aws:autoscaling:trigger,OptionName=UpperThreshold,Value=70 \
    Namespace=aws:autoscaling:trigger,OptionName=LowerBreachScaleIncrement,Value=-1 \
    Namespace=aws:autoscaling:trigger,OptionName=UpperBreachScaleIncrement,Value=1 \
    Namespace=aws:autoscaling:trigger,OptionName=BreachDuration,Value=300 \
  --region us-east-1
```

## Opt 8 — NAT Gateway elimination

For single-instance dev/staging environments with a public IP, the NAT
Gateway can be eliminated. The instance accesses the internet via the
Internet Gateway (IGW), which is free.

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

**Verify the instance has a public IP before eliminating NAT:**

```bash
# Check if the instance has a public IP
aws ec2 describe-instances \
  --filters Name=tag:elasticbeanstalk:environment-name,Values=my-dev-env \
  --query 'Reservations[*].Instances[*].{PublicIp:PublicIpAddress,SubnetId:SubnetId}' \
  --output table --region us-east-1
```

**Eliminate NAT Gateway:**

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

**Critical:** NAT Gateway elimination is ONLY safe for dev/staging. For
production, instances should be in private subnets behind a NAT Gateway
for security.

## Opt 9 — RDS integration cost

Elastic Beanstalk can provision an RDS instance as part of the
environment or connect to an external RDS instance. Environment-
attached RDS is convenient but has lifecycle coupling (the database is
deleted when the environment is terminated).

**RDS cost optimization options:**

| Approach | Cost | Best for |
|---|---|---|
| Environment-attached RDS | Same as standalone RDS | Dev (auto-provisioned) |
| External shared RDS | Shared across environments | Multi-env (lower total) |
| Aurora Serverless v2 | Scales to zero (min ACU) | Dev with idle periods |
| RDS t-class (t3.micro) | ~$11/mo | Dev databases |

**Key recommendations:**
- For multiple dev/staging environments, use a shared external RDS
  instance with separate databases per environment. This is cheaper than
  one RDS per environment.
- For dev, use `db.t3.micro` or `db.t4g.micro` (Graviton, ~$9/mo).
- Use Aurora Serverless v2 for dev with `MinCapacity=0.5` ACU to reduce
  cost during idle periods.
- Detach RDS from the environment to prevent accidental deletion on
  environment termination.

**Detach RDS from environment (for safety):**

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

## Opt 10 — Health check tuning

Health check tuning reduces false alarms and unnecessary auto-scaling
triggered by overly aggressive health check thresholds.

**Check current health check config:**

```bash
aws elasticbeanstalk describe-configuration-settings \
  --environment-name my-env \
  --query 'ConfigurationSettings[0].OptionSettings[?Namespace==`aws:elasticbeanstalk:healthreporting:system`]' \
  --output table --region us-east-1
```

**Common health check issues:**
- Health check URL path is wrong (returns 404, marked unhealthy).
- Health check timeout is too short (marks instances unhealthy before
  the application starts up).
- Threshold too sensitive (marks instances unhealthy on brief CPU spike).

**Tune health check:**

```bash
aws elasticbeanstalk update-environment \
  --environment-name my-env \
  --option-settings \
    Namespace=aws:elasticbeanstalk:application,OptionName=Application Healthcheck URL,Value=/health \
    Namespace=aws:elasticbeanstalk:healthreporting:system,OptionName=SystemType,Value=enhanced \
  --region us-east-1
```

## Opt 11 — Termination protection cleanup

Termination protection prevents accidental environment deletion. For
production, keep it enabled. For dev/staging that should be torn down
after use, disabling termination protection allows cleanup.

**Check termination protection:**

```bash
aws elasticbeanstalk describe-environments \
  --environment-names my-dev-env \
  --query 'Environments[0].{Name:EnvironmentName,TerminationProtected:TerminationProtected}' \
  --output table --region us-east-1
```

**Disable for dev cleanup:**

```bash
# Only for dev/staging environments that should be torn down
aws elasticbeanstalk update-environment \
  --environment-name my-dev-env \
  --no-terminate-on-failure \
  --region us-east-1
```

## NEVER do these things

1. **NEVER switch a production environment to single-instance.** Single-
   instance eliminates the ELB and reduces instances to 1. This removes
   high availability and causes downtime during deploys and platform
   updates. Single-instance is for dev/staging ONLY.

2. **NEVER eliminate the NAT Gateway for production environments.**
   Production instances should be in private subnets behind a NAT
   Gateway for security. NAT Gateway elimination is for dev/staging
   single-instance environments with a public IP.

3. **NEVER use immutable deployment for dev/staging.** Immutable
   deployment doubles compute cost during the deploy window. For dev/
   staging where brief downtime is acceptable, use "All at Once" or
   "Rolling" deployment. Immutable is for production zero-downtime.

4. **NEVER right-size based on peak CPU only.** Right-size based on
   average CPU utilization over a 7-14 day period. Using only peak CPU
   leads to over-provisioning. Use CloudWatch metrics to analyze
   steady-state patterns.

5. **NEVER enable managed major version updates without testing.**
   Major platform updates can break application compatibility. Always
   set the update level to `minor` (backward compatible) and test major
   updates manually in a staging environment first.

6. **NEVER delete a NAT Gateway without verifying the instance has a
   public IP.** Without a public IP and IGW route, the instance cannot
   download dependencies or communicate with AWS services, causing
   deployment failures.

7. **NEVER leave RDS attached to a dev environment without termination
   protection awareness.** If the environment is terminated, the RDS is
   also terminated (unless a snapshot is configured). For important data,
   detach RDS or enable deletion protection on the RDS instance.

8. **NEVER set auto-scaling min=max for production.** This disables
   auto-scaling entirely. Set min < max to allow scaling. For dev,
   min=max=1 is fine (no scaling needed).

9. **NEVER ignore .ebextensions cleanup.** Unused resources in
   .ebextensions slow down deployments and can create unnecessary AWS
   resources that incur costs. Audit .ebextensions regularly.

10. **NEVER change deployment policy during a deploy.** The deployment
    policy change takes effect on the NEXT deploy, but changing it
    during an active deploy can cause inconsistent state. Wait for the
    current deploy to finish.

## Output format

```text
EB_ENV: <environment-name> (<environment-id>)
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
OPTIMIZATIONS:
  [✓|~|✗] Topology: Single-instance | Load-balanced (instance count: <n>)
  [✓|~|✗] Instance type: <current> → <recommended> (<reason>)
  [✓|~|~] Deployment policy: <current> → <recommended> (cost impact: <description>)
  [✓|~|✗] Managed updates: <enabled/disabled> <schedule> → <recommended schedule>
  [✓|~|✗] NAT Gateway: <present/eliminated> (<cost/mo>)
  [✓|~|✗] Auto-scaling: min=<n> max=<n> desired=<n> → <recommendation>
  [✓|~|✗] RDS: <attached/external> <type> → <recommendation>
  [✓|~|✗] .ebextensions: <count> files → <recommendation>
  [✓|~|✗] Health check: <url> <interval> → <recommendation>
COST_IMPACT:
  Current estimated cost: $<amount>/mo
  Optimized estimated cost: $<amount>/mo
  Estimated savings: $<amount>/mo (<percentage>%)
VERIFICATION_COMMANDS:
  aws elasticbeanstalk describe-configuration-settings --environment-name <env-name> --region <region>
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization ...
```

### Worked example — dev environment optimization

```text
EB_ENV: my-dev-app (e-abc123def)
VERDICT: OPTIMIZED
OPTIMIZATIONS:
  [✓] Topology: switched from Load-balanced to Single-instance (instance count: 2 → 1)
  [✓] Instance type: t3.medium → t3.small (avg CPU 12%, well within t3.small capacity)
  [✓] Deployment policy: Immutable → All at Once (dev downtime acceptable, saves 2x deploy cost)
  [✓] NAT Gateway: eliminated (instance has public IP, uses IGW)
  [✓] Auto-scaling: min=2 max=4 desired=2 → min=1 max=1 desired=1 (no scaling for dev)
COST_IMPACT:
  Current estimated cost: $98.73/mo
  Optimized estimated cost: $15.18/mo
  Estimated savings: $83.55/mo (85%)
VERIFICATION_COMMANDS:
  aws elasticbeanstalk describe-configuration-settings --environment-name my-dev-app --region us-east-1
  aws ec2 describe-nat-gateways --filter Name=state,Values=available --region us-east-1
```

### Worked example — production environment with further optimization

```text
EB_ENV: my-prod-app (e-xyz789abc)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
OPTIMIZATIONS:
  [✓] Topology: Load-balanced (correct for production, 3 instances across 2 AZs)
  [✓] Deployment policy: Immutable (correct for zero-downtime production)
  [✓] NAT Gateway: present (correct for production private subnets)
  [✓] Termination protection: enabled (correct for production)
  [~] Instance type: m5.xlarge → t3.large (avg CPU 28%, t3.large sufficient, saves $48/mo)
  [~] Managed updates: disabled → enable minor weekly Sun:04:00 (prevents surprise updates)
  [~] Auto-scaling: min=3 max=10 → min=2 max=6 (avg 3 instances, over-provisioned at night)
  [~] RDS: db.t3.medium attached → db.t4g.medium external (Graviton saves ~$20/mo, external decouples lifecycle)
  [~] .ebextensions: 8 files, 3 have unused resources (cleanup reduces deploy time)
COST_IMPACT:
  Current estimated cost: $412.00/mo
  Optimized estimated cost: $324.00/mo
  Estimated savings: $88.00/mo (21%)
VERIFICATION_COMMANDS:
  aws elasticbeanstalk describe-configuration-settings --environment-name my-prod-app --region us-east-1
  aws cloudwatch get-metric-statistics --namespace AWS/EC2 --metric-name CPUUtilization --dimensions Name=InstanceId,Values=i-xxx --start-time 2026-07-29T00:00:00Z --end-time 2026-08-12T00:00:00Z --period 86400 --statistics Average --region us-east-1
```

## Error handling

### Environment update fails during topology change
- Ensure the instance type is compatible with the new topology. Single-
  instance requires a single instance type; load-balanced requires the
  auto-scaling group config.
- Check IAM permissions for `elasticbeanstalk:UpdateEnvironment`.

### Instance replacement after instance type change
- Changing the instance type triggers instance replacement. For single-
  instance environments, this causes brief downtime. For load-balanced,
  instances are replaced one at a time.

### NAT Gateway deletion leaves instances without internet
- Verify the instance has a public IP and the route table has an IGW
  route for 0.0.0.0/0 BEFORE deleting the NAT Gateway.
- If instances are in a private subnet, move them to a public subnet
  first or keep the NAT Gateway.

### Managed update breaks application
- If a managed update breaks the application, roll back by changing the
  platform version to the previous one.
- Disable managed updates until the compatibility issue is resolved.

## Domain

AWS CloudOps / Elastic Beanstalk Environment Cost & Performance
Optimization.

## AWS documentation

- **Elastic Beanstalk overview** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/Welcome.html
- **Environment types** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.managing.ec2.html
- **Deployment policies** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.rolling-version-deploy.html
- **Managed platform updates** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/environment-platform-update-managed.html
- **Auto-scaling** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.managing.asg.html
- **.ebextensions** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/ebextensions.html
- **Health reporting** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/health-enhanced-status.html
- **RDS with Beanstalk** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/AWSHowTo.RDS.html
- **Environment configuration** — https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/command-options.html
