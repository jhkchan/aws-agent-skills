---
allowed-tools: Read, Bash, Grep
description: "Optimize Elastic Load Balancer costs — ALB vs NLB vs CLB cost comparison, LCU (Load Balancer Capacity Unit) analysis across four billing dimensions (new connections, active connections, processed bytes, rule evaluations), target group consolidation via multi-path routing, cross-zone load balancing cost impact, idle load balancer detection, CLB-to-ALB/NLB migration savings, data transfer cost via PrivateLink, ALB access log volume reduction, SSL certificate overhead"
nl_triggers:
  - "optimise ELB cost"
  - "ALB LCU analysis"
  - "load balancer cost"
  - "idle load balancer"
  - "CLB to ALB migration cost"
  - "target group consolidation"
  - "multi-path routing"
  - "reduce ALB count"
  - "cross-zone load balancing cost"
  - "LCU dimensions"
  - "ELB FinOps"
  - "reduce load balancer bill"
  - "NLB vs ALB cost"
  - "PrivateLink data transfer"
  - "ALB access log cost"
routes_to: elb-cost-optimizer
---

# /aws:optimize-elb-cost

Activate the `elb-cost-optimizer` skill and optimise Elastic Load
Balancer spend.

## What it does

Reads ELB configurations, CloudWatch LCU metrics, target group details,
and Cost Explorer data, then walks the optimization decision tree
across six dimensions:

1. IDLE_LB — detect and eliminate idle load balancers (RequestCount <
   100/day or zero healthy targets for 7+ days). Each idle ALB wastes
   $16.43+/month.
2. LCU_DIM — analyze the four LCU billing dimensions (new connections,
   active connections, processed bytes, rule evaluations) and reduce
   the peak dimension via keep-alive, compression, timeout tuning, and
   rule simplification.
3. CONSOLIDATION — merge multiple ALBs in the same VPC using host-based
   and path-based routing. Each consolidated ALB saves $16.43+/month.
4. CLB_MIGRATION — migrate Classic Load Balancers to ALB (HTTP) or NLB
   (TCP/UDP) for cost savings and feature gains.
5. DATA_TRANSFER — optimize NLB cross-zone load balancing settings and
   evaluate PrivateLink for inter-VPC traffic reduction.
6. ACCESS_LOGS — apply S3 lifecycle rules to ALB access log storage
   for 70-90% cost reduction.

Emits a deterministic optimization block:

```text
TARGET: <load balancer ARN or name> — <type, region>
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE | OPTIMIZED
REASON: <summary of LCU analysis, idle detection, consolidation opportunities>
RECOMMENDATION:
  1. <IDLE_LB recommendation>
  2. <LCU_DIM recommendation>
  3. <CONSOLIDATION recommendation>
  4. <CLB_MIGRATION recommendation>
  5. <DATA_TRANSFER recommendation>
ESTIMATED_SAVINGS: $<monthly savings> ($<annual savings>)
ACTION_STEPS:
  1. <specific step with AWS CLI or console action>
  2. <verification step>
  3. <rollback step>
```

## When to invoke

Paste any of the following:

- An ALB/NLB/CLB name with LCU metrics or CloudWatch data.
- "My load balancer bill is too high" / "reduce ELB cost".
- An ALB with high LCU consumption.
- Multiple ALBs that might be consolidatable.
- A CLB that should be migrated.
- A FinOps review of networking spend.

A bare load balancer ARN + any optimize/cost verb also routes here.

## Inputs

- Load balancer ARN or name.
- CloudWatch LCU metrics (ConsumedLCUs, per-dimension, 14+ days).
- Listener and target group configuration.
- Monthly ELB spend (from Cost Explorer).

## Outputs

- One optimization block per load balancer or fleet.
- ESTIMATED_SAVINGS with monthly and annual figures.
- ACTION_STEPS with exact AWS CLI commands and verification steps.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for Networking/ELB).
- `/aws:migrate-clb-to-alb` for executing a CLB-to-ALB migration
  (this skill identifies the opportunity; that skill executes it).
- `/aws:troubleshoot-alb-5xx` for ALB 5xx error troubleshooting
  (separate from cost optimization).
