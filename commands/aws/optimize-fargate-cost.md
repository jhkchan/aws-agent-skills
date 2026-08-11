---
allowed-tools: Read, Bash, Grep
description: "Optimize Fargate costs — right-size task definitions (CPU/memory), evaluate Fargate Spot vs On-Demand, ARM64/Graviton migration, capacity provider bin-packing, Savings Plans, and latest features (EFA, instance storage)"
nl_triggers:
  - "optimise Fargate cost"
  - "Fargate right-sizing"
  - "Fargate CPU memory combo"
  - "Fargate Spot savings"
  - "Fargate capacity provider"
  - "Fargate ARM64 Graviton"
  - "Fargate Savings Plans"
  - "Fargate bin-packing"
  - "Fargate task scheduling"
  - "Fargate FinOps"
  - "reduce Fargate bill"
  - "Fargate cost review"
  - "ECS task over-provisioned"
  - "Fargate EFA"
  - "Fargate instance storage"
routes_to: fargate-cost-optimizer
---

# /aws:optimize-fargate-cost

Activate the `fargate-cost-optimizer` skill and optimise Fargate spend.

## What it does

Reads the task definition, CloudWatch metrics (CPUUtilization,
MemoryUtilization), capacity provider strategy, and Cost Explorer data,
then walks the optimization decision tree across five dimensions:

1. RIGHT_SIZE — CPU/memory combination downsizing from the 28 allowed
   combos (CloudWatch CPUUtilization < 50% and MemoryUtilization < 60%
   signal over-provisioning).
2. SPOT — Fargate Spot capacity provider for fault-tolerant, stateless,
   or retriable workloads (up to 70% savings).
3. ARM64 — Graviton migration for compatible runtimes (Java 11+,
   Python, Node.js, Go, .NET 6+) — ~20% cheaper per vCPU/GB-hour.
4. SCHEDULING — bin-packing via capacity providers, auto scaling on
   CPU target tracking, deployment minimumHealthyPercent tuning.
5. SAVINGS_PLANS — Compute Savings Plans for steady-state 24/7
   workloads (20-48% discount, applies to Fargate + EC2 + Lambda).

Emits a deterministic optimization block:

```text
TARGET: <task-definition>:<revision> (service <service> on cluster <cluster>)
VERDICT: OPPORTUNITY_FOUND | OPTIMIZED | ALREADY_OPTIMAL
REASON: <summary of findings across dimensions>
RECOMMENDATION:
  1. <RIGHT_SIZE recommendation with old → new combo>
  2. <SPOT recommendation with capacity provider strategy>
  3. <ARM64 recommendation if applicable>
  4. <SCHEDULING recommendation if applicable>
  5. <SAVINGS_PLANS recommendation if applicable>
ESTIMATED_SAVINGS: $<monthly savings> ($<annual savings>)
MIGRATION_STEPS:
  1. <specific step with AWS CLI or console action>
  2. <verification step>
  3. <rollback step>
```

## When to invoke

Paste any of the following:

- A task definition and CloudWatch metrics for a Fargate service.
- "My Fargate bill is too high" / "reduce Fargate cost".
- An ECS task that is over-provisioned (low CPU/memory utilization).
- A workload to evaluate for Fargate Spot or ARM64 migration.
- A FinOps review of container spend.

A bare task definition ARN + any optimize/cost verb also routes here.

## Inputs

- Task definition ARN or name:revision.
- CloudWatch CPUUtilization and MemoryUtilization (14+ days).
- Capacity provider strategy (if any).
- Monthly Fargate spend (from Cost Explorer).
- Workload characteristics (stateless/stateful, fault-tolerant, 24/7).

## Outputs

- One optimization block per task definition or service.
- ESTIMATED_SAVINGS with monthly and annual figures.
- MIGRATION_STEPS with exact AWS CLI commands and verification steps.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 3 Optimize specialist for Compute/Fargate).
- `/aws:troubleshoot-ecs-task` for ECS task failures (separate from
  cost optimization).
- `/aws:audit-ecs-task-definition` for task definition security/config
  audits.
