---
description: Optimize AWS Elastic Beanstalk environments for cost and performance (single-instance vs load-balanced, instance right-sizing, deployment policy selection, NAT Gateway elimination, managed platform update scheduling, auto-scaling tuning, RDS cost optimization). Emits an OPTIMIZED assessment with cost savings estimates.
nl_triggers:
  - "optimize elastic beanstalk"
  - "beanstalk cost optimization"
  - "eb cost"
  - "beanstalk right-size"
  - "single-instance beanstalk"
  - "immutable deployment cost"
  - "managed platform update"
  - "nat gateway elimination"
  - "ebextensions cleanup"
  - "beanstalk auto-scaling"
  - "rds shared cost"
  - "reduce beanstalk cost"
  - "elastic beanstalk optimize"
  - "eb environment optimize"
routes_to: elastic-beanstalk-environment-optimizer
---

# /aws:optimize-beanstalk-env

Activate the `elastic-beanstalk-environment-optimizer` skill and
optimize an Elastic Beanstalk environment for cost and performance.

## What it does

The skill walks the optimization layers and emits an OPTIMIZED or
FURTHER_OPTIMIZATION_AVAILABLE assessment:

1. Instance type right-sizing (based on CPU utilization)
2. Single-instance vs load-balanced topology (dev vs production)
3. t3/t4g burstable instances for dev environments
4. Deployment policy selection (Immutable vs Rolling vs All at Once)
5. Managed platform update scheduling (off-peak maintenance window)
6. .ebextensions optimization (remove unused resources)
7. Auto-scaling policy tuning (capacity and trigger thresholds)
8. NAT Gateway elimination (for single-instance dev/staging)
9. RDS integration cost (shared vs dedicated, Graviton)
10. Health check tuning (reduce false alarms)
11. Termination protection cleanup

## When to use

- You need to reduce Elastic Beanstalk environment costs.
- You want to right-size instance types.
- You are deciding single-instance vs load-balanced.
- You want to eliminate the NAT Gateway for dev.
- You need to tune auto-scaling policies.
- You want to schedule managed platform updates.
- You need to optimize RDS integration costs.
- You want to clean up .ebextensions.

## When NOT to use

- **ECS/EKS optimization** — use container-specific skills.
- **Lambda optimization** — use serverless skills.
- **EC2 Auto Scaling Groups** (non-Beanstalk) — use EC2 skills.
- **Beanstalk deployment troubleshooting** — use deploy skills.

## How to invoke

### Slash command

```
/aws:optimize-beanstalk-env
```

Then provide: environment name, environment ID, current instance
type, topology (single or load-balanced), min/max/desired capacity,
deployment policy, NAT Gateway status, managed updates status,
average CPU utilization, and environment purpose (prod or dev).

### Natural language

Any of these routes to the same skill:

- "optimize my dev beanstalk environment for cost"
- "reduce elastic beanstalk monthly bill"
- "switch beanstalk to single-instance for dev"
- "eliminate NAT gateway for staging beanstalk"
- "right-size beanstalk instances"

### CLI routing

```bash
node cli/bin/cli.js route "optimize elastic beanstalk cost"
```

## Pipeline integration

This skill operates in **Phase 1 (Optimize)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to optimize Elastic
Beanstalk environments. The output assessment feeds into cost
optimization pipelines and downstream audit skills.

## Example

```
You: /aws:optimize-beanstalk-env

     Optimize my dev Elastic Beanstalk environment my-dev-app.
     It's load-balanced with 2x t3.medium instances, an ALB, and
     a NAT Gateway. CPU is only 12%. Brief downtime is fine.

Skill:
  EB_ENV: my-dev-app (e-abc123def)
  VERDICT: OPTIMIZED
  OPTIMIZATIONS:
    [✓] Topology: switched to Single-instance (2 → 1)
    [✓] Instance type: t3.medium → t3.small (CPU 12%)
    [✓] Deployment: Immutable → All at Once
    [✓] NAT Gateway: eliminated (public IP + IGW)
    [✓] Auto-scaling: min=1 max=1 desired=1
  COST_IMPACT:
    Current: ~$98.73/mo
    Optimized: ~$15.18/mo
    Savings: ~$83.55/mo (85%)
  VERIFICATION_COMMANDS:
    aws elasticbeanstalk describe-configuration-settings --environment-name my-dev-app --region us-east-1
    aws ec2 describe-nat-gateways --filter Name=state,Values=available --region us-east-1
```

## References

- Skill definition: `skills/elastic-beanstalk-environment-optimizer/SKILL.md`
- Cost and deployment guide: `skills/elastic-beanstalk-environment-optimizer/references/cost-and-deployment.md`
- Auto-scaling and health guide: `skills/elastic-beanstalk-environment-optimizer/references/autoscaling-and-health.md`
- Eval suite: `skills/elastic-beanstalk-environment-optimizer/evals/evals.json`
