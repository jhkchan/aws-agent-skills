# Example usage: rds-cost-optimizer

A walkthrough showing the skill optimising an overprovisioned production
PostgreSQL database, demonstrating the seven-dimension analysis (idle
detection, right-sizing, pricing model, Multi-AZ gating, storage, engine,
Aurora ACU), the FreeableMemory signal, Graviton layering, and RI pricing-
model stacking.

## Input (user prompt)

> Our FinOps review flagged RDS as our #2 cost line. This production Postgres
> database is the biggest contributor. Can you tell me what to do?

```text
DBInstanceIdentifier: db-prod-orders-pg
Engine: postgres (PostgreSQL 15.4)
DBInstanceClass: db.r6i.2xlarge (8 vCPU, 64 GB RAM)
Region: us-east-1
Multi-AZ: true
Storage: 500 GB gp3
License model: postgresql-license (open-source)
Pricing: On-Demand (no RI/Savings Plan)

CloudWatch metrics (last 30 days):
  - CPUUtilization: avg=12%, max=25%
  - FreeableMemory: avg=28 GB (of 64 GB total), stable
  - DatabaseConnections: avg=15, max=30

Performance Insights:
  - DBLoad: avg=2, max=8 (low for 8 vCPUs)
  - Top SQL: evenly distributed, no single dominant query

Workload context: production OLTP database for an e-commerce platform.
Steady-state 24/7 with moderate peak during business hours.
```

## Skill output

```text
TARGET: db-prod-orders-pg
VERDICT: OPPORTUNITY_FOUND
REASON: db.r6i.2xlarge PostgreSQL at 12% CPU / 28 GB FreeableMemory (of 64 GB)
  over 30 days is oversized (Step 2). No RI in place on steady-state production
  database (Step 3). Multi-AZ is correctly enabled for production. Graviton
  path available — PostgreSQL 15.4 fully supports Graviton (Step 2).
RECOMMENDATION:
  Current: postgres db.r6i.2xlarge Multi-AZ 500GB gp3 at On-Demand in us-east-1
  Proposed: postgres db.r6g.large Multi-AZ 500GB gp3 at 3-yr Standard RI in us-east-1
  Dimensions: right-size (r6i.2xlarge → r6g.large), Graviton (x86 → ARM),
    pricing model (On-Demand → 3-yr Standard RI)
  Confidence: HIGH — 30 days of CloudWatch + Performance Insights data, clear
    utilization margins (CPU 12%, Memory 44% used), PostgreSQL 15.4 fully
    Graviton-compatible, DBLoad evenly distributed (no query bottleneck).
ESTIMATED_SAVINGS:
  Monthly (right-size + Graviton): $1,255.60
    - Current: db.r6i.2xlarge Multi-AZ = $2.00 × 2 × 730 = $2,920.00/month
    - Proposed: db.r6g.large Multi-AZ = $0.34 × 2 × 730 = $496.40/month
    - Gross saving: $2,423.60/month
    - Less: cross-check with Cost Explorer baseline (actual spend $2,800/month)
    - Adjusted: ~$1,255.60/month conservatively
  Monthly (pricing model): $297.84
    - 3-yr Standard RI (60% off) on db.r6g.large Multi-AZ:
      $496.40 × 0.60 = $297.84/month additional saving
  Annual total: ~$18,641.00
  Assumptions: 730h/month, us-east-1 On-Demand pricing as of 2026-08-07,
    workload steady-state, PostgreSQL 15.4 Graviton-compatible.
MIGRATION_STEPS:
  1. Take a pre-change manual snapshot (rollback path):
     aws rds create-db-snapshot --db-instance-identifier db-prod-orders-pg
       --db-snapshot-identifier pre-rightsize-$(date +%s)
  2. Modify the instance class (brief restart, Multi-AZ minimises downtime):
     aws rds modify-db-instance --db-instance-identifier db-prod-orders-pg
       --db-instance-class db.r6g.large --apply-immediately
  3. Monitor CPUUtilization and FreeableMemory for 7 days post-change via
     CloudWatch and Performance Insights. Roll back if CPU > 80% or
     FreeableMemory < 20%.
  4. After 7 days of stable operation, purchase a 3-yr Standard RI:
     aws rds describe-reserved-db-instances-offerings
       --db-instance-class db.r6g.large --duration 94608000
       --offering-type "No Upfront" --multi-az
     aws rds purchase-reserved-db-instances-offering
       --reserved-db-instances-offering-id <offering-id>
       --reserved-db-instance-id ri-r6g-large-3yr-prod
  5. Verify RI coverage:
     aws rds describe-reserved-db-instances --status active
CONFIRM: Before modifying the instance class, emit and await:
  "CONFIRM: About to modify-db-instance db-prod-orders-pg to db.r6g.large
   in us-east-1. This causes a brief restart (~2-5 minutes with Multi-AZ
   failover). Proceed? (yes/no)"
  Do NOT run the CLI until the operator confirms.
```

## What the skill caught that a generic assistant misses

1. **FreeableMemory is the right-sizing signal.** A generic assistant says
   "CPU is at 12%, right-size it." The skill confirms FreeableMemory is
   stable at 28 GB (of 64 GB) — meaning the database is using only 36% of
   its memory. Without this data point, a downsize could crash a memory-
   bound database with idle CPU.

2. **Performance Insights DBLoad rules out query-level issues.** The skill
   checks DBLoad (avg=2, max=8 for 8 vCPUs) and confirms no single query
   dominates — meaning the low utilization is a capacity issue, not a
   query-optimisation issue. A generic assistant recommends a downsize
   without checking whether a bad query is masking the real problem.

3. **Graviton layering with engine verification.** The skill confirms
   PostgreSQL 15.4 is Graviton-compatible and recommends db.r6g.large
   (Graviton3, ~20% cheaper than r6i). A generic assistant might recommend
   Graviton without verifying the engine supports it (Oracle and SQL Server
   do NOT).

4. **RI instead of Savings Plan.** A generic assistant might recommend a
   "Savings Plan." The skill knows that RDS does NOT support Compute Savings
   Plans (as of 2026) — only Reserved Instances. Recommending a Savings Plan
   for RDS is a hard error the skill prevents.

5. **Stacking order: right-size first, RI second.** The skill explicitly
   sequences the changes: right-size to db.r6g.large FIRST, verify for 7
   days, THEN purchase the RI for the smaller instance. Stacking both at
   once obscures which change produced the savings.

6. **Multi-AZ kept for production.** A generic assistant might suggest
   disabling Multi-AZ to save more. The skill keeps Multi-AZ because this
   is a customer-facing production database — the HA failover prevents
   customer-visible outages.

7. **Rollback path via snapshot.** The skill creates a manual snapshot
   before the modification. RDS does not support in-place rollback of
   instance-class changes — the snapshot restore is the only recovery path.

## Slash-command invocation

```
/aws:optimize-rds-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "our RDS bill is too high — find the savings"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: rds-cost-optimizer]` and hands off to
this skill for the optimisation block.

## Live-account follow-up (optional, requires AWS CLI)

After applying the right-size, validate the new instance's utilization:

```bash
# Confirm the new instance class landed
aws rds describe-db-instances --db-instance-identifier db-prod-orders-pg \
  --profile default --output json | \
  jq '.DBInstances[0] | {DBInstanceClass, DBInstanceStatus, MultiAZ}'

# Monitor CPU and FreeableMemory for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=db-prod-orders-pg \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value=db-prod-orders-pg \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Minimum --output json

# Confirm RI is covering the new instance
aws rds describe-reserved-db-instances --status active \
  --output json | jq '.ReservedDBInstances[] | {
    ReservedDBInstanceId, DBInstanceClass, State, Duration
  }'
```

If CPU > 80% or FreeableMemory < 20% sustained for 7 days, roll back to
the original db.r6i.2xlarge from the pre-rightsize snapshot.

## Fleet-wide extension

For a fleet of N databases, run the skill in batch mode:

1. Pull all databases via `describe-db-instances`.
2. For each, pull 30-day CloudWatch + Performance Insights.
3. Prioritise by estimated monthly savings (largest first).
4. Slice into batches of 5 databases per operator CONFIRM gate.
5. Process idle-database deletion candidates FIRST (highest leverage).
6. Process right-size + RI candidates SECOND.
7. After the right-size sweep, batch-purchase RIs for the new instance
   classes (billing-account operation, no downtime).
