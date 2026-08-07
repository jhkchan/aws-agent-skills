---
description: Optimises RDS and Aurora database cost through instance-class right-sizing (CloudWatch CPU/FreeableMemory/DatabaseConnections + Performance Insights DBLoad), storage-class selection (gp3 vs io2), Multi-AZ gating by environment, pricing-model evaluation (Reserved Instances, not Savings Plans), engine choice (open-source vs commercial), Aurora Serverless v2 ACU tuning, and idle-database detection. Emits a deterministic VERDICT, recommendation, and estimated monthly savings per database.
nl_triggers:
  - "optimise RDS cost"
  - "right-size RDS instance"
  - "Aurora Serverless v2 ACU"
  - "RDS Multi-AZ cost"
  - "RDS Reserved Instance"
  - "idle database detection"
  - "gp3 vs io2 RDS"
  - "Oracle to PostgreSQL migration"
  - "BYOL vs License-included"
  - "RDS storage autoscaling"
  - "manual snapshot cleanup"
  - "database FinOps review"
  - "Aurora ACU tuning"
  - "RDS downsize recommendation"
  - "reduce RDS bill"
routes_to: rds-cost-optimizer
---

# /aws:optimize-rds-cost

Activate the `rds-cost-optimizer` skill and right-size RDS and Aurora
databases for cost optimisation using the seven-dimension analysis framework.

## What it does

Reads a database's configuration (instance class, engine, Multi-AZ, storage,
pricing model) plus 14-30 day CloudWatch metrics (CPUUtilization,
FreeableMemory, DatabaseConnections) and Performance Insights (DBLoad, top
SQL), then applies the ordered optimisation logic:

1. **Pre-flight** — data sufficiency gate. If CloudWatch or PI data is
   insufficient, emit NEED_MORE_INFO (enable PI, wait 14-30 days).
2. **Idle database detection** — 0 connections for 7+ days → deletion
   candidate (highest single saving).
3. **Instance-class right-sizing** — CPU < 30% + high FreeableMemory +
   low connections → downsize; CPU > 70% or low FreeableMemory → upsize.
4. **Pricing model** — On-Demand → Reserved Instance (Standard or
   Convertible, 1yr/3yr). NOTE: RDS does NOT support Compute Savings Plans
   — recommend RI only.
5. **Multi-AZ gating** — Multi-AZ in non-production → disable (halves
   compute). Keep for production customer-facing databases.
6. **Storage optimisation** — io2 → gp3 (free 3000 IOPS baseline); remove
   unused provisioned IOPS; clean up manual snapshots.
7. **Engine optimisation** — commercial (Oracle/MSSQL) → open-source
   (PostgreSQL/MySQL); BYOL vs License-included.
8. **Aurora Serverless v2 ACU tuning** — min ACU too high → lower to
   baseline; verify genuine scale-down pattern.
9. **Verdict** — OPPORTUNITY_FOUND (any dimension has a recommendation),
   OPTIMIZED (applied and verified), or ALREADY_OPTIMAL (no change needed).

Emits a deterministic optimisation block per database:

```text
TARGET: <db-instance-id or cluster-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <engine> <instance-class> <Multi-AZ> <storage> at <pricing-model>
  Proposed: <engine> <instance-class> <Multi-AZ> <storage> at <pricing-model>
  Dimensions: <list of applicable dimensions>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly (right-size): $<amount>
  Monthly (pricing model): $<amount>
  Monthly (Multi-AZ): $<amount>
  Annual total: $<amount>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a database configuration and ask any of:

- "right-size this RDS instance"
- "is this database oversized?"
- "should I buy an RI for this database?"
- "can I disable Multi-AZ for this staging database?"
- "is this database idle?"
- "should I use Aurora Serverless v2?"
- "is my min ACU too high?"

A bare database ID + any optimise verb ("optimise this database", "reduce
RDS cost") also routes here via the orchestrator.

## Inputs

- Database metadata: instance ID, engine, instance class, Multi-AZ, storage
  type and allocation, pricing model (On-Demand / RI).
- CloudWatch metrics (last 14-30 days):
  - `CPUUtilization` (always available)
  - `FreeableMemory` (required for downsize recommendations)
  - `DatabaseConnections` (idle-database detection)
  - `ACUUtilization` (Aurora Serverless v2 only)
- Performance Insights (optional but HIGH confidence requires it):
  - `DBLoad` average and max
  - Top SQL by load (rules out query-optimisation issues)
- Workload context: production vs dev/test/staging, steady-state vs variable.

## Outputs

- One optimisation block per database.
- Confidence level with rationale (HIGH requires FreeableMemory + PI data +
  clear thresholds).
- Estimated monthly and annual savings, broken down by dimension (right-size,
  pricing model, Multi-AZ, storage).
- Specific migration steps with CLI commands (modify-db-instance for right-
  size, purchase-reserved-db-instances-offering for RI, delete-db-instance
  for idle deletion).
- Rollback path (pre-change snapshot) for production right-sizes.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for database cost).
- `/aws:optimize-ec2-rightsizing` for the compute cost-optimisation sibling
  — EC2 and RDS are typically the two largest compute lines.
- `/aws:audit-rds-instance` for the security and configuration audit of an
  RDS instance (complements this cost-focused optimisation).
