# Worked Examples — Elastic Beanstalk Environment Optimizer

Secondary worked examples moved verbatim from SKILL.md. Loaded on demand.

## Worked example — production environment with further optimization (from SKILL.md)

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
