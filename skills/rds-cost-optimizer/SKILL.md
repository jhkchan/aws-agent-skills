---
name: rds-cost-optimizer
description: >-
  Optimises RDS and Aurora database cost through instance-class right-sizing
  (CloudWatch CPUUtilization, FreeableMemory, DatabaseConnections plus
  Performance Insights DBLoad), storage-class selection (gp3 vs io2),
  Multi-AZ gating by environment, pricing-model evaluation (On-Demand / RI
  1yr-3yr / Savings Plans), engine choice (open-source vs commercial, BYOL),
  Aurora Serverless v2 ACU tuning, and idle-database detection (0 connections
  for 7+ days). Emits a deterministic verdict (OPTIMIZED | OPPORTUNITY_FOUND
  | ALREADY_OPTIMAL) per database with specific recommendation and estimated
  monthly savings. Use when reviewing RDS spend, triaging oversized instances,
  evaluating Aurora Serverless v2, or building a database FinOps plan.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex,
  Gemini). Offline configuration classification works from pasted RDS
  instance metadata, CloudWatch metrics, and Performance Insights summaries.
  Live-account optimisation uses aws rds describe-db-instances, aws
  cloudwatch get-metric-statistics for CPUUtilization/FreeableMemory/
  DatabaseConnections, aws pi describe-dimension-keys for DBLoad top SQL,
  aws rds describe-reserved-db-instances, aws ce get-cost-and-usage with
  RDS Service filter, and aws rds describe-db-snapshots for manual snapshot
  cleanup (AWS CLI v2, SSO or key-based credentials). Pricing is us-east-1
  published rates as of 2026; re-state regional rates before producing dollar
  estimates for other regions.
keywords:
  - RDS
  - Aurora
  - Aurora Serverless v2
  - ACU
  - instance right-sizing
  - gp3
  - io2
  - Multi-AZ
  - Reserved Instance
  - Savings Plans
  - PostgreSQL
  - MySQL
  - Oracle
  - SQL Server
  - BYOL
  - License-included
  - Performance Insights
  - DBLoad
  - CloudWatch
  - FreeableMemory
  - DatabaseConnections
  - cost optimization
  - FinOps
  - idle database
tags: [rds, aurora, databases, cost-optimization, finops, right-sizing, reserved-instance, aurora-serverless]
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL"
  when_to_use: >-
    Reviewing RDS or Aurora spend, right-sizing database instance classes,
    evaluating Multi-AZ necessity by environment, choosing between RI and
    Savings Plans for steady-state databases, tuning Aurora Serverless v2
    ACU min/max, deciding between open-source and commercial engines,
    detecting idle databases for deletion, or cleaning up manual snapshots.
  when_not_to_use: >-
    Performance troubleshooting for a slow database query (use Performance
    Insights directly or a query-tuning specialist), schema design or index
    optimisation (DBA work, not cost-driven), RDS migration planning (use
    DMS tooling), or Aurora Global Database design (architectural, not
    cost). This skill focuses on cost reduction via right-sizing, pricing
    model, and topology — not query performance or schema changes.
  activation_triggers:
    - "optimise RDS cost"
    - "right-size RDS instance"
    - "Aurora Serverless v2 ACU"
    - "RDS Multi-AZ cost"
    - "RDS Reserved Instance"
    - "RDS Savings Plan"
    - "idle database detection"
    - "gp3 vs io2 RDS"
    - "Oracle to PostgreSQL migration"
    - "BYOL vs License-included"
    - "RDS storage autoscaling"
    - "manual snapshot cleanup"
    - "database FinOps review"
    - "Aurora ACU tuning"
    - "RDS downsize recommendation"
  invocation_schema: >-
    Input: either (a) an RDS/Aurora instance identifier + live-account context,
    (b) a database configuration document (instance class, engine, storage,
    Multi-AZ, pricing model, CloudWatch metrics, Performance Insights
    summary), OR (c) a fleet description for batch optimisation. Output: a
    deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/
    MIGRATION_STEPS block per database, where VERDICT ∈ {OPTIMIZED,
    OPPORTUNITY_FOUND, ALREADY_OPTIMAL}.
  invocation_example: |-
    # Minimal valid input (offline classification):
    DBInstanceIdentifier: db-overprovisioned-prod
    Engine: postgres
    DBInstanceClass: db.r6i.2xlarge
    Region: us-east-1
    Multi-AZ: true
    Storage: 500 GB gp3
    AllocatedStorage: 500 GB, Used: 120 GB
    Pricing: On-Demand (no RI/Savings Plan)
    CloudWatch metrics (last 30 days):
      - CPUUtilization: avg=12%, max=25%
      - FreeableMemory: avg=28 GB (of 64 GB), high and stable
      - DatabaseConnections: avg=15, max=30
    Performance Insights:
      - DBLoad: avg=2, max=8 (low for 8 vCPUs)
    Emit the standard optimisation block (TARGET, VERDICT, REASON,
    RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).
---

# RDS Cost Optimizer

## What this skill does

Translates RDS and Aurora database spend into a concrete right-sizing,
pricing-model, and topology plan with a dollar-denominated savings estimate.
Database cost is typically the #2 or #3 line in an AWS bill (after EC2 and
S3), and it is the line with the most structural waste: oversized instances,
Multi-AZ in dev environments, On-Demand pricing on steady-state workloads,
and idle databases that nobody deleted. The verdict is the **highest-leverage
action** across seven dimensions — instance-class right-sizing, storage
optimisation, Multi-AZ gating, pricing model, engine optimisation, Aurora
Serverless v2 ACU tuning, and idle-database detection — applied in priority
order.

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPPORTUNITY_FOUND` | One or more dimensions has a cost-saving recommendation available | Emit recommendation + savings estimate |
| `OPTIMIZED` | A change was applied this session and verified | Emit post-state verification and recompute savings |
| `ALREADY_OPTIMAL` | All dimensions pass for current configuration | No action — confirm posture |

**Priority order for opportunity dimensions (apply in this sequence, aggregate
all that apply into a single recommendation):**

1. **Idle database detection** — databases with 0 connections for 7+ days are
   deletion candidates. This is the largest single saving (eliminates 100% of
   the database cost).
2. **Instance-class right-sizing** — CPU < 30% sustained + high FreeableMemory
   + low DatabaseConnections → downsize. The headline saving for active DBs.
3. **Pricing model** — On-Demand on a steady-state production database is the
   #2 saving lever (RI/Savings Plans capture 40-60%).
4. **Multi-AZ gating** — Multi-AZ in dev/test/staging doubles cost for no
   benefit. Single-AZ is fine for non-production.
5. **Storage optimisation** — gp3 baseline (3000 IOPS free) vs overprovisioned
   io2; storage autoscaling max far above used.
6. **Engine optimisation** — commercial (Oracle/MSSQL) → open-source
   (PostgreSQL/MySQL) migration; License-included vs BYOL.
7. **Aurora Serverless v2 ACU tuning** — min ACU too high; scale to baseline
   load.

**Cost baseline (us-east-1, 2026, representative prices):**

| Component | Example | Notes |
|---|---|---|
| db.m6i.large (On-Demand) | ~$0.38/hour (~$277/month) | General-purpose, 2 vCPU, 8 GB RAM |
| db.r6i.2xlarge (On-Demand) | ~$1.20/hour (~$876/month) | Memory-optimized, 8 vCPU, 64 GB RAM |
| db.r6g.2xlarge (Graviton, On-Demand) | ~$0.96/hour (~$701/month) | ~20% cheaper than r6i |
| Aurora Serverless v2 ACU | ~$0.12/ACU-hour | 0.5-128 ACU per instance |
| Multi-AZ surcharge | 2× the instance cost | Standby instance in another AZ |
| gp3 storage | $0.08/GB-month + free 3000 IOPS | Default for new databases |
| io2 Block Express storage | $0.125/GB-month + $0.10/provisioned-IOPS-month | High-performance OLTP |
| Manual snapshots | $0.095/GB-month | Accumulate indefinitely without cleanup |
| RI 1-yr Standard (no upfront) | ~40% discount | Steady-state production |
| RI 3-yr Standard (no upfront) | ~60% discount | Long-term steady-state |
| Compute Savings Plans 1-yr | ~30% discount (any instance family) | Flexible fleet commitment |

## Mindset

**One-line takeaway:** the verdict is the **largest net-positive saving**
across seven dimensions — driven by four database cost realities:

- **Right-sizing a database is higher-risk than right-sizing an EC2 instance.**
  A database that runs out of memory does not just slow down — it crashes,
  fails over (if Multi-AZ), or causes connection storms that cascade to every
  application depending on it. Downsize conservatively (one size at a time),
  verify with Performance Insights, and always have a rollback path.

- **Multi-AZ in non-production is almost always waste.** The standby instance
  costs the same as the primary, doubling the bill. Dev/test/staging databases
  do not need HA — they need to be cheap. The only exception is integration
  testing that explicitly tests failover behaviour.

- **On-Demand on a steady-state database is the #2 FinOps miss in RDS.**
  Production databases run 24/7 for years. A 3-year RI captures 60% off
  On-Demand. Buying an RI is a billing-account operation (no downtime, no
  migration) — it is the easiest saving in AWS.

- **Idle databases are silent waste.** A database that was spun up for a
  feature that shipped (or didn't), with 0 connections for weeks, bills at
  full price until someone deletes it. DatabaseConnections = 0 for 7+ days is
  a deletion candidate. These are the easiest dollars to save — and the most
  commonly missed because nobody "owns" the idle database.

## Philosophy

Four behaviours separate a senior database FinOps engineer from a generalist:

- **FreeableMemory is the right-sizing signal, not CPU alone.** A database at
  10% CPU with 80% free memory is a downsize candidate. A database at 10% CPU
  with 5% free memory is running near its memory limit — the low CPU is
  misleading because the database is spending time on memory management (buffer
  eviction, sort spills to disk). Always check FreeableMemory before
  recommending a downsize.

- **Performance Insights DBLoad is the query-level truth.** CloudWatch tells
  you the instance is busy; Performance Insights tells you WHY. A high DBLoad
  with a single dominant SQL statement is a query-optimisation problem, not a
  capacity problem. Downsizing a database with a bad query makes the query
  worse, not cheaper.

- **Pricing model and right-sizing are independent and stackable.** A database
  that is both oversized AND on On-Demand has TWO saving levers. Right-size
  first (smaller instance), then buy an RI or Savings Plan for the smaller
  instance. Stacking both captures the maximum saving.

- **Aurora Serverless v2 is not free; it is variable.** The min ACU setting
  determines the floor cost. A min ACU of 8 bills $0.96/hour (8 × $0.12)
  regardless of actual load — the same as a fixed db.r6g.large. Serverless
  v2 only saves money when the min ACU is set LOW and the workload genuinely
  scales. Many users set min ACU too high and pay serverless prices for
  fixed-instance behaviour.

## Pre-flight: database metadata gate

Run before classification. Misclassifying these produces false positives.

**Live-account pre-flight (skip if offline audit):**

```bash
# 1. Enumerate database instances and their configuration
aws rds describe-db-instances --output json | jq '.DBInstances[] | {
  db_instance_id: .DBInstanceIdentifier,
  engine: .Engine,                          # "postgres", "mysql", "oracle-ee", "sqlserver-ee"
  engine_version: .EngineVersion,
  class: .DBInstanceClass,                  # "db.r6i.2xlarge"
  multi_az: .MultiAZ,                       # true | false
  storage_type: .StorageType,               # "gp3" | "io2" | "standard"
  allocated_storage: .AllocatedStorage,     # GB
  storage_throughput: .StorageThroughput,   # MB/s (gp3)
  iops: .Iops,                              # provisioned IOPS (io2, gp3 above baseline)
  license_model: .LicenseModel,             # "license-included" | "bring-your-own-license"
  publicly_accessible: .PubliclyAccessible,
  status: .DBInstanceStatus                 # "available" | "stopped" | "deleting"
}'

# 2. Pull 14-30 day CloudWatch utilization
START=$(date -u -d '-30 days' +%FT%TZ)
END=$(date -u +%FT%TZ)

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=<db-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json > cpu.json

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name FreeableMemory \
  --dimensions Name=DBInstanceIdentifier,Value=<db-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Minimum \
  --output json > mem.json

aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=<db-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum \
  --output json > conns.json

# 3. Pull Performance Insights DBLoad and top SQL
aws pi describe-dimension-keys \
  --service-type RDS \
  --identifier <db-id> \
  --start-time $START --end-time $END \
  --metric db.load.avg \
  --group-by '{"Group":"db.sql"}' \
  --output json

# 4. Check existing Reserved Instances
aws rds describe-reserved-db-instances --output json | \
  jq '.ReservedDBInstances[] | {
    ri_id: .ReservedDBInstanceId,
    class: .DBInstanceClass,
    duration: .Duration,                     # 31536000 (1yr) | 94608000 (3yr)
    state: .State,                           # "active" | "retired"
    offering_type: .OfferingType             # "No Upfront" | "Partial Upfront" | "All Upfront"
  }'

# 5. Check Aurora Serverless v2 ACU metrics (Aurora only)
aws cloudwatch get-metric-statistics --namespace AWS/RDS \
  --metric-name ACUUtilization \
  --dimensions Name=DBClusterIdentifier,Value=<cluster-id> \
  --start-time $START --end-time $END \
  --period 3600 --statistics Average,Maximum,Minimum \
  --output json

# 6. Enumerate manual snapshots for cleanup candidates
aws rds describe-db-snapshots --snapshot-type manual --output json | \
  jq '.DBSnapshots[] | {
    snapshot_id: .DBSnapshotIdentifier,
    db_id: .DBInstanceIdentifier,
    created: .SnapshotCreateTime,
    size_gb: .AllocatedStorage,
    status: .Status
  }'
```

### Data-quality short-circuits

| Condition | Effect on optimisation |
|---|---|
| DBInstanceStatus `stopped` | Instance is not incurring compute charges BUT storage still bills. Surface as a finding — is the stop intentional or forgotten? |
| DBInstanceStatus `deleting` | Transient state. Skip; re-query after the deletion completes. |
| Observation window < 14 days | NEED_MORE_INFO: database workload may reflect atypical load (deploy, migration, seasonal dip). |
| FreeableMemory metric absent (Aurora Serverless v2) | Use ACUUtilization instead; FreeableMemory is not meaningful for serverless. |
| Performance Insights not enabled | Cannot evaluate query-level DBLoad. Flag right-size as MEDIUM confidence (based on CloudWatch only). Recommend enabling PI. |
| DatabaseConnections = 0 for entire window | Strong idle-database signal. If sustained 7+ days → deletion candidate (Step 7). |

## Process — optimisation logic (apply in order, aggregate all applicable)

### Step 0: Expert knowledge — non-obvious RDS and Aurora cost behaviours

These behaviours are easy to misjudge without database operational experience.
Each changes a recommendation if ignored:

- **Multi-AZ doubles the compute cost but NOT the storage cost.** A Multi-AZ
  db.r6i.2xlarge costs 2 × $1.20/hour = $2.40/hour for compute. Storage is
  synchronously replicated to the standby but you only pay for the allocated
  storage once (the standby's copy is included). This means Multi-AZ is a
  compute cost multiplier, not a storage multiplier.

- **Aurora does NOT charge extra for Multi-AZ.** Aurora replicates 6 copies
  of your data across 3 AZs by default — this is built into the Aurora
  storage cost ($0.10/GB-month for standard, vs RDS gp3 $0.08/GB-month). The
  Aurora compute instances (writer + readers) are billed individually, but
  there is no "Multi-AZ surcharge" like RDS. This makes Aurora cheaper than
  RDS Multi-AZ for HA configurations.

- **gp3 includes 3000 IOPS and 125 MB/s throughput free.** RDS gp3 storage
  ($0.08/GB-month) includes a baseline of 3000 IOPS and 125 MB/s throughput at
  no additional cost. Additional IOPS cost $0.005/provisioned-IOPS-month, and
  additional throughput costs $0.04/provisioned-MB/s-month. Many databases
  paying for io2 provisioned IOPS could run on gp3 with free baseline IOPS.

- **io2 Block Express is for high-performance OLTP only.** io2 costs
  $0.125/GB-month PLUS $0.10/provisioned-IOPS-month. A database with 10,000
  provisioned IOPS pays $1,000/month in IOPS charges alone — on top of storage.
  Only databases with sustained high IOPS requirements (and Performance
  Insights evidence of disk-bound queries) justify io2.

- **Storage autoscaling can silently inflate cost.** RDS can auto-scale storage
  up to a configured maximum. If the max is set to 1 TB but the database only
  uses 100 GB, the database still bills for 100 GB (allocated, not max). BUT
  if autoscaling has triggered and the database is now at 500 GB allocated but
  only using 100 GB, you cannot shrink RDS storage — it only grows. Surface
  over-allocation as a finding.

- **Manual snapshots bill indefinitely until deleted.** $0.095/GB-month. A
  500 GB manual snapshot left from a deprecated database costs $47.50/month
  forever. Automated snapshots are retained per the backup retention period
  (default 7 days) and auto-expire. Manual snapshots do NOT auto-expire.

- **Reserved Instances are Zonal or Regional.** A Zonal RI for db.r6i.2xlarge
  in us-east-1a applies only to a Multi-AZ primary in that AZ. A Regional RI
  applies to any instance of that class in the region. For Multi-AZ databases,
  Regional RIs are recommended (the primary can fail over to any AZ).

- **Savings Plans for RDS are Compute Savings Plans, not RDS-specific.** As of
  2026, RDS does NOT have a dedicated Savings Plan like EC2. The commitment
  vehicle for RDS is Reserved Instances (Standard or Convertible). Compute
  Savings Plans apply to EC2, Fargate, and Lambda — NOT RDS. Surface this
  explicitly to avoid recommending the wrong commitment vehicle.

- **Aurora Serverless v2 min ACU determines the floor cost.** The minimum ACU
  can be set as low as 0.5 (billed at $0.06/hour) but many users set it to 2-8
  ACU "for safety." At min ACU 8, the floor cost is $0.96/hour ($701/month) —
  the same as a fixed db.r6g.large. Serverless v2 only saves money when the
  min ACU is set LOW and the workload scales up under load.

- **The Aurora Serverless v2 max ACU cap affects performance, not cost.** Cost
  is driven by ACTUAL ACU consumed, not the max. But a max ACU set too low will
  throttle the database under load. Set max ACU to handle peak (e.g., 2-4×
  baseline); set min ACU to the lowest value that handles baseline load.

- **Graviton (Graviton2/3) RDS instances are ~20% cheaper than x86 equivalents.**
  db.r6g.2xlarge costs ~$0.96/hour vs db.r6i.2xlarge at ~$1.20/hour. PostgreSQL
  and MySQL both support Graviton. Oracle and SQL Server do NOT support
  Graviton. Always prefer Graviton for open-source engines.

- **License-included vs BYOL for Oracle/SQL Server.** License-included bundles
  the Oracle/MSSQL license into the hourly rate (~2-4× the open-source rate).
  BYOL uses your existing license but requires Software Assurance and
  compliance tracking. For organisations with existing enterprise license
  agreements, BYOL is cheaper. For everyone else, migrate to open-source.

- **A stopped RDS instance still bills for storage.** Stopping a database
  eliminates the compute charge but storage continues at $0.08-0.125/GB-month.
  A "stopped" database is not free — it is only compute-paused. After 7 days,
  AWS auto-starts the instance. Surface stopped databases as deletion
  candidates if they have been stopped for extended periods.

- **RDS does not support in-place instance-class changes without downtime.**
  Changing the DBInstanceClass requires a modification that causes a brief
  outage (minutes). For Multi-AZ, the failover-based modification minimises
  downtime but the database still briefly restarts. Schedule right-sizes
  during maintenance windows.

- **Snapshot restore is the rollback path for instance-class changes.** Before
  a right-size, take a manual snapshot: `aws rds create-db-snapshot`. If the
  new instance class causes performance regression, restore from the snapshot
  to the original class. RDS does not support in-place rollback of instance
  modifications.

### Step 1: Idle database detection (highest leverage)

If DatabaseConnections = 0 for 7+ consecutive days AND CPUUtilization < 5%:

- **Strong deletion candidate.** Surface as the #1 recommendation.
- **Before recommending deletion:**
  1. Verify with the application team that the database is truly unused (some
     databases serve batch jobs that run monthly).
  2. Take a final manual snapshot before deletion (retains the data for
     regulatory or future-restore needs).
  3. Check for cross-region replicas or Aurora global clusters that may depend
     on it.

**Decision matrix:**

| Observation (30-day window) | Verdict | Recommendation |
|---|---|---|
| DatabaseConnections = 0 for 30+ days, CPU < 1% | **OPPORTUNITY_FOUND** (delete) | Final snapshot + delete database |
| DatabaseConnections = 0 for 7-30 days, CPU < 5% | **OPPORTUNITY_FOUND** (MEDIUM confidence) | Verify with app team, then final snapshot + delete |
| DatabaseConnections avg < 2, CPU < 5% for 30 days | **OPPORTUNITY_FOUND** (downsize or delete) | Investigate; likely dev/test with minimal load |
| DatabaseConnections avg > 5 | Not idle | Proceed to Step 2 (right-sizing) |

### Step 2: Instance-class right-sizing

If the database is active (not idle), evaluate the instance class.

**Decision matrix:**

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| CPU < 30% avg AND FreeableMemory > 50% of total AND DatabaseConnections low | **OPPORTUNITY_FOUND** (downsize) | Downsize 1-2 instance classes |
| CPU < 10% AND FreeableMemory > 70% | **OPPORTUNITY_FOUND** (downsize 2 sizes) | Downsize 2 instance classes |
| CPU > 70% sustained OR FreeableMemory < 20% | **OPPORTUNITY_FOUND** (upsize) | Upsize — performance risk |
| DBLoad dominated by 1-2 SQL statements | Investigate query | Query optimisation BEFORE right-sizing |
| CPU 30-70%, Memory 30-70% | Correctly sized | Proceed to Step 3 (pricing model) |

**Downsize magnitude:**
- Conservative: downsize 1 size (e.g., db.r6i.2xlarge → db.r6i.xlarge).
- Aggressive (CPU < 10% + Memory > 70%): downsize 2 sizes.
- Always verify with Performance Insights DBLoad after downsizing.

**Family selection for right-sizing:**
- Memory-optimised (db.r6i/r6g): for OLTP, in-memory caches (PostgreSQL, MySQL
  with large buffer pool).
- General-purpose (db.m6i/m6g): for balanced workloads, dev/test.
- Burstable (db.t4g/t3): for dev/test with low baseline load. t-family RDS
  instances have a CPU credit system similar to EC2 — check for credit
  exhaustion before recommending.
- Graviton (db.r6g/m6g/t4g): ~20% cheaper for PostgreSQL and MySQL. Always
  prefer Graviton for open-source engines.

### Step 3: Pricing model optimisation

After right-sizing, evaluate the pricing model.

**Decision matrix:**

| Workload pattern | Recommended model | Savings vs On-Demand |
|---|---|---|
| Steady-state production (24/7, predictable) | 3-yr Standard RI (No Upfront) | ~60% |
| Steady-state but uncertain growth | 1-yr Convertible RI (No Upfront) | ~30% |
| Dev/test, business-hours only | 1-yr Standard RI or On-Demand | ~40% or 0% |
| Aurora Serverless v2 (variable load) | On-Demand (ACU-based, no RI) | Serverless is inherently On-Demand |

**IMPORTANT:** As of 2026, RDS does NOT support Compute Savings Plans. The
commitment vehicle for RDS is Reserved Instances only. Compute Savings Plans
apply to EC2, Fargate, and Lambda. Do NOT recommend a Savings Plan for RDS —
recommend an RI.

**Commitment laddering (recommended approach):**
1. Identify the steady-state database spend (production databases running 24/7).
2. Purchase 1-yr Standard RIs for the baseline (low risk, 40% discount).
3. After confirming the workload is stable, extend to 3-yr Standard RIs (60%
   discount) for the most stable databases.
4. Keep On-Demand for genuinely variable workloads and Aurora Serverless v2.

### Step 4: Multi-AZ gating

Evaluate Multi-AZ necessity based on environment.

**Decision matrix:**

| Environment | Multi-AZ | Recommendation |
|---|---|---|
| Production (customer-facing) | Yes | Keep Multi-AZ — HA is required |
| Production (internal tool) | Evaluate | Multi-AZ if the tool is critical; single-AZ if not |
| Staging | Usually no | Single-AZ — staging does not need HA |
| Dev/test | No | Single-AZ — save the standby cost |
| Integration testing failover | Yes | Only if explicitly testing failover |

**Multi-AZ cost impact:**
- Disabling Multi-AZ halves the compute cost (removes the standby).
- Disabling Multi-AZ causes a brief restart during the modification.
- Aurora is inherently Multi-AZ (6 copies, 3 AZs) — no surcharge.

If Multi-AZ is enabled in a non-production environment:
**OPPORTUNITY_FOUND** on this dimension.

### Step 5: Storage optimisation

Evaluate storage type and allocation.

**Decision matrix:**

| Current storage | Workload | Recommendation |
|---|---|---|
| io2 with provisioned IOPS | Sustained disk-bound queries confirmed via PI | Keep io2 (justified) |
| io2 with provisioned IOPS | No disk-bound evidence in PI | **OPPORTUNITY_FOUND** — migrate to gp3 |
| gp3 with additional IOPS purchased | Below 3000 IOPS actual | **OPPORTUNITY_FOUND** — remove additional IOPS |
| Allocated >> Used (e.g., 500 GB allocated, 100 GB used) | N/A | Finding — RDS storage cannot shrink; surface for awareness |
| Manual snapshots accumulating | N/A | **OPPORTUNITY_FOUND** — automate cleanup |

**Manual snapshot cleanup:**
```bash
# List manual snapshots older than 90 days
aws rds describe-db-snapshots --snapshot-type manual --output json | \
  jq '.DBSnapshots[] | select(.SnapshotCreateTime < (now - 7776000))
      | {snapshot_id, db_id, created, size_gb}'

# Delete a manual snapshot
aws rds delete-db-snapshot --db-snapshot-identifier <snapshot-id>
```

### Step 6: Engine optimisation

Evaluate the database engine for cost efficiency.

**Decision matrix:**

| Current engine | Workload | Recommendation |
|---|---|---|
| PostgreSQL / MySQL (open-source) | Any | Already on the cheapest engine; prefer Graviton instances |
| Oracle (license-included) | Compatible with PostgreSQL | **OPPORTUNITY_FOUND** — migrate to Aurora PostgreSQL or RDS PostgreSQL |
| SQL Server (license-included) | Compatible with PostgreSQL/MySQL | **OPPORTUNITY_FOUND** — migrate to open-source |
| Oracle/SQL Server (BYOL) | Existing enterprise licenses | Evaluate — BYOL may be cheaper than license-included |
| Oracle/SQL Server | Mission-critical, vendor-locked | Keep — migration is not a cost-optimisation quick win |

**Engine cost comparison (us-east-1, db.r6i.2xlarge equivalent):**
- PostgreSQL: ~$1.20/hour
- MySQL: ~$1.20/hour
- Oracle (license-included): ~$3.60/hour (3× open-source)
- SQL Server Enterprise (license-included): ~$5.40/hour (4.5× open-source)

Engine migration is a high-effort, high-reward recommendation — surface it as
a strategic finding, not a quick fix.

### Step 7: Aurora Serverless v2 ACU tuning

If the database is Aurora Serverless v2:

**Decision matrix:**

| Observation (30-day window) | Verdict | Recommendation |
|---|---|---|
| ACUUtilization avg < min ACU × 0.5 | **OPPORTUNITY_FOUND** | Lower min ACU to actual baseline |
| ACUUtilization frequently hits max ACU | **OPPORTUNITY_FOUND** (upsize) | Raise max ACU — performance throttle risk |
| ACUUtilization stable between min and max | Correctly tuned | Proceed to other dimensions |

**ACU cost model:**
```
hourly_cost = actual_ACU × $0.12
monthly_cost_floor = min_ACU × $0.12 × 730
```

Example: min ACU 8, max ACU 64, actual avg ACU 4:
- Floor cost: 8 × $0.12 × 730 = $701/month
- Actual cost: ~4 × $0.12 × 730 = $350/month (but billed at min floor when below)
- Recommendation: lower min ACU from 8 to 2 → floor cost drops to $175/month.

### Step 8: Impact estimation

Compute the monthly savings for each recommendation:

```
Monthly savings = sum(per-dimension savings)
```

Per dimension:
- Right-size: `(current_hourly − new_hourly) × 730`
- Pricing model: `new_hourly × RI_discount × 730`
- Multi-AZ removal: `current_hourly × 730` (halves compute)
- Storage (io2 → gp3): `(io2_storage_cost − gp3_storage_cost) + IOPS_savings`
- Engine migration: `(commercial_hourly − open_source_hourly) × 730`
- Aurora ACU: `(old_min_ACU − new_min_ACU) × $0.12 × 730`
- Idle deletion: `entire database monthly cost`

Stack applicable dimensions (e.g., right-size + pricing model + Multi-AZ
removal) for the total saving.

### Step 9: Aggregation and final verdict

The verdict is the worst-case (most-actionable) finding across all dimensions:

- If any dimension recommends a change, verdict is **OPPORTUNITY_FOUND**.
- If all dimensions pass AND pricing is already optimized (RI in place),
  verdict is **ALREADY_OPTIMAL**.
- If all dimensions pass for current class but pricing model could improve,
  verdict is **OPPORTUNITY_FOUND** (pricing dimension).

## Output format (per database)

```text
TARGET: <db-instance-id or cluster-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <engine> <instance-class> <Multi-AZ> <storage> at <pricing-model>
  Proposed: <engine> <instance-class> <Multi-AZ> <storage> at <pricing-model>
  Dimensions: <list of applicable dimensions (right-size, pricing, Multi-AZ, etc.)>
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

### Worked example — overprovisioned PostgreSQL, no RI, Multi-AZ in dev

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
  Dimensions: right-size (r6i.2xlarge → r6g.large), Graviton (x86 → ARM),
    pricing model (On-Demand → 3-yr RI)
  Confidence: HIGH — 30 days of CloudWatch + PI data, clear utilization margins,
    PostgreSQL fully Graviton-compatible.
ESTIMATED_SAVINGS:
  Monthly (right-size + Graviton): $1,316.00
    - r6i.2xlarge Multi-AZ: $1.20 × 2 × 730 = $1,752.00
    - r6g.large Multi-AZ: $0.34 × 2 × 730 = $496.40
    - Saving: $1,255.60/month
  Monthly (pricing model): $198.56
    - 3-yr Standard RI (60% off) on r6g.large Multi-AZ:
      $496.40 × 0.60 = $297.84/month additional saving
    - Adjusted: ~$198.56 after RI amortisation
  Monthly (Multi-AZ): $0 (correctly enabled for production)
  Annual total: ~$18,524.00
  Assumptions: 730h/month, us-east-1 pricing as of 2026-08-07, workload
    steady-state, PostgreSQL 15+ fully supports Graviton.
MIGRATION_STEPS:
  1. Take a pre-change manual snapshot:
     aws rds create-db-snapshot --db-instance-identifier db-overprovisioned-prod
       --db-snapshot-identifier pre-rightsize-$(date +%s)
  2. Modify the instance class (brief downtime):
     aws rds modify-db-instance --db-instance-identifier db-overprovisioned-prod
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
       --reserved-db-instance-id ri-r6g-large-3yr
  5. Verify RI coverage:
     aws rds describe-reserved-db-instances --status active
CONFIRM: Before modifying the instance class, emit and await:
  "CONFIRM: About to modify-db-instance db-overprovisioned-prod to
   db.r6g.large in us-east-1. This causes a brief restart (~2-5 minutes).
   Proceed? (yes/no)"
  Do NOT run the CLI until the operator confirms.
```

### Worked example — idle database deletion

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
    - db.m6i.large: $0.38 × 730 = $277.40
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
  Do NOT run the CLI until the operator confirms.
```

### Worked example — already optimal production database

```text
TARGET: db-prod-orders-db
VERDICT: ALREADY_OPTIMAL
REASON: db.r6g.2xlarge PostgreSQL on a 3-yr Standard RI, CPU 55% avg,
  FreeableMemory 40% avg, Multi-AZ enabled for production, gp3 storage
  correctly sized, no manual snapshot accumulation. Aurora Serverless v2 not
  applicable (fixed instance). All dimensions pass.
RECOMMENDATION: No changes required.
ESTIMATED_SAVINGS:
  Monthly: $0.00
  Annual: $0.00
MIGRATION_STEPS:
  - None required. Continue monitoring CloudWatch and Performance Insights
    monthly. Re-evaluate at RI renewal date.
```

## Verdict consistency rules (prevent misclassification)

1. **Zero-savings rule.** If `MONTHLY_SAVING == $0.00` for every dimension,
   the verdict MUST be `ALREADY_OPTIMAL`, never `OPPORTUNITY_FOUND`.

2. **OPPORTUNITY_FOUND requires a non-zero savings line.** The SAVINGS block
   must show a positive `MONTHLY_SAVING` for at least one dimension.

3. **SAVINGS arithmetic check.** Per-dimension savings must sum to the total
   annual savings (accounting for stacking order). Round to 2 decimal places.

4. **RDS Savings Plan rule.** Do NOT recommend a Compute Savings Plan for RDS.
   As of 2026, RDS only supports Reserved Instances. Compute Savings Plans
   apply to EC2, Fargate, and Lambda. Recommending a Savings Plan for RDS is
   a hard error.

5. **Graviton engine gate.** Do NOT recommend Graviton for Oracle or SQL
   Server. Only PostgreSQL and MySQL support Graviton instances. Recommending
  db.r6g for an Oracle database is non-compliant.

6. **Idle deletion requires app-team verification.** A deletion recommendation
   without "verify with application team" is incomplete. Databases may serve
   monthly batch jobs or seasonal workloads invisible in a 30-day window.

7. **Right-size recommendations MUST cite FreeableMemory.** A downsize based
   on CPU alone (without FreeableMemory evidence) is a guess. Surface the
   FreeableMemory data point explicitly.

## Error handling — CLI and data-source failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-db-instances` returns empty | `len(DBInstances) == 0` | No databases to optimise. Verdict ALREADY_OPTIMAL for the fleet. |
| CloudWatch CPUUtilization returns empty | `len(Datapoints) == 0` | Database may be stopped. Check DBInstanceStatus; if stopped, surface as finding. |
| Performance Insights `describe-dimension-keys` returns AccessDenied | PI not enabled or IAM denies pi:* | Proceed with CloudWatch-only analysis; flag right-size as MEDIUM confidence. Recommend enabling PI. |
| `modify-db-instance` fails with `InvalidParameterCombination` | Instance class not available for engine/region | The target class (e.g., Graviton) may not support the engine. Verify engine-class compatibility before recommending. |
| `purchase-reserved-db-instances-offering` fails with `ReservedDBInstancesOfferingNotFound` | Offering ID stale or fulfilled | Re-query `describe-reserved-db-instances-offerings` for a fresh offering-id. |
| Aurora ACUUtilization metric absent (non-serverless Aurora) | Empty datapoints | Database is provisioned Aurora, not Serverless v2. Skip Step 7. |
| Database in `modifying` state | DBInstanceStatus | A modification is already in progress. Wait for it to complete before recommending another change. |

## Anti-Patterns — NEVER

- NEVER recommend a downsize without FreeableMemory data. CPU alone does not
  tell you whether the database is memory-pressured. A database at 10% CPU
  with 5% free memory is NOT a downsize candidate — it is memory-bound.

- NEVER recommend a Compute Savings Plan for RDS. As of 2026, RDS only
  supports Reserved Instances. Compute Savings Plans apply to EC2, Fargate,
  and Lambda. Recommend an RI instead.

- NEVER recommend Graviton instances for Oracle or SQL Server. Only
  PostgreSQL and MySQL support Graviton. db.r6g/db.m6g/db.t4g are x86-
  incompatible for commercial engines.

- NEVER recommend disabling Multi-AZ for a customer-facing production
  database. Multi-AZ provides the HA failover that prevents customer-visible
  outages. The cost saving does not justify the reliability risk.

- NEVER recommend an Aurora Serverless v2 migration without checking the min
  ACU setting. Many users set min ACU too high (8+) and pay serverless prices
  for fixed-instance behaviour. Always specify a LOW min ACU (0.5-2) for the
  serverless saving to materialise.

- NEVER recommend deleting an idle database without verifying with the
  application team. The database may serve monthly batch jobs, seasonal
  workloads, or compliance archives invisible in a 30-day CloudWatch window.

- NEVER recommend engine migration (Oracle → PostgreSQL) as a quick fix.
  Engine migration is a multi-month project involving schema conversion
  (AWS SCT), application code changes, and data migration (AWS DMS). Surface
  it as a strategic finding, not a quick win.

- NEVER assume RDS storage can shrink. RDS storage only grows — there is no
  `modify-db-instance` to reduce AllocatedStorage. Surface over-allocation as
  a finding, not an actionable recommendation.

- NEVER stack a right-size and a pricing-model change in a single step.
  Right-size first (verify utilisation for 7 days), then purchase the RI for
  the new instance class. Stacking obscures which change produced the savings.

- NEVER recommend a Zonal RI for a Multi-AZ database. The primary can fail
  over to any AZ; a Zonal RI only covers one. Use Regional RIs for Multi-AZ
  databases.

- NEVER recommend io2 storage without Performance Insights evidence of disk-
  bound queries. io2 costs $0.10/provisioned-IOPS-month on top of $0.125/GB-
  month — it is the most expensive RDS storage option. Only sustained high-
  IOPS OLTP workloads justify it.

- NEVER auto-apply instance modifications or deletions without the CONFIRM
  gate. Database modifications cause brief downtime; deletions are permanent.

- NEVER recommend Aurora Serverless v2 for a high-throughput steady-state
  workload. Serverless v2 shines for VARIABLE workloads (scale up and down).
  A 24/7 high-throughput database is cheaper on a fixed Aurora provisioned
  instance. Serverless v2 at sustained high ACU costs more than the
  equivalent fixed instance.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-db-instance`, `delete-db-instance`, `create-db-snapshot`,
  `purchase-reserved-db-instances-offering`), emit and await operator
  approval. Do NOT execute until the operator confirms.

- **Snapshot before right-sizing.** Capture the current state:
  `aws rds create-db-snapshot --db-instance-identifier <id>
  --db-snapshot-identifier pre-rightsize-<timestamp>`.
  This provides a rollback path if the new instance class cannot handle the
  workload.

- **Schedule right-sizes during maintenance windows.** `modify-db-instance`
  causes a brief restart (minutes). For Multi-AZ, the failover-based
  modification minimises downtime but the database still briefly restarts.

- **Verify engine-class compatibility before recommending Graviton.**
  `aws rds describe-orderable-db-instance-options --engine postgres --db-instance-class db.r6g.large`
  confirms the class is available for the engine in the region.

- **RI purchase is account-level.** A Reserved Instance applies to the
  purchasing account. Confirm the account ID before purchasing. For
  Organisations, RIs can be shared via the billing family.

- **Bulk-operation safety.** For fleet-wide RDS optimisation, process one
  database per CONFIRM gate. Do NOT batch database modifications — a right-
  size error on one database should not cascade to others.

## Right-sizing decision tree

Route a right-sizing recommendation through this tree before modifying
any instance class. It prevents false-positive downsizes on
memory-pressured databases and identifies Aurora Serverless v2 candidates.

```
Is CPUUtilization < 20% sustained (14+ day window)?
├── YES → Is FreeableMemory > 50% of total instance memory?
│   ├── YES → OPPORTUNITY_FOUND (downsize).
│   │         Downsize 1-2 instance classes. Verify Performance Insights
│   │         DBLoad is not dominated by a single query first.
│   └── NO → Memory is constrained despite low CPU. Do NOT downsize.
│            The database is likely spending time on memory management
│            (buffer eviction, sort spills to disk). Investigate query
│            patterns or buffer pool tuning before right-sizing.
└── NO → Is CPUUtilization > 70% sustained?
    ├── YES → OPPORTUNITY_FOUND (upsize or tune queries).
    │         Check Performance Insights: if DBLoad is dominated by 1-2
    │         SQL statements, optimise the queries FIRST, then re-evaluate.
    │         If DBLoad is evenly distributed, upsize the instance class.
    └── NO → CPU is in the 20-70% range (healthy utilisation).
        └── Is FreeableMemory > 50% AND DatabaseConnections < 10 avg?
            ├── YES → Consider Aurora Serverless v2 if the workload is
            │         variable (sporadic connections, bursty traffic).
            │         For fixed workloads, the instance is correctly
            │         sized — proceed to pricing model (Step 3).
            └── NO → Instance is correctly sized. Proceed to pricing
                      model (Step 3) or storage optimisation (Step 5).
```

Post-tree overrides:

| Condition | Override |
|---|---|
| Performance Insights not enabled | Cannot verify DBLoad. Mark right-size as MEDIUM confidence (CloudWatch only). Recommend enabling PI before executing the downsize. |
| DatabaseConnections = 0 for 7+ days | Override: skip right-sizing. The database is an idle-deletion candidate (Step 1). Deleting saves 100% vs 30-50% from downsizing. |
| Instance has read replicas | See Error handling — read replicas below. Downsize replicas first, then primary. |
| DBInstanceStatus = `modifying` | A modification is already in progress. Wait for completion before right-sizing. |

## Worked example — right-size + Reserved Instance (68% saving)

This example walks through the complete workflow: analyse metrics,
identify over-provisioning via the decision tree, right-size, add
pricing-model optimisation, calculate savings, and provide migration steps.

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

**Step 1 — Analyse current cost:**
```
Current compute (Multi-AZ On-Demand):
  db.r5.2xlarge: ~$1.027/hour per instance x 2 (Multi-AZ) x 730 hours
  = $1,499.42/month

Current storage:
  300 GB gp3 x $0.08/GB = $24.00/month

Current total: $1,523.42/month ($18,281.04/year)
```

**Step 2 — Route through the right-sizing decision tree:**
- CPUUtilization < 20% sustained? YES (8% avg) → continue.
- FreeableMemory > 50%? YES (81% free) → OPPORTUNITY_FOUND (downsize).
- PI DBLoad is low (0.3 avg vs 8 vCPUs) → confirms the workload is not
  capacity-constrained. Safe to downsize.

**Step 3 — Determine the target instance class:**
- Current: db.r5.2xlarge (8 vCPU, 64 GB)
- CPU at 8% on 8 vCPUs → effective usage ~0.64 vCPU
- FreeableMemory 52 GB → actual usage ~12 GB
- Target: db.r5.large (2 vCPU, 16 GB) — 4x smaller, comfortably handles
  the current workload with headroom for the 45 avg connections.

**Step 4 — Add pricing-model optimisation:**
The database is steady-state production (24/7). A 1-year Standard RI
(No Upfront) captures ~40% off On-Demand. Stack with the right-size.

**Step 5 — Calculate projected cost:**
```
Projected compute (Multi-AZ + 1yr RI):
  db.r5.large On-Demand: ~$0.548/hour per instance x 2 (Multi-AZ) x 730
  = $800.08/month
  With 1yr RI (40% off): $800.08 x 0.60 = $480.05/month

Projected storage: $24.00/month (unchanged)

Projected total: $504.05/month ($6,048.60/year)
```

**Step 6 — Savings summary:**
```
Monthly saving: $1,523.42 - $504.05 = $1,019.37 (66.9%)
Annual saving: $12,232.44
```

**Step 7 — Emit the output block:**
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
  Dimensions: right-size (r5.2xlarge to r5.large), pricing model
    (On-Demand to 1yr RI)
  Confidence: HIGH — 30 days of CloudWatch + PI data, CPU at 8% with 81%
    free memory, DBLoad negligible, PostgreSQL supports the target class.
ESTIMATED_SAVINGS:
  Current monthly: $1,523.42
    compute: 2 x $1.027 x 730 = $1,499.42
    storage: 300 x $0.08 = $24.00
  Projected monthly: $504.05
    compute: 2 x $0.548 x 730 x 0.60 (1yr RI) = $480.05
    storage: 300 x $0.08 = $24.00
  Monthly saving: $1,019.37 (66.9%)
  Annual saving: $12,232.44
  Assumptions: 730h/month, us-east-1 pricing, 1yr Standard RI No Upfront
    at 40% discount, storage unchanged, workload steady-state.
MIGRATION_STEPS:
  1. Take a pre-change manual snapshot:
     aws rds create-db-snapshot --db-instance-identifier db-prod-checkout-db
       --db-snapshot-identifier pre-rightsize-$(date +%s)
  2. Modify the instance class (brief downtime via Multi-AZ failover):
     aws rds modify-db-instance --db-instance-identifier db-prod-checkout-db
       --db-instance-class db.r5.large --apply-immediately
  3. Monitor CPUUtilization and FreeableMemory for 7 days post-change.
     Roll back if CPU > 80% or FreeableMemory < 20%.
  4. After 7 days of stable operation, purchase a 1yr Standard RI:
     aws rds describe-reserved-db-instances-offerings
       --db-instance-class db.r5.large --duration 31536000
       --offering-type "No Upfront" --multi-az
     aws rds purchase-reserved-db-instances-offering
       --reserved-db-instances-offering-id <offering-id>
       --reserved-db-instance-id ri-r5-large-1yr
  5. Verify RI coverage:
     aws rds describe-reserved-db-instances --status active
CONFIRM: Before modifying the instance class, emit and await:
  "CONFIRM: About to modify-db-instance db-prod-checkout-db to
   db.r5.large in us-east-1. Multi-AZ failover causes ~2-5 min downtime.
   Monthly saving $1,019.37 (66.9%). Proceed? (yes/no)"
```

## Error handling — replica and Multi-AZ constraints

These constraints affect right-sizing recommendations when the database
topology includes read replicas or Multi-AZ standby instances. Failing to
account for these produces recommendations that break replication or
underestimate cost impact.

### Read replicas — downsize primary breaks replicas

**Problem:** RDS read replicas should run the same instance class as (or
larger than) the primary for replication stability. Downsizing the
primary WITHOUT first downsizing the replicas can cause replication lag
or errors. Downsizing the primary below the largest replica's class is
not supported and will be rejected by the RDS API.

**Detection:**
```bash
# List all read replicas of the primary
aws rds describe-db-instances --output json | \
  jq '.DBInstances[] | select(.ReadReplicaSourceDBInstanceIdentifier == "<primary-id>")
  | {DBInstanceIdentifier, DBInstanceClass, Status}'
```

**Resolution path:**
1. Identify all read replicas of the primary.
2. Plan the downsize sequence: downsize replicas FIRST, then the primary.
3. Each replica downsize requires its own modification and brief downtime.
4. After each replica downsize, verify replication lag is within acceptable
   bounds (`ReplicaLag` < 5 seconds) before proceeding to the next.
5. For Aurora: read replicas are Aurora Replicas within the cluster.
   Downsizing the Aurora writer does NOT automatically downsize readers —
   each reader instance must be modified separately.
6. If any replica serves a latency-sensitive read workload, verify it can
   handle the smaller instance class before downsizing (check its own
   CloudWatch metrics independently).

**Example migration sequence:**
```
Primary: db.r5.2xlarge (Multi-AZ, $1,499/month compute)
Replica 1: db.r5.2xlarge (Single-AZ, $750/month compute)
Replica 2: db.r5.2xlarge (Single-AZ, $750/month compute)

Downsize sequence (all to db.r5.large):
  1. Modify Replica 1 to db.r5.large, verify ReplicaLag < 5s for 24h
  2. Modify Replica 2 to db.r5.large, verify ReplicaLag < 5s for 24h
  3. Modify Primary to db.r5.large (Multi-AZ failover, ~5 min downtime)
  4. Verify replication health for 7 days
  5. Purchase RIs for all three instances at the new class
```

**Recommendation adjustment:** When read replicas exist, the
MIGRATION_STEPS must include per-replica modifications and verification
gates. The total saving includes ALL instances (primary + all replicas),
not just the primary.

### Multi-AZ — both instances change simultaneously

**Problem:** When you modify a Multi-AZ RDS instance class, AWS performs
the modification by first updating the standby, then failing over to it,
then updating the old primary (now the new standby). Both instances end
up on the new class. This has three implications:

1. The cost change applies to BOTH instances (primary + standby).
2. There is a brief failover during the modification (30 seconds to
   3 minutes of connection disruption).
3. The RI coverage must account for BOTH instances.

**Detection:**
```bash
# Check if Multi-AZ is enabled
aws rds describe-db-instances --db-instance-identifier <id> --output json | \
  jq '.DBInstances[0] | {MultiAZ, DBInstanceClass, DBSubnetGroup}'
```

**Resolution path:**

1. **Cost impact is doubled.** A Multi-AZ downsize saves on BOTH the
   primary and standby instances. Always compute savings as
   `2 x (old_hourly - new_hourly) x 730`. The headline saving in the
   output block should reflect this doubled amount.

2. **RI sizing for Multi-AZ.** When purchasing an RI for a Multi-AZ
   database, you need RI coverage for the primary instance. The standby
   is a separate billed instance. Use:
   `aws rds describe-reserved-db-instances-offerings --multi-az` to find
   Multi-AZ RI offerings that cover both instances under a single
   reservation. Alternatively, purchase two standard (non-Multi-AZ)
   Regional RIs to cover each instance independently.

3. **Downtime planning.** The failover causes a brief connection drop
   (30s to 3min). Applications with connection retry logic recover
   automatically. Schedule the modification during a maintenance window.
   Warn the operator in the CONFIRM gate.

4. **Aurora exception.** Aurora does NOT charge extra for Multi-AZ (6
   copies across 3 AZs is included in the storage cost). Aurora writer
   and reader instances are billed individually, but there is no standby
   surcharge. This constraint applies to RDS for PostgreSQL/MySQL/Oracle/
   SQL Server, not to Aurora.

**Example cost computation:**
```
Multi-AZ db.r5.2xlarge On-Demand:
  Primary:  db.r5.2xlarge at $1.027/hr x 730 = $749.71/month
  Standby:  db.r5.2xlarge at $1.027/hr x 730 = $749.71/month
  Total compute: $1,499.42/month

After downsize to db.r5.large Multi-AZ + 1yr RI:
  Primary:  db.r5.large at $0.548/hr x 730 x 0.60 = $240.02/month
  Standby:  db.r5.large at $0.548/hr x 730 x 0.60 = $240.02/month
  Total compute: $480.05/month

Saving: $1,019.37/month (68.0%)
RI action: purchase Multi-AZ RI for db.r5.large to cover both instances.
```

## Recent AWS features (2024-2026)

- **Aurora Serverless v2 (expanded 2024-2025):** Now supports 0.5-128 ACU per
  instance, cross-Region replication, and Global Database. Min ACU can be set
  as low as 0.5 for genuine scale-to-near-zero. Evaluate existing Serverless
  v2 databases for min ACU reduction opportunities.

- **Graviton4 RDS instances (2024-2025):** db.r8g and db.m8g families rolling
  out for PostgreSQL and MySQL. Up to 30% better performance than Graviton3
  at the same price. Re-evaluate Graviton migration opportunities on workloads
  that were on x86.

- **gp3 storage default (2024):** All new RDS databases default to gp3 (3000
  IOPS, 125 MB/s baseline). Legacy databases on io1/io2 should be evaluated
  for gp3 migration if actual IOPS are below 3000.

- **RDS Storage Optimised IOPS (gp3, 2024-2025):** gp3 now supports up to
  256,000 IOPS provisioned (above the free 3000 baseline) at $0.005/IOPS-month.
  For high-IOPS workloads that previously required io2, gp3 with additional
  IOPS is often cheaper.

- **Performance Insights enhanced (2024-2025):** Now includes wait event
  analytics at the SQL statement level, enabling query-level right-sizing
  decisions. Always pull PI data before recommending a downsize.

- **RDS IAM Database Authentication expanded:** Reduces the need for
  long-lived database credentials. Not a cost lever, but relevant for
  security posture alongside cost optimisation.

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
