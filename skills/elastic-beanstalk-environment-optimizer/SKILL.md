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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Mindset misconceptions".
> Load when: you need the full numbers behind the topology / immutable-deploy / NAT misconceptions.

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

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Configuration dependency graph".
> Load when: cascading impacts and gotchas of topology, NAT, right-sizing, and update windows.

## Expert heuristic: single-instance savings breakdown

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Expert heuristic: single-instance savings breakdown".
> Load when: computing the actual monthly cost of load-balanced vs single-instance dev.

## Expert heuristic: deployment policy cost analysis

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Expert heuristic: deployment policy cost analysis".
> Load when: comparing deploy policies by downtime and extra deploy-window cost.

## Expert heuristic: managed platform update scheduling

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Expert heuristic: managed platform update scheduling".
> Load when: choosing an update level and a maintenance window.

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

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Opt 1".
> Load when: gathering average CPU over 14 days for the right-sizing heuristic.

**Right-sizing decision matrix:**

| Current type | Avg CPU | Recommended | Savings/mo |
|---|---|---|---|
| t3.medium | < 20% | t3.micro or t3.small | $15-23 |
| t3.large | < 20% | t3.small | $30 |
| m5.large | < 20% | t3.medium | $17 |
| m5.xlarge | < 30% | t3.large or m5.large | $31-62 |
| c5.xlarge | < 30% | t3.medium | $20 |

**Update instance type:**

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 1".
> Load when: applying a right-sized instance type.

## Opt 2 — Single-instance vs load-balanced

The topology choice (single-instance vs load-balanced) is the most
impactful cost optimization for dev/staging environments.

**When to use single-instance:**
> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 2".
> Load when: deciding the topology; full when-to-use criteria for each.

**Switch from load-balanced to single-instance:**

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 2".
> Load when: executing the topology switch to SingleInstance.

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 2".
> Load when: the before/after monthly cost of the topology switch.

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

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 3".
> Load when: applying a t3/t4g burstable instance type.

**Unlimited mode vs standard:** for dev environments, standard burst
mode is sufficient. Unlimited mode charges for CPU credits beyond the
accumulated balance — not worth it for dev.

## Opt 4 — Deployment policy selection

The deployment policy affects both downtime and cost during deploys.

**Check current deployment policy:**

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Opt 4".
> Load when: checking the current deployment policy configuration.

**Change deployment policy:**

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 4".
> Load when: switching between Rolling and Immutable deployment policies.

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 4".
> Load when: the per-deploy cost math and prod/dev policy recommendation.

## Opt 5 — Managed platform update scheduling

Managed platform updates keep the environment on the latest platform
version. Schedule them during off-peak hours to minimize impact.

**Check current managed update config:**

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Opt 5".
> Load when: checking the current managed-update configuration.

**Schedule managed updates during off-peak:**

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 5".
> Load when: enabling managed updates in an off-peak window.

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 5".
> Load when: choosing minor/patch/major update level and the recommended window.

## Opt 6 — .ebextensions optimization

`.ebextensions` files contain YAML configuration that Elastic Beanstalk
applies during environment creation and deployment. Unused or redundant
configurations slow down deployments and can create unnecessary
resources.

**Audit .ebextensions:**

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Opt 6".
> Load when: auditing .ebextensions files for unused resources.

**Common .ebextensions optimizations:**
> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 6".
> Load when: cleaning up unused Resources/files/packages/commands entries.

## Opt 7 — Auto-scaling policy tuning

Auto-scaling policies determine how the environment scales in response
to load. Over-provisioned auto-scaling wastes money; under-provisioned
scales too slowly.

**Check current auto-scaling config:**

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Opt 7".
> Load when: checking current ASG and trigger settings.

**Right-size capacity:**

> **Moved verbatim** → [references/autoscaling-and-health.md](references/autoscaling-and-health.md) § "Opt 7".
> Load when: setting min/max/desired capacity.

**Tune scaling triggers:**

> **Moved verbatim** → [references/autoscaling-and-health.md](references/autoscaling-and-health.md) § "Opt 7".
> Load when: adjusting CPU thresholds and breach duration.

## Opt 8 — NAT Gateway elimination

For single-instance dev/staging environments with a public IP, the NAT
Gateway can be eliminated. The instance accesses the internet via the
Internet Gateway (IGW), which is free.

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 8".
> Load when: the per-AZ NAT Gateway cost math.

**Verify the instance has a public IP before eliminating NAT:**

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Opt 8".
> Load when: verifying the instance has a public IP before NAT removal.

**Eliminate NAT Gateway:**

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 8".
> Load when: deleting the NAT Gateway and repointing the route table.

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

> **Moved verbatim** → [references/cost-and-deployment.md](references/cost-and-deployment.md) § "Opt 9".
> Load when: snapshotting, restoring standalone, and repointing RDS.

## Opt 10 — Health check tuning

Health check tuning reduces false alarms and unnecessary auto-scaling
triggered by overly aggressive health check thresholds.

**Check current health check config:**

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Opt 10".
> Load when: checking the current health reporting configuration.

**Common health check issues:**
> **Moved verbatim** → [references/autoscaling-and-health.md](references/autoscaling-and-health.md) § "Opt 10".
> Load when: diagnosing false health-check failures.

**Tune health check:**

> **Moved verbatim** → [references/autoscaling-and-health.md](references/autoscaling-and-health.md) § "Opt 10".
> Load when: setting the health check path and enhanced reporting.

## Opt 11 — Termination protection cleanup

Termination protection prevents accidental environment deletion. For
production, keep it enabled. For dev/staging that should be torn down
after use, disabling termination protection allows cleanup.

**Check termination protection:**

> **Moved verbatim** → [references/diagnostic-commands.md](references/diagnostic-commands.md) § "Opt 11".
> Load when: checking whether termination protection is enabled.

**Disable for dev cleanup:**

> **Moved verbatim** → [references/autoscaling-and-health.md](references/autoscaling-and-health.md) § "Opt 11".
> Load when: allowing dev/staging environment teardown.

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

> **Moved verbatim** → [references/worked-examples.md](references/worked-examples.md) § "Worked example".
> Load when: emitting a FURTHER_OPTIMIZATION_AVAILABLE assessment for production.

## Error handling

> **Moved verbatim** → [references/error-handling.md](references/error-handling.md) § "Error handling".
> Load when: an update fails, instances lose internet after NAT removal, or a managed update breaks the app.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — FURTHER_OPTIMIZATION_AVAILABLE production assessment example
- [references/error-handling.md](references/error-handling.md) — triage: topology-change failures, instance replacement, NAT removal outages, managed update breakage
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — read-only check commands per Opt (config settings, CPU metrics, public IP, termination protection, .ebextensions audit)
- [references/advanced-patterns.md](references/advanced-patterns.md) — cost misconceptions deep dive, dependency-graph cascades and gotchas
- [references/cost-and-deployment.md](references/cost-and-deployment.md) — cost math, deployment-policy cost analysis, managed-update scheduling, update/detach/NAT-removal commands
- [references/autoscaling-and-health.md](references/autoscaling-and-health.md) — capacity/trigger/health-check tuning commands

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
