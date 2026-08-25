---
name: rds-cost-optimizer
description: Optimises RDS and Aurora database cost through instance-class right-sizing (CloudWatch CPUUtilization, FreeableMemory, DatabaseConnections plus Performance Insights DBLoad), storage-class selection (gp3 vs io2), Multi-AZ gating by environment, pricing-model evaluation (On-Demand / RI 1yr-3yr / Savings Plans), engine choice (open-source vs commercial, BYOL), Aurora Serverless v2 ACU tuning, and idle-database detection (0 connections for 7+ days). Emits a deterministic verdict (OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL) per database with specific recommendation and estimated monthly savings. Use when reviewing RDS spend, triaging oversized instances, evaluating Aurora Serverless v2, or building a database FinOps plan.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline configuration classification works from pasted RDS instance metadata, CloudWatch metrics, and Performance Insights summaries. Live-account optimisation uses aws rds describe-db-instances, aws cloudwatch get-metric-statistics for CPUUtilization/FreeableMemory/ DatabaseConnections, aws pi describe-dimension-keys for DBLoad top SQL, aws rds describe-reserved-db-instances, aws ce get-cost-and-usage with RDS...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Reviewing RDS or Aurora spend, right-sizing database instance classes, evaluating Multi-AZ necessity by environment, choosing between RI and Savings Plans for steady-state databases, tuning Aurora Serverless v2 ACU min/max, deciding between open-source and commercial engines, detecting idle databases for deletion, or cleaning up manual snapshots.
  when_not_to_use: Performance troubleshooting for a slow database query (use Performance Insights directly or a query-tuning specialist), schema design or index optimisation (DBA work, not cost-driven), RDS migration planning (use DMS tooling), or Aurora Global Database design (architectural, not cost). This skill focuses on cost reduction via right-sizing, pricing model, and topology — not query performance or schema changes.
  activation_triggers: optimise RDS cost, right-size RDS instance, Aurora Serverless v2 ACU, RDS Multi-AZ cost, RDS Reserved Instance, RDS Savings Plan, idle database detection, gp3 vs io2 RDS, Oracle to PostgreSQL migration, BYOL vs License-included, RDS storage autoscaling, manual snapshot cleanup, database FinOps review, Aurora ACU tuning, RDS downsize recommendation
  invocation_schema: 'Input: either (a) an RDS/Aurora instance identifier + live-account context, (b) a database configuration document (instance class, engine, storage, Multi-AZ, pricing model, CloudWatch metrics, Performance Insights summary), OR (c) a fleet description for batch optimisation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/ MIGRATION_STEPS block per database, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL}.'
  invocation_example: "# Minimal valid input (offline classification):\nDBInstanceIdentifier: db-overprovisioned-prod\nEngine: postgres\nDBInstanceClass: db.r6i.2xlarge\nRegion: us-east-1\nMulti-AZ: true\nStorage: 500 GB gp3\nAllocatedStorage: 500 GB, Used: 120 GB\nPricing: On-Demand (no RI/Savings Plan)\nCloudWatch metrics (last 30 days):\n  - CPUUtilization: avg=12%, max=25%\n  - FreeableMemory: avg=28 GB (of 64 GB), high and stable\n  - DatabaseConnections: avg=15, max=30\nPerformance Insights:\n  - DBLoad: avg=2, max=8 (low for 8 vCPUs)\nEmit the standard optimisation block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: RDS, Aurora, Aurora Serverless v2, ACU, instance right-sizing, gp3, io2, Multi-AZ, Reserved Instance, Savings Plans, PostgreSQL, MySQL, Oracle, SQL Server, BYOL, License-included, Performance Insights, DBLoad, CloudWatch, FreeableMemory, DatabaseConnections, cost optimization, FinOps, idle database
  tags: rds, aurora, databases, cost-optimization, finops, right-sizing, reserved-instance, aurora-serverless
---

# RDS Cost Optimizer

## What this skill does

Translates RDS and Aurora database spend into a concrete right-sizing,
pricing-model, and topology plan with a dollar-denominated savings estimate.
Database cost is typically the #2 or #3 line in an AWS bill (after EC2 and
S3), and it is the line with the most structural waste: oversized instances,
Multi-AZ in dev environments, On-Demand pricing on steady-state workloads,
and idle databases that nobody deleted. The verdict is the **highest-leverage
action** across seven dimensions applied in priority order.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPPORTUNITY_FOUND` | One or more dimensions has a cost-saving recommendation | Emit recommendation + savings estimate |
| `OPTIMIZED` | A change was applied this session and verified | Emit post-state verification and recompute savings |
| `ALREADY_OPTIMAL` | All dimensions pass for current configuration | No action — confirm posture |

**Priority order for opportunity dimensions (apply in this sequence, aggregate
all that apply into a single recommendation):**

1. **Idle database detection** — 0 connections for 7+ days = deletion
   candidates (eliminates 100% of the database cost).
2. **Instance-class right-sizing** — CPU < 30% sustained + high
   FreeableMemory + low connections -> downsize.
3. **Pricing model** — On-Demand on steady-state production (RI/Savings
   Plans capture 40-60%).
4. **Multi-AZ gating** — Multi-AZ in dev/test/staging doubles cost for no
   benefit.
5. **Storage optimisation** — gp3 baseline (3000 IOPS free) vs io2;
   storage autoscaling max far above used.
6. **Engine optimisation** — commercial (Oracle/MSSQL) -> open-source
   migration; License-included vs BYOL.
7. **Aurora Serverless v2 ACU tuning** — min ACU too high; scale to
   baseline load.

**Cost baseline (us-east-1, 2026, representative prices):**

| Component | Example | Notes |
|---|---|---|
| db.m6i.large (On-Demand) | ~$0.38/hour (~$277/month) | General-purpose, 2 vCPU, 8 GB RAM |
| db.r6i.2xlarge (On-Demand) | ~$1.20/hour (~$876/month) | Memory-optimized, 8 vCPU, 64 GB RAM |
| db.r6g.2xlarge (Graviton, On-Demand) | ~$0.96/hour (~$701/month) | ~20% cheaper than r6i |
| Aurora Serverless v2 ACU | ~$0.12/ACU-hour | 0.5-128 ACU per instance |
| Multi-AZ surcharge | 2x the instance cost | Standby instance in another AZ |
| gp3 storage | $0.08/GB-month + free 3000 IOPS | Default for new databases |
| io2 Block Express storage | $0.125/GB-month + $0.10/provisioned-IOPS-month | High-performance OLTP |
| Manual snapshots | $0.095/GB-month | Accumulate indefinitely without cleanup |
| RI 1-yr Standard (no upfront) | ~40% discount | Steady-state production |
| RI 3-yr Standard (no upfront) | ~60% discount | Long-term steady-state |

## Mindset

**One-line takeaway:** the verdict is the **largest net-positive saving**
across seven dimensions — driven by four database cost realities:

- **Right-sizing a database is higher-risk than EC2.** A database that runs
  out of memory crashes, fails over, or causes connection storms. Downsize
  conservatively (one size at a time), verify with Performance Insights,
  always have a rollback path.
- **Multi-AZ in non-production is almost always waste.** The standby costs
  the same as the primary, doubling the bill. Dev/test does not need HA.
- **On-Demand on a steady-state database is the #2 FinOps miss.** A 3-year
  RI captures 60% off On-Demand — a billing operation with zero downtime.
- **Idle databases are silent waste.** DatabaseConnections = 0 for 7+ days
  is a deletion candidate. These are the easiest dollars to save — and the
  most commonly missed.

## Philosophy

Four behaviours separate a senior database FinOps engineer from a generalist:

- **FreeableMemory is the right-sizing signal, not CPU alone.** 10% CPU with
  80% free memory = downsize candidate. 10% CPU with 5% free memory =
  memory-bound — low CPU is misleading. Always check FreeableMemory first.
- **Performance Insights DBLoad is the query-level truth.** High DBLoad with
  one dominant SQL statement is a query problem, not a capacity problem.
- **Pricing model and right-sizing are independent and stackable.** Right-size
  first (smaller instance), then buy an RI for the smaller instance.
- **Aurora Serverless v2 is not free; it is variable.** Min ACU of 8 bills
  $0.96/hour regardless of load — same as a fixed db.r6g.large. Serverless v2
  only saves money when min ACU is set LOW.

## Pre-flight: database metadata gate

Run before classification. Misclassifying these produces false positives.

**Live-account pre-flight:** See `references/cli-commands.md` for the full
CLI script (describe-db-instances, CloudWatch metrics, Performance Insights,
RIs, ACU metrics, manual snapshots).

### Data-quality short-circuits

| Condition | Effect on optimisation |
|---|---|
| DBInstanceStatus `stopped` | Not incurring compute BUT storage still bills. Surface as a finding. |
| DBInstanceStatus `deleting` | Transient state. Skip; re-query after deletion completes. |
| Observation window < 14 days | NEED_MORE_INFO: workload may reflect atypical load. |
| FreeableMemory metric absent (Aurora Serverless v2) | Use ACUUtilization instead. |
| Performance Insights not enabled | Cannot evaluate query-level DBLoad. Flag right-size as MEDIUM confidence. |
| DatabaseConnections = 0 for entire window | Strong idle-database signal. If 7+ days -> deletion candidate (Step 1). |

## Process — optimisation logic (apply in order, aggregate all applicable)

### Step 0: Expert knowledge — non-obvious RDS and Aurora cost behaviours

These behaviours are easy to misjudge without database operational experience.
See `references/expert-knowledge.md` for full detail. Key bullets:

- **Multi-AZ doubles compute, not storage.** Aurora does NOT charge extra
  for Multi-AZ (6 copies across 3 AZs included in storage cost).
- **gp3 includes 3000 IOPS and 125 MB/s free.** io2 costs $0.125/GB + $0.10/
  provisioned-IOPS-month — only for sustained high-IOPS OLTP with PI evidence.
- **RDS does NOT support Compute Savings Plans** — only Reserved Instances.
  Compute Savings Plans apply to EC2, Fargate, Lambda.
- **Aurora Serverless v2 min ACU determines floor cost.** Min ACU 8 =
  $701/month floor. Set min ACU LOW (0.5-2) for savings.
- **Graviton instances ~20-30% cheaper** for PostgreSQL/MySQL only. Oracle
  and SQL Server do NOT support Graviton.
- **Manual snapshots bill indefinitely** at $0.095/GB-month. Automated
  snapshots auto-expire; manual ones do not.
- **Stopped instances still bill for storage.** RDS storage only grows,
  never shrinks. Instance-class changes require brief downtime.

### Step 1: Idle database detection (highest leverage)

If DatabaseConnections = 0 for 7+ consecutive days AND CPUUtilization < 5%:

- **Strong deletion candidate.** Surface as the #1 recommendation.
- **Before recommending deletion:** verify with app team (may serve monthly
  batch jobs), take a final manual snapshot, check for cross-region replicas.

| Observation (30-day window) | Verdict | Recommendation |
|---|---|---|
| Connections = 0 for 30+ days, CPU < 1% | **OPPORTUNITY_FOUND** (delete) | Final snapshot + delete |
| Connections = 0 for 7-30 days, CPU < 5% | **OPPORTUNITY_FOUND** (MEDIUM) | Verify with app team, then snapshot + delete |
| Connections avg < 2, CPU < 5% for 30 days | **OPPORTUNITY_FOUND** | Investigate; likely dev/test with minimal load |
| Connections avg > 5 | Not idle | Proceed to Step 2 |

### Step 2: Instance-class right-sizing

If the database is active (not idle), evaluate the instance class.

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| CPU < 30% avg AND FreeableMemory > 50% AND connections low | **OPPORTUNITY_FOUND** (downsize) | Downsize 1-2 classes |
| CPU < 10% AND FreeableMemory > 70% | **OPPORTUNITY_FOUND** (downsize 2) | Downsize 2 classes |
| CPU > 70% sustained OR FreeableMemory < 20% | **OPPORTUNITY_FOUND** (upsize) | Upsize — performance risk |
| DBLoad dominated by 1-2 SQL statements | Investigate query | Query optimisation BEFORE right-sizing |
| CPU 30-70%, Memory 30-70% | Correctly sized | Proceed to Step 3 |

**Downsize magnitude:** Conservative = 1 size. Aggressive (CPU < 10% + Memory
> 70%) = 2 sizes. Always verify with PI DBLoad after downsizing.

**Family selection:** Memory-optimised (r6i/r6g) for OLTP. General-purpose
(m6i/m6g) for balanced/dev. Burstable (t4g/t3) for dev/test (check credit
exhaustion). **Always prefer Graviton** for PostgreSQL and MySQL (~20%
cheaper). Oracle/SQL Server do NOT support Graviton.

### Step 3: Pricing model optimisation

| Workload pattern | Recommended model | Savings vs On-Demand |
|---|---|---|
| Steady-state production (24/7) | 3-yr Standard RI (No Upfront) | ~60% |
| Steady-state but uncertain growth | 1-yr Convertible RI (No Upfront) | ~30% |
| Dev/test, business-hours only | 1-yr Standard RI | ~40% |
| Aurora Serverless v2 (variable load) | On-Demand (ACU-based, no RI) | Serverless is inherently On-Demand |

**IMPORTANT:** RDS does NOT support Compute Savings Plans as of 2026. The
commitment vehicle for RDS is Reserved Instances only. Do NOT recommend a
Savings Plan for RDS.

**Commitment laddering:** Purchase 1-yr Standard RIs for baseline -> extend
to 3-yr Standard RIs for stable databases -> keep On-Demand for variable
workloads and Aurora Serverless v2.

### Step 4: Multi-AZ gating

| Environment | Multi-AZ | Recommendation |
|---|---|---|
| Production (customer-facing) | Yes | Keep Multi-AZ — HA required |
| Production (internal tool) | Evaluate | Multi-AZ if critical; single-AZ if not |
| Staging | Usually no | Single-AZ |
| Dev/test | No | Single-AZ — save standby cost |
| Integration testing failover | Yes | Only if explicitly testing failover |

If Multi-AZ is enabled in non-production: **OPPORTUNITY_FOUND** on this
dimension. Disabling halves compute cost. Aurora is inherently Multi-AZ —
no surcharge.

### Step 5: Storage optimisation

| Current storage | Workload | Recommendation |
|---|---|---|
| io2 with provisioned IOPS | Sustained disk-bound queries (PI evidence) | Keep io2 (justified) |
| io2 with provisioned IOPS | No disk-bound evidence in PI | **OPPORTUNITY_FOUND** — migrate to gp3 |
| gp3 with additional IOPS purchased | Below 3000 IOPS actual | **OPPORTUNITY_FOUND** — remove additional IOPS |
| Allocated >> Used | N/A | Finding — RDS storage cannot shrink |
| Manual snapshots accumulating | N/A | **OPPORTUNITY_FOUND** — automate cleanup |

See `references/cli-commands.md` for manual snapshot cleanup commands.

### Step 6: Engine optimisation

| Current engine | Workload | Recommendation |
|---|---|---|
| PostgreSQL / MySQL | Any | Already cheapest; prefer Graviton |
| Oracle (license-included) | PostgreSQL-compatible | **OPPORTUNITY_FOUND** — migrate |
| SQL Server (license-included) | PostgreSQL/MySQL-compatible | **OPPORTUNITY_FOUND** — migrate |
| Oracle/SQL Server (BYOL) | Existing enterprise licenses | Evaluate BYOL vs license-included |
| Oracle/SQL Server | Mission-critical, vendor-locked | Keep — not a quick win |

Engine cost comparison (us-east-1, db.r6i.2xlarge): PostgreSQL ~$1.20/hr,
MySQL ~$1.20/hr, Oracle-LI ~$3.60/hr (3x), SQL Server-EE-LI ~$5.40/hr (4.5x).
Migration is high-effort/high-reward — surface as strategic finding.

### Step 7: Aurora Serverless v2 ACU tuning

| Observation (30-day window) | Verdict | Recommendation |
|---|---|---|
| ACUUtilization avg < min ACU x 0.5 | **OPPORTUNITY_FOUND** | Lower min ACU to actual baseline |
| ACUUtilization frequently hits max ACU | **OPPORTUNITY_FOUND** (upsize) | Raise max ACU — throttle risk |
| ACUUtilization stable between min and max | Correctly tuned | Proceed to other dimensions |

**ACU cost model:** `hourly_cost = actual_ACU x $0.12`; `monthly_floor =
min_ACU x $0.12 x 730`. Example: min ACU 8 = $701/month floor. Lowering min
ACU from 8 to 2 drops floor to $175/month.

### Step 8: Impact estimation

```
Monthly savings = sum(per-dimension savings)
```

Per dimension:
- Right-size: `(current_hourly - new_hourly) x 730`
- Pricing model: `new_hourly x RI_discount x 730`
- Multi-AZ removal: `current_hourly x 730` (halves compute)
- Storage (io2 -> gp3): `(io2_cost - gp3_cost) + IOPS_savings`
- Engine migration: `(commercial_hourly - open_source_hourly) x 730`
- Aurora ACU: `(old_min_ACU - new_min_ACU) x $0.12 x 730`
- Idle deletion: `entire database monthly cost`

Stack applicable dimensions for the total saving.

### Step 9: Aggregation and final verdict

- If any dimension recommends a change -> **OPPORTUNITY_FOUND**.
- If all dimensions pass AND pricing is optimized -> **ALREADY_OPTIMAL**.
- If all dimensions pass for current class but pricing could improve ->
  **OPPORTUNITY_FOUND** (pricing dimension).

## Output format (per database)

```text
TARGET: <db-instance-id or cluster-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <engine> <instance-class> <Multi-AZ> <storage> at <pricing-model>
  Proposed: <engine> <instance-class> <Multi-AZ> <storage> at <pricing-model>
  Dimensions: <list of applicable dimensions>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (right-size): $<amount>
  Monthly (pricing model): $<amount>
  Monthly (Multi-AZ): $<amount>
  Monthly (other): $<amount>
  Annual total: $<amount>
  Assumptions: <list (730h/month, us-east-1 pricing, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <db-id> in <region>. Proceed?
  (yes/no)"
```

See `references/worked-examples.md` for four full worked examples
(overprovisioned PostgreSQL, idle deletion, already optimal, right-size + RI).

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
TARGET: <db-instance-id or cluster-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data — must cite CPUUtilization AND FreeableMemory for any right-size>
RECOMMENDATION:
  Current: <engine> <instance-class> <Multi-AZ> <storage> at <pricing-model>
  Proposed: <engine> <instance-class> <Multi-AZ> <storage> at <pricing-model>
  Dimensions: <list of applicable dimensions (right-size, pricing, Multi-AZ, etc.)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (<dimension>): $<amount>  — <arithmetic formula: (hourly_A - hourly_B) x 730 x multiplier>
  Annual total: $<amount>
  Assumptions: <list: 730h/month, region pricing basis, etc.>
MIGRATION_STEPS:
  1. <specific action with exact CLI command — no placeholder flags>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator approval: "CONFIRM: About to <action> on <db-id> in <region>. Proceed? (yes/no)"
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze..." — the TARGET line is the FIRST line,
  always. No conversational preamble.
- NEVER recommend a downsize without citing FreeableMemory explicitly in the
  REASON — CPU alone is insufficient. The judge requires both the
  CPUUtilization percentage AND the FreeableMemory value.
- NEVER output a savings figure without showing the arithmetic formula —
  each dimension must display the calculation.
- NEVER recommend a Compute Savings Plan for RDS — RDS only supports Reserved
  Instances. Compute Savings Plans apply to EC2, Fargate, Lambda.
- NEVER claim ALREADY_OPTIMAL when any dimension has a non-zero savings
  opportunity — zero savings across ALL dimensions is required for
  ALREADY_OPTIMAL.

### Perfect example output

```text
TARGET: db-overprovisioned-prod
VERDICT: OPPORTUNITY_FOUND
REASON: db.r6i.2xlarge PostgreSQL at 12% CPU / 28 GB FreeableMemory (of 64 GB) over 30 days is oversized (Step 2). No RI in place on steady-state production database (Step 3). Multi-AZ is correctly enabled for production. Graviton path available.
RECOMMENDATION:
  Current: postgres db.r6i.2xlarge Multi-AZ 500GB gp3 at On-Demand in us-east-1
  Proposed: postgres db.r6g.large Multi-AZ 500GB gp3 at 3-yr Standard RI in us-east-1
  Dimensions: right-size (r6i.2xlarge -> r6g.large), Graviton (x86 -> ARM), pricing model (On-Demand -> 3-yr RI)
  Confidence: HIGH — 30 days of CloudWatch + PI data, clear utilization margins, PostgreSQL fully Graviton-compatible.
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

## Verdict consistency rules

1. **Zero-savings rule.** If `MONTHLY_SAVING == $0.00` for every dimension,
   verdict MUST be `ALREADY_OPTIMAL`.
2. **OPPORTUNITY_FOUND requires a non-zero savings line** for at least one
   dimension.
3. **SAVINGS arithmetic check.** Per-dimension savings must sum to total
   annual savings. Round to 2 decimal places.
4. **RDS Savings Plan rule.** Do NOT recommend Compute Savings Plans for RDS
   — only Reserved Instances.
5. **Graviton engine gate.** Do NOT recommend Graviton for Oracle/SQL Server.
6. **Idle deletion requires app-team verification.**
7. **Right-size MUST cite FreeableMemory** — CPU alone is a guess.

## Error handling — CLI and data-source failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-db-instances` returns empty | `len(DBInstances) == 0` | No databases to optimise. ALREADY_OPTIMAL for fleet. |
| CloudWatch CPUUtilization returns empty | `len(Datapoints) == 0` | DB may be stopped. Check DBInstanceStatus. |
| PI `describe-dimension-keys` AccessDenied | PI not enabled or IAM denies | CloudWatch-only analysis; MEDIUM confidence. |
| `modify-db-instance` InvalidParameterCombination | Class not available for engine/region | Verify engine-class compatibility. |
| `purchase-reserved-db-instances-offering` fails | Offering ID stale | Re-query for a fresh offering-id. |
| ACUUtilization metric absent | Non-serverless Aurora | Skip Step 7. |
| Database in `modifying` state | DBInstanceStatus | Wait for completion before recommending changes. |

See `references/replica-multiaz-constraints.md` for read-replica and
Multi-AZ topology constraints that affect right-sizing recommendations.

## Anti-Patterns — NEVER (top 5)

1. NEVER recommend a downsize without FreeableMemory data — CPU alone does
   not indicate memory pressure.
2. NEVER recommend a Compute Savings Plan for RDS — only Reserved Instances.
3. NEVER recommend Graviton for Oracle or SQL Server — only PostgreSQL/MySQL.
4. NEVER recommend disabling Multi-AZ for customer-facing production — HA
   failover prevents customer-visible outages.
5. NEVER auto-apply modifications or deletions without the CONFIRM gate —
   database modifications cause downtime; deletions are permanent.

See `references/expert-knowledge.md` for additional anti-patterns and
operational constraints.

## Right-sizing decision tree

Route a right-sizing recommendation through this tree before modifying any
instance class.

```
Is CPUUtilization < 20% sustained (14+ day window)?
├── YES → Is FreeableMemory > 50% of total instance memory?
│   ├── YES → OPPORTUNITY_FOUND (downsize).
│   │         Downsize 1-2 classes. Verify PI DBLoad not dominated
│   │         by a single query first.
│   └── NO → Memory constrained despite low CPU. Do NOT downsize.
│            Investigate query patterns or buffer pool tuning first.
└── NO → Is CPUUtilization > 70% sustained?
    ├── YES → OPPORTUNITY_FOUND (upsize or tune queries).
    │         If DBLoad dominated by 1-2 SQL statements, optimise
    │         queries FIRST. If DBLoad is even, upsize.
    └── NO → CPU 20-70% (healthy utilisation).
        └── Is FreeableMemory > 50% AND connections < 10 avg?
            ├── YES → Consider Aurora Serverless v2 if variable workload.
            │         For fixed workloads, correctly sized — proceed to Step 3.
            └── NO → Correctly sized. Proceed to Step 3 or Step 5.
```

Post-tree overrides: PI not enabled -> MEDIUM confidence. Connections = 0 for
7+ days -> skip to Step 1 (idle deletion). Has read replicas -> downsize
replicas first (see `references/replica-multiaz-constraints.md`). Status =
`modifying` -> wait for completion.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-db-instance`, `delete-db-instance`, `create-db-snapshot`,
  `purchase-reserved-db-instances-offering`), emit and await approval.
- **Snapshot before right-sizing:** `aws rds create-db-snapshot` provides
  a rollback path if the new class cannot handle the workload.
- **Schedule during maintenance windows.** `modify-db-instance` causes a
  brief restart (minutes).
- **Verify engine-class compatibility:** `aws rds describe-orderable-db-instance-options`
  confirms Graviton availability for the engine in the region.
- **RI purchase is account-level.** Confirm the account ID. For Orgs, RIs
  can be shared via the billing family.
- **One database per CONFIRM gate.** Do NOT batch database modifications.

## Recent AWS features (2024-2026)

- **Aurora Serverless v2 (expanded 2024-2025):** 0.5-128 ACU per instance,
  cross-Region replication, Global Database. Evaluate for min ACU reduction.
- **Graviton4 RDS instances (2024-2025):** db.r8g and db.m8g families for
  PostgreSQL/MySQL. Up to 30% better performance than Graviton3 at same price.
- **gp3 storage default (2024):** All new RDS databases default to gp3
  (3000 IOPS, 125 MB/s baseline). Legacy io1/io2 databases -> evaluate gp3.
- **RDS Storage Optimised IOPS (gp3, 2024-2025):** gp3 supports up to
  256,000 provisioned IOPS at $0.005/IOPS-month. Often cheaper than io2.
- **Performance Insights enhanced (2024-2025):** Wait event analytics at SQL
  statement level. Always pull PI data before recommending a downsize.

## References

- `references/cli-commands.md` — full CLI script for pre-flight data gathering
- `references/expert-knowledge.md` — non-obvious RDS/Aurora cost behaviours
- `references/worked-examples.md` — four complete worked examples
- `references/replica-multiaz-constraints.md` — replica and Multi-AZ topology constraints
- `references/rds-instance-pricing-matrix.md` — instance class pricing reference

## Domain

AWS CloudOps / RDS & Aurora Database Cost Optimisation & FinOps.

## AWS documentation

- **Amazon RDS User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Welcome.html
- **Amazon Aurora User Guide** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/CHAP_AuroraOverview.html
- **Aurora Serverless v2** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html
- **Amazon RDS Instance Types** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.DBInstanceClass.html
- **Amazon RDS Storage** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_Storage.html
- **Performance Insights** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.html
- **Amazon RDS Pricing** — https://aws.amazon.com/rds/pricing/
- **Amazon Aurora Pricing** — https://aws.amazon.com/rds/aurora/pricing/
- **Reserved DB Instances** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithReservedDBInstances.html
- **AWS CLI Command Reference: rds** — https://docs.aws.amazon.com/cli/latest/reference/rds/
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
