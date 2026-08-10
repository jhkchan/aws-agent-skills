# RDS Cost Optimizer — Worked Examples

## Example 1: Overprovisioned PostgreSQL, no RI, Multi-AZ in production

```text
TARGET: db-overprovisioned-prod
VERDICT: OPPORTUNITY_FOUND
REASON: db.r6i.2xlarge PostgreSQL at 12% CPU / 28 GB FreeableMemory (of 64 GB)
  over 30 days is oversized (Step 2). No RI in place on steady-state production
  database (Step 3). Multi-AZ is correctly enabled for production. Graviton
  path available (Step 2).
RECOMMENDATION:
  Current: postgres db.r6i.2xlarge Multi-AZ 500GB gp3 at On-Demand in us-east-1
  Proposed: postgres db.r6g.large Multi-AZ 500GB gp3 at 3-yr Standard RI in us-east-1
  Dimensions: right-size (r6i.2xlarge -> r6g.large), Graviton (x86 -> ARM),
    pricing model (On-Demand -> 3-yr RI)
  Confidence: HIGH — 30 days of CloudWatch + PI data, clear utilization margins,
    PostgreSQL fully Graviton-compatible.
ESTIMATED_SAVINGS:
  Monthly (right-size + Graviton): $1,255.60 — ($1.20 x 2 x 730) - ($0.34 x 2 x 730) = $1,752.00 - $496.40 = $1,255.60
  Monthly (pricing model): $297.84 — $496.40 x 0.60 (3-yr RI at 60% discount) = $297.84
  Monthly (Multi-AZ): $0.00 (correctly enabled for production — no change)
  Annual total: ~$18,524.00 — ($1,255.60 + $297.84) x 12 = $18,641.28 (adjusted for RI amortisation)
  Assumptions: 730h/month, us-east-1 pricing as of 2026, workload steady-state, PostgreSQL 15+ fully supports Graviton.
MIGRATION_STEPS:
  1. Take a pre-change manual snapshot:
     aws rds create-db-snapshot --db-instance-identifier db-overprovisioned-prod --db-snapshot-identifier pre-rightsize-$(date +%s)
  2. Modify the instance class (brief downtime via Multi-AZ failover):
     aws rds modify-db-instance --db-instance-identifier db-overprovisioned-prod --db-instance-class db.r6g.large --apply-immediately
  3. Monitor CPUUtilization and FreeableMemory for 7 days post-change. Roll back if CPU > 80% or FreeableMemory < 20%.
  4. After 7 days of stable operation, purchase a 3-yr Standard RI:
     aws rds describe-reserved-db-instances-offerings --db-instance-class db.r6g.large --duration 94608000 --offering-type "No Upfront" --multi-az
     aws rds purchase-reserved-db-instances-offering --reserved-db-instances-offering-id <offering-id> --reserved-db-instance-id ri-r6g-large-3yr
  5. Verify RI coverage: aws rds describe-reserved-db-instances --status active
CONFIRM: Before modifying the instance class, emit and await: "CONFIRM: About to modify-db-instance db-overprovisioned-prod to db.r6g.large in us-east-1. Multi-AZ failover causes ~2-5 min downtime. Proceed? (yes/no)"
```

## Example 2: Idle database deletion

```text
TARGET: db-forgotten-feature-db
VERDICT: OPPORTUNITY_FOUND
REASON: Database has 0 connections for 30+ days, CPUUtilization < 1% sustained.
  No Performance Insights data (no queries executing). This is a strong idle-
  database signal (Step 1). The database bills $316/month for zero usage.
RECOMMENDATION:
  Current: mysql db.m6i.large Single-AZ 100GB gp3 at On-Demand
  Proposed: delete (after final snapshot)
  Dimensions: idle database detection (Step 1)
  Confidence: HIGH — 30 days of 0 connections confirmed in CloudWatch.
ESTIMATED_SAVINGS:
  Monthly (idle deletion): $316.00
    - db.m6i.large: $0.38 x 730 = $277.40
    - Storage 100GB gp3: $8.00
    - Total: $285.40 (Cost Explorer shows $316 after tax/fees)
  Annual total: $3,792.00
MIGRATION_STEPS:
  1. Verify with application team that the database is truly unused.
  2. Take a final manual snapshot (retain data for future restore):
     aws rds create-db-snapshot --db-instance-identifier db-forgotten-feature-db
       --db-snapshot-identifier final-snapshot-$(date +%s)
  3. Delete the database:
     aws rds delete-db-instance --db-instance-identifier db-forgotten-feature-db
       --final-db-snapshot-identifier final-snapshot-db-forgotten-feature-db
  4. Verify deletion:
     aws rds describe-db-instances --db-instance-identifier db-forgotten-feature-db
     (should return DBInstanceNotFound)
  5. Review automated snapshots — they will expire per the retention period.
     The final manual snapshot persists until manually deleted.
CONFIRM: Before deleting, emit and await:
  "CONFIRM: About to delete-db-instance db-forgotten-feature-db in us-east-1.
   A final snapshot will be created. The database bills $316/month and has had
   0 connections for 30+ days. Proceed? (yes/no)"
```

## Example 3: Already optimal production database

```text
TARGET: db-prod-orders-db
VERDICT: ALREADY_OPTIMAL
REASON: db.r6g.2xlarge PostgreSQL on a 3-yr Standard RI, CPU 55% avg,
  FreeableMemory 40% avg, Multi-AZ enabled for production, gp3 storage
  correctly sized, no manual snapshot accumulation. All dimensions pass.
RECOMMENDATION: No changes required.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Continue monitoring CloudWatch and Performance Insights
    monthly. Re-evaluate at RI renewal date.
```

## Example 4: Right-size + Reserved Instance (68% saving)

**Database profile:**
- DB Instance: `db-prod-checkout-db`
- Engine: PostgreSQL 15
- Instance class: db.r5.2xlarge (8 vCPU, 64 GB RAM)
- Multi-AZ: Yes (production)
- Storage: 300 GB gp3
- Pricing: On-Demand
- Region: us-east-1

**Metrics (30-day CloudWatch + Performance Insights):**
- CPUUtilization: avg 8%, max 22%
- FreeableMemory: avg 52 GB (of 64 GB = 81% free)
- DatabaseConnections: avg 45, max 80
- Performance Insights DBLoad: avg 0.3, max 1.2 (low for 8 vCPUs)

**Step 1 — Current cost:**
```
Current compute (Multi-AZ On-Demand):
  db.r5.2xlarge: ~$1.027/hour per instance x 2 (Multi-AZ) x 730 hours
  = $1,499.42/month
Current storage: 300 GB gp3 x $0.08/GB = $24.00/month
Current total: $1,523.42/month ($18,281.04/year)
```

**Step 2 — Right-sizing decision tree:**
- CPUUtilization < 20% sustained? YES (8% avg).
- FreeableMemory > 50%? YES (81% free) -> OPPORTUNITY_FOUND (downsize).
- PI DBLoad is low (0.3 avg vs 8 vCPUs) -> confirms not capacity-constrained.

**Step 3 — Target instance class:**
- Current: db.r5.2xlarge (8 vCPU, 64 GB)
- CPU at 8% on 8 vCPUs -> effective usage ~0.64 vCPU
- FreeableMemory 52 GB -> actual usage ~12 GB
- Target: db.r5.large (2 vCPU, 16 GB) — 4x smaller with headroom.

**Step 4 — Pricing model:** 1-year Standard RI (No Upfront) ~40% off.

**Step 5 — Projected cost:**
```
Projected compute (Multi-AZ + 1yr RI):
  db.r5.large On-Demand: ~$0.548/hr x 2 x 730 = $800.08/month
  With 1yr RI (40% off): $800.08 x 0.60 = $480.05/month
Projected storage: $24.00/month (unchanged)
Projected total: $504.05/month ($6,048.60/year)
```

**Step 6 — Savings:** $1,523.42 - $504.05 = $1,019.37/month (66.9%), $12,232.44/year.

**Step 7 — Output block:**
```text
TARGET: db-prod-checkout-db
VERDICT: OPPORTUNITY_FOUND
REASON: db.r5.2xlarge PostgreSQL Multi-AZ at 8% CPU and 81% FreeableMemory
  over 30 days is significantly oversized (Step 2). PI DBLoad confirms the
  workload is not capacity-constrained. Right-sizing to db.r5.large plus a
  1yr Standard RI captures 66.9% monthly saving ($1,019.37/month).
RECOMMENDATION:
  Current: postgres db.r5.2xlarge Multi-AZ 300GB gp3 at On-Demand
  Proposed: postgres db.r5.large Multi-AZ 300GB gp3 at 1yr Standard RI
  Dimensions: right-size (r5.2xlarge to r5.large), pricing model (On-Demand to 1yr RI)
  Confidence: HIGH — 30 days of CloudWatch + PI data, CPU at 8% with 81% free memory.
ESTIMATED_SAVINGS:
  Current monthly: $1,523.42
  Projected monthly: $504.05
  Monthly saving: $1,019.37 (66.9%)
  Annual saving: $12,232.44
MIGRATION_STEPS:
  1. aws rds create-db-snapshot --db-instance-identifier db-prod-checkout-db --db-snapshot-identifier pre-rightsize-$(date +%s)
  2. aws rds modify-db-instance --db-instance-identifier db-prod-checkout-db --db-instance-class db.r5.large --apply-immediately
  3. Monitor CPU/FreeableMemory for 7 days. Roll back if CPU > 80% or FreeableMemory < 20%.
  4. After 7 days stable: purchase 1yr Standard RI for db.r5.large Multi-AZ.
  5. Verify RI coverage: aws rds describe-reserved-db-instances --status active
CONFIRM: "CONFIRM: About to modify-db-instance db-prod-checkout-db to db.r5.large in us-east-1. Multi-AZ failover causes ~2-5 min downtime. Monthly saving $1,019.37 (66.9%). Proceed? (yes/no)"
```
