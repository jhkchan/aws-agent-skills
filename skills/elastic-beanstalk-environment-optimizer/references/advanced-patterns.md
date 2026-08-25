# Advanced Patterns — Elastic Beanstalk Environment Optimizer

Misconception analysis and dependency-graph deep dives moved verbatim from SKILL.md. Loaded on demand.

## Mindset misconceptions — full cost reasoning (from SKILL.md § Mindset)

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

## Configuration dependency graph — deep-dive notes (from SKILL.md)

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
