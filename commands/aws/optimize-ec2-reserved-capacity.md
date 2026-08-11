---
allowed-tools: Read, Bash, Grep
description: "Optimize EC2 Reserved Instance and Savings Plans commitments — RI utilization analysis, coverage gap detection, Standard vs Convertible RI, 1yr vs 3yr term trade-offs, upfront vs no-upfront payment, Compute SP vs EC2 Instance SP vs SageMaker SP, Cost Explorer recommendation harvesting, RI Marketplace selling, CloudWatch/Budgets utilization alerts"
nl_triggers:
  - "optimise Reserved Instances"
  - "RI utilization"
  - "RI coverage"
  - "Savings Plans optimization"
  - "Standard vs Convertible RI"
  - "1-year vs 3-year commitment"
  - "upfront vs no upfront"
  - "Compute Savings Plans"
  - "EC2 Instance Savings Plans"
  - "RI marketplace sell"
  - "commitment management"
  - "FinOps commitment review"
  - "reduce EC2 commitment waste"
  - "RI underutilized"
  - "on-demand coverage gap"
routes_to: ec2-reserved-capacity-optimizer
---

# /aws:optimize-ec2-reserved-capacity

Activate the `ec2-reserved-capacity-optimizer` skill and optimise EC2
Reserved Instance and Savings Plans commitments.

## What it does

Reads RI/SP utilization, coverage reports, EC2 fleet inventory, and
Cost Explorer data, then walks the commitment optimization decision
tree across five dimensions:

1. COVERAGE_GAP — identify on-demand spend eligible for commitment
   (RI/SP coverage < 80% of steady-state hours).
2. UTILIZATION_GAP — identify underused RIs/SPs (RI utilization < 90%
   or SP utilization < 95%).
3. TERM_EVAL — 1-year vs 3-year trade-off based on workload stability
   (90-day minimum, migration plans, deprecation horizon).
4. PAYMENT_EVAL — upfront vs no-upfront breakeven analysis (All
   Upfront maximizes discount; No Upfront preserves capital).
5. VEHICLE_EVAL — Standard RI vs Convertible RI vs Compute SP vs EC2
   Instance SP based on workload flexibility needs.

Emits a deterministic optimization block:

```text
TARGET: <account/fleet> — <instance family or SP scope>
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE | OPTIMIZED
REASON: <summary of utilization, coverage, and commitment gaps>
RECOMMENDATION:
  1. <COVERAGE_GAP recommendation>
  2. <UTILIZATION_GAP recommendation>
  3. <TERM_EVAL recommendation>
  4. <PAYMENT_EVAL recommendation>
  5. <VEHICLE_EVAL recommendation>
ESTIMATED_SAVINGS: $<monthly savings> ($<annual savings>)
ACTION_STEPS:
  1. <specific step with AWS CLI or console action>
  2. <verification step>
  3. <rollback / hedging step>
```

## When to invoke

Paste any of the following:

- An RI/SP utilization or coverage report.
- "My RI utilization is low" / "my RI coverage is poor".
- An EC2 fleet summary and a question about commitment strategy.
- A workload change (migration, right-sizing) that affects existing RIs.
- A FinOps commitment review or quarterly RI/SP audit.

A bare account ID + any commitment/RI/SP verb also routes here.

## Inputs

- RI/SP utilization and coverage data (Cost Explorer, 30+ days).
- EC2 fleet instance-type distribution (describe-instances).
- Monthly on-demand EC2 spend (Cost Explorer).
- Workload stability context (migration plans, fleet changes).

## Outputs

- One optimization block per fleet or commitment scope.
- ESTIMATED_SAVINGS with monthly and annual figures.
- ACTION_STEPS with exact AWS CLI commands and verification steps.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for Compute commitment management).
- `/aws:optimize-ec2-rightsizing` for EC2 instance right-sizing
  (separate from commitment optimization).
- `/aws:optimize-fargate-cost` for Fargate cost optimization
  (Compute SP also covers Fargate spend).
