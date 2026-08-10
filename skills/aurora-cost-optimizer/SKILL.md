---
name: aurora-cost-optimizer
description: Optimises Amazon Aurora cluster cost across seven dimensions — instance-class right-sizing for Aurora Standard (db.r6/r7 vs db.t3/t4 burstable), Aurora Serverless v2 ACU min/max tuning (eliminate
  idle ACU floor, scale to peak), Aurora I/O-Optimized storage tier (flat-rate I/O for I/O-heavy workloads, 40-60% I/O cost reduction vs Standard), storage and automated snapshot cleanup, Global Database
  cross-region read-replica instance cost, backtrack storage cost, Performance Insights waste detection (top-SQL tuning targets that reduce instance-class requirements), and Reserved Instance vs On-Demand
  (1-yr/3-yr commit break-even). Distinguishes Aurora vs RDS for cost (Aurora slightly higher per unit but better HA/performance; free Multi-AZ replication). Covers Aurora Limitless Database (2024+) horizontal
  sharding cost trade-offs. Emits OPTIMIZED, OPPORTUNITY_FOUND, or ALREADY_OPTIMAL per cluster with estimated monthly savings. Use when reviewing Aurora spend, tuning Serverless v2 ACU, evaluating I/O-Optimized.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted cluster configuration, Performance Insights summaries, and billing
  line items. Live-account optimisation uses aws rds describe-db-clusters, describe-db-instances, describe-global-clusters, describe-db-proxies, aws pi describe-dimension-keys and get-resource-metrics for
  DBLoad top-SQL, aws ce get-cost-and-usage filtered to Amazon Aurora USAGE_TYPEs (Aurora:InstanceUsage, Aurora:StorageUsage, Aurora:IOUsage, Aurora:ServerlessUsage), aws rds describe-reserved-db-instances-offerings,
  and aws rds describe-db-cluster-backtracks (AWS CLI v2, SSO or key-based credentials). Pricing is us-east-1 published rates as of 2026; re-state regional rates before producing dollar estimates for other
  regions.
keywords:
- Amazon Aurora
- Aurora MySQL
- Aurora PostgreSQL
- Aurora Serverless v2
- Aurora I/O-Optimized
- Aurora Limitless
- Aurora Global Database
- ACU
- instance right-sizing
- Performance Insights
- DBLoad
- Reserved Instance
- backtrack
- Aurora Standard
- storage optimization
- FinOps
- database cost
tags:
- aurora
- databases
- cost-optimization
- finops
- serverless
- right-sizing
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 3
  supports_pipeline: true
  entry_point: false
  family: Databases
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Reviewing Amazon Aurora cluster spend, right-sizing Aurora writer and reader instance classes, tuning Aurora Serverless v2 ACU min and max, evaluating Aurora I/O-Optimized vs Standard storage
    tier, sizing Aurora Global Database read replicas, auditing backtrack storage cost, using Performance Insights to identify waste-driving SQL, deciding between On-Demand and Reserved Instances for steady-state
    Aurora, or evaluating Aurora Limitless Database for horizontal scaling workloads.
  when_not_to_use: RDS for MySQL/PostgreSQL/Oracle/SQL Server cost optimisation (use rds-cost-optimizer — this skill is Aurora-specific), DynamoDB capacity-mode optimisation (use a DynamoDB specialist),
    Redshift cluster right-sizing, query performance tuning as the primary goal (use a DBA / Performance Insights query-tuning workflow; this skill uses Performance Insights only to identify cost waste),
    or Aurora failover operations (use aurora-failover-operator).
  activation_triggers:
  - optimise Aurora cost
  - right-size Aurora instance
  - Aurora Serverless v2 ACU
  - Aurora I/O-Optimized
  - Aurora Standard vs I/O-Optimized
  - Aurora Reserved Instance
  - Aurora Global Database cost
  - Aurora backtrack cost
  - Aurora vs RDS cost
  - Aurora Limitless Database cost
  - Aurora reader replica sizing
  - Aurora storage optimization
  - Aurora Performance Insights waste
  - Aurora idle ACU
  - Aurora FinOps review
  invocation_schema: 'Input: either (a) an Aurora cluster identifier + live-account context, (b) a cluster configuration document (engine, instance classes, ACU range, storage, I/O volume, Multi-AZ, pricing
    model, Performance Insights summary), OR (c) a fleet description for batch optimisation. Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block
    per cluster, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL}.'
  invocation_example: "# Minimal valid input (offline classification):\nCluster: orders-prod-cluster\nEngine: aurora-mysql (8.0)\nRegion: us-east-1\nInstances:\n  - writer: db.r6g.2xlarge (8 vCPU, 64 GB)\n\
    \  - reader-1: db.r6g.2xlarge\n  - reader-2: db.r6g.2xlarge\nStorage: Standard tier, 800 GB used\nI/O (last 30 days): 18,000,000 I/O requests\nPricing: On-Demand (no RI)\nCloudWatch metrics (last 30\
    \ days):\n  - writer CPUUtilization: avg=15%, max=28%\n  - reader CPUUtilization: avg=8%, max=18%\n  - DatabaseConnections (writer): avg=40, max=80\nPerformance Insights:\n  - writer DBLoad: avg=1.2,\
    \ max=4.5 (low for 8 vCPU)\n  - top-SQL: 1 query = 40% of DBLoad (missing index)\nEmit the standard optimisation block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# Aurora Cost Optimizer

## What this skill does

Optimises Amazon Aurora cluster cost across seven dimensions: instance
right-sizing, Aurora Serverless v2 ACU tuning, Aurora I/O-Optimized
storage tier selection, storage and snapshot cleanup, Global Database
replica cost, backtrack storage cost, and Performance Insights waste
detection. Emits a deterministic verdict per cluster with estimated
monthly savings and a one-dimension-per-window migration plan.

## STRICT output contract

Every invocation MUST emit exactly one optimisation block per cluster
in this shape — no prose before, no commentary after:

```text
TARGET: <cluster-identifier>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <instance-class, ACU range, storage tier, I/O volume,
            pricing model, Global DB, backtrack>
  Proposed: <per-dimension list of changes>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (right-sizing): $<amount>
  Monthly (ACU tuning): $<amount>
  Monthly (I/O-Optimized tier): $<amount>
  Monthly (storage/snapshot): $<amount>
  Monthly (Global DB): $<amount>
  Monthly (backtrack): $<amount>
  Monthly (RI/commit): $<amount>
  Annual total: $<amount>
  Assumptions: <pricing region, 730h/month, etc.>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <cluster>. Proceed? (yes/no)"
```

A block missing VERDICT, RECOMMENDATION, ESTIMATED_SAVINGS, or
MIGRATION_STEPS is a contract violation — re-emit the full block.

## Quick start

- **Aurora I/O-Optimized is the highest-leverage 2024+ feature for
  I/O-heavy workloads.** It charges a flat rate per GB of storage (no
  per-I/O-request fee). Workloads with > 3-5x I/O-to-storage cost ratio
  typically save 40-60% on the I/O line. The trade-off: storage cost is
  ~50-70% higher per GB; for low-I/O workloads, Standard stays cheaper.
- **Aurora Serverless v2 ACU min is a recurring bill.** A cluster with
  `ServerlessV2ScalingConfiguration.MinCapacity=8` pays for 8 ACU × 730h
  even at zero load. Most workloads can drop min to 1-2 ACU and rely on
  auto-scaling; the floor only matters for sub-second latency SLAs.
- **Writer + reader right-sizing are independent.** Readers can run on
  a smaller instance class than the writer because they don't bear the
  write/commit load. A common waste pattern is mirrored `db.r6g.2xlarge`
  on all replicas when the readers cruise at < 10% CPU.
- **Aurora vs RDS: Aurora is slightly pricier per compute unit but
  free Multi-AZ replication and faster failover often net out cheaper.**
  Don't migrate for compute savings alone — migrate for HA / reader
  scale / storage auto-scaling.
- **Reserved Instances are Aurora's biggest single lever for steady-
  state clusters.** A 1-yr no-upfront RI on `db.r6g.2xlarge` yields
  ~40% discount vs On-Demand; a 3-yr is ~60%. Apply to the writer and
  primary readers only — don't commit on burst-readers.

## Mindset

Aurora's cost structure differs from RDS in three ways: I/O is metered
per request (Standard) or rolled into storage (I/O-Optimized), Multi-AZ
replication is free (storage-layer), and storage auto-scales in 10-GB
increments. The levers are I/O tier, Serverless v2 ACU floor, reader
instance-class separation, and RI commits. Most Aurora waste comes
from (a) Standard tier when I/O-Optimized is cheaper, (b) over-floored
Serverless v2 ACU, or (c) readers mirrored to the writer's class.

## Quick reference — verdict thresholds

| Observation | Verdict | Dimension |
|---|---|---|
| I/O cost > storage cost on Standard tier | **OPPORTUNITY_FOUND** | I/O-Optimized tier |
| Serverless v2 MinCapacity > 2 ACU with avg CPU < 10% | **OPPORTUNITY_FOUND** | ACU tuning |
| Writer CPU avg < 20% on db.r6g.2xlarge+ | **OPPORTUNITY_FOUND** | Right-sizing |
| Reader CPU avg < 10% on same class as writer | **OPPORTUNITY_FOUND** | Reader right-sizing |
| Aurora cluster On-Demand, no RI, uptime > 6 months steady | **OPPORTUNITY_FOUND** | Reserved Instance |
| Global DB read replica CPU avg < 5% in DR region | **OPPORTUNITY_FOUND** | Global DB right-sizing |
| Backtrack enabled with > 100 GB change volume | **OPPORTUNITY_FOUND** | Backtrack storage |
| Manual snapshots > 90 days old, no retention policy | **OPPORTUNITY_FOUND** | Storage cleanup |
| Top-SQL = > 30% of DBLoad on missing index | **OPPORTUNITY_FOUND** | Performance Insights |
| All seven dimensions at cost-optimal config | **ALREADY_OPTIMAL** | (continue monitoring) |

## Pre-flight: data gate (run before any optimisation decision)

Aurora optimisation requires four data sources: Cost Explorer for
billing line items, cluster configuration (instances, ACU, storage,
I/O), CloudWatch metrics for utilisation, and Performance Insights for
DBLoad top-SQL.

### Required data sources

```bash
# 1. Aurora cost breakdown (last 30 days)
START=$(date -u -v-30d +%F 2>/dev/null || date -u -d '-30 days' +%F)
END=$(date -u +%F)
aws ce get-cost-and-usage \
  --time-period Start=$START,End=$END \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Aurora"]}}' \
  --granularity MONTHLY --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE --output json > aurora-cost.json

# 2. Cluster + instance + global + RI topology
aws rds describe-db-clusters --output json > aurora-clusters.json
aws rds describe-db-instances \
  --filters Name=engine,Values=aurora-mysql,aurora-postgresql \
  --output json > aurora-instances.json
aws rds describe-global-clusters --output json > aurora-global.json
aws rds describe-reserved-db-instances --output json > aurora-ris.json

# 3. Backtrack inventory (clusters with backtrack enabled)
for cluster in $(jq -r '.DBClusters[].DBClusterIdentifier' aurora-clusters.json); do
  aws rds describe-db-cluster-backtracks --db-cluster-identifier $cluster --output json
done > aurora-backtracks.json

# 4. CloudWatch CPU + Performance Insights top-SQL (per instance)
START_CW=$(date -u -v-30d +%FT%TZ 2>/dev/null || date -u -d '-30 days' +%FT%TZ)
END_CW=$(date -u +%FT%TZ)
for inst in $(jq -r '.DBInstances[].DBInstanceIdentifier' aurora-instances.json); do
  aws cloudwatch get-metric-statistics --namespace AWS/RDS \
    --metric-name CPUUtilization \
    --dimensions Name=DBInstanceIdentifier,Value=$inst \
    --start-time $START_CW --end-time $END_CW \
    --period 3600 --statistics Average Maximum --output json
  aws pi describe-dimension-keys --service-type RDS --identifier $inst \
    --start-time $START_CW --end-time $END_CW \
    --metric db.load.avg --group-by Group=db.sql --output json
done > aurora-cpu-pi.json
```

### Data-quality short-circuits

| Condition | Effect on optimisation |
|---|---|
| Cost Explorer access denied | NEED_MORE_INFO for cost quantification; topology still analysable. |
| Observation window < 14 days | NEED_MORE_INFO: workload may reflect atypical load. Min 14 days; 30 preferred. |
| Performance Insights not enabled | NEED_MORE_INFO for DBLoad / top-SQL; right-sizing still works from CPU. |
| Aurora cluster in `creating` / `modifying` / `failing-over` | Wait for `available` before emitting a change recommendation. |
| Serverless v2 with auto-pause enabled | Min ACU floor is 0 when paused; don't flag the floor as waste. |
| I/O-Optimized already enabled | Skip the I/O tier dimension — already optimal. |
| Cluster part of Aurora Limitless Database | Route to Step 10 (Limitless) — standard right-sizing does not apply. |

## Process — Optimisation logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

- **Aurora I/O-Optimized charges per GB of storage, not per I/O request.**
  Standard tier: ~$0.10/GB-month storage + ~$0.20/million I/O requests.
  I/O-Optimized tier: ~$0.18/GB-month storage + $0 I/O. Break-even is
  when I/O cost > storage price differential. For 1,000 GB doing 500M
  I/O/month: Standard ~$100 + ~$100 = $200; I/O-Optimized ~$180 —
  I/O-Optimized wins. At 50M I/O: Standard ~$90; I/O-Optimized ~$180 —
  Standard wins.

- **Aurora Serverless v2 ACU = compute + memory bundled.** 1 ACU ≈ 2
  vCPU / 16 GB. MinCapacity is the floor; the cluster bills at the ACU
  value averaged per hour. A cluster at MinCapacity=8 when it could sit
  at MinCapacity=2 wastes 6 ACU × $0.12/h × 730h = $525/month.

- **Aurora writer and readers are billed independently.** The writer
  instance class can differ from readers. A common waste pattern is
  mirroring `db.r6g.2xlarge` on all replicas "for symmetry," when
  readers cruise at < 10% CPU.

- **Aurora Multi-AZ replication is free; RDS Multi-AZ is $0.01/GB.**
  For high-write workloads, migrating RDS Multi-AZ to Aurora eliminates
  this data-transfer charge.

- **Aurora Global Database replication traffic is free; the secondary-
  region read replicas bill as full Aurora instances at the secondary
  region's rate.** Right-size DR-region instances independently of the
  primary.

- **Backtrack storage is billed per GB-month of change log.** Every
  change is stored. High-change workloads with backtrack enabled can
  rack up significant charges; tune the backtrack window.

- **Reserved Instances apply to a specific instance class + engine +
  region.** A `db.r6g.2xlarge` Aurora PostgreSQL RI does NOT apply to
  `db.r6g.large` or to Aurora MySQL. Match the RI to the longest-
  running instance class.

- **Aurora Limitless Database (2024+) adds compute shard cost.** Each
  shard is an Aurora instance; right-sizing shards and the router (SLG)
  is the cost lever — different from standard right-sizing.

- **Performance Insights top-SQL identifies the query driving 30%+ of
  DBLoad.** Fixing it (e.g., adding an index) reduces DBLoad and often
  lets the cluster downsize — turning a DBA task into a cost saving.

### Step 1: Validate input and data sufficiency

If Cost Explorer access is unavailable AND the caller has not pasted
billing line items, emit NEED_MORE_INFO:

```text
TARGET: <cluster-identifier>
VERDICT: NEED_MORE_INFO
REASON: Cost Explorer access is required to quantify per-dimension
  savings. Without USAGE_TYPE granularity (Aurora:InstanceUsage,
  Aurora:StorageUsage, Aurora:IOUsage, Aurora:ServerlessUsage), the
  seven dimensions can be analysed qualitatively but the dollar
  savings cannot be computed.
RECOMMENDATION:
  1. Grant the auditor role `ce:GetCostAndUsage`.
  2. Or, paste the top 10 Aurora USAGE_TYPE line items from the
     last 30 days of CUR.
ESTIMATED_SAVINGS: $0 (cannot quantify without CUR data)
MIGRATION_STEPS:
  - IAM policy addition:
    {"Effect":"Allow",
     "Action":["ce:GetCostAndUsage","ce:GetDimensionValues"],
     "Resource":"*"}
```

### Step 2: Cost Explorer reconciliation

```bash
aws ce get-cost-and-usage \
  --time-period Start=$START,End=$END \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Aurora"]}}' \
  --output json | \
  jq '.ResultsByTime[].Groups[] | {usage: .Keys[0],
    cost: (.Metrics.BlendedCost.Amount | tonumber)}'
```

| USAGE_TYPE | Dimension | What it represents |
|---|---|---|
| `Aurora:InstanceUsage` | Compute (provisioned) | Per-instance-hour by class |
| `Aurora:ServerlessUsage` | Compute (Serverless v2) | Per-ACU-hour |
| `Aurora:StorageUsage` | Storage | Per-GB-month |
| `Aurora:IOUsage` | I/O (Standard tier) | Per-million I/O requests |
| `Aurora:BackupUsage` | Backtrack / snapshots | Per-GB-month |
| `Aurora:ReplicaUsage` | Cross-region replicas | Per-replica-instance-hour |

If `Aurora:IOUsage` is > 30% of total Aurora bill AND the cluster is on
Standard tier, I/O-Optimized is a prime candidate. If
`Aurora:ServerlessUsage` dominates with low CPU, ACU floor is too high.

### Step 3: Cost classification

| Cost profile | Indicators | Emphasis |
|---|---|---|
| I/O-heavy | Aurora:IOUsage > 30% of total | I/O-Optimized tier (Step 6) |
| Serverless waste | ServerlessUsage high, CPU < 10% | ACU min tuning (Step 5) |
| Compute-heavy, low CPU | InstanceUsage high, avg CPU < 20% | Right-sizing (Step 4) |
| Compute-heavy, On-Demand | No RI, uptime > 6 months | Reserved Instance (Step 11) |
| Storage / backtrack creep | StorageUsage/BackupUsage growing | Storage cleanup (Step 7) |
| Global DB DR | ReplicaUsage in DR region, CPU < 5% | Replica right-sizing (Step 8) |
| Mixed (no single dimension > 30%) | Even distribution | Apply all dimensions in parallel |

### Step 4: Instance-class right-sizing

**Decision matrix:**

| CPU profile (30-day) | Recommendation | Savings estimate |
|---|---|---|
| Writer avg < 20%, max < 40% on db.r6g.2xlarge | Downsize to db.r6g.xlarge | ~50% of writer compute |
| Writer avg 20-50%, max < 70% | Keep current class | None |
| Writer avg > 70% frequently | Upsize (DBLoad is the constraint) | None — already maxed |
| Reader avg < 10%, max < 20% on same class as writer | Downsize reader one step | 40-60% of reader compute |
| Reader avg < 5% | Consider removing the reader | 100% of that reader |
| Reader avg > 60% (e.g., analytics reader) | Keep current class; consider read-scaling | None |
| Burstable db.t4g with frequent CPU credit exhaustion | Move to db.r6g (unlimited is more expensive) | Variable |

**Worked example — writer + reader right-sizing:**

Cluster with writer `db.r6g.2xlarge` ($1.00/h in us-east-1) and two
readers `db.r6g.2xlarge` (mirrored). Writer CPU avg=15%, max=28%;
readers CPU avg=8%, max=18%. Right-size writer to `db.r6g.xlarge`
($0.50/h) and readers to `db.r6g.large` ($0.25/h):
- Writer: ($1.00 - $0.50) × 730h = $365/month
- Each reader: ($1.00 - $0.25) × 730h = $547.50/month
- Total monthly savings: $365 + $547.50 × 2 = $1,460/month
- Trade-off: writer has less headroom for traffic spikes. Confirm max
  CPU stays < 70% after the downsize; otherwise keep writer at 2xlarge.

### Step 5: Aurora Serverless v2 ACU tuning

**Decision matrix:**

| ACU observation | Recommendation | Savings |
|---|---|---|
| MinCapacity > 2, avg CPU < 10% | Drop MinCapacity to 1-2 ACU | (Min−2) × $0.12 × 730 |
| MinCapacity = 0 with auto-pause | Already optimal | None |
| MaxCapacity >> peak ACU reached | Lower MaxCapacity to peak+20% | None directly; limits scaling failure |
| ACU at Min > 50% of hours | Workload is steady; migrate to provisioned | Provisioned cheaper if steady |
| ACU spikes brief but high | Keep MaxCapacity; tune Min down | Per above |

**Worked example — Serverless v2 ACU floor:**

Cluster with MinCapacity=8, MaxCapacity=32, avg ACU=4.5 over 30 days,
peak ACU=14. Drop MinCapacity to 2 (MaxCapacity stays at 32):
- Current floor: 8 ACU × $0.12 × 730h = $700.80/month minimum
- New floor: 2 ACU × $0.12 × 730h = $175.20/month minimum
- Actual billed ACU drops by ~3.5 ACU average → ~3.5 × $0.12 × 730 =
  $306.60/month savings
- Trade-off: sub-second response on cold-start; verify p99 latency
  stays within SLA during scale-up events.

### Step 6: Aurora I/O-Optimized tier

**Break-even calculation:**

```
Standard_monthly = (storage_GB × $0.10) + (IO_millions × $0.20)
IOOptimized_monthly = storage_GB × $0.18

break_even_IO_millions = (storage_GB × ($0.18 - $0.10)) / $0.20
                      = storage_GB × 0.4
```

| Storage (GB) | Break-even I/O (millions/month) | Example workload |
|---|---|---|
| 100 | 40M | Small db, dev/test |
| 500 | 200M | Mid-size OLTP |
| 1,000 | 400M | Standard production |
| 5,000 | 2,000M | Large production |

If actual I/O exceeds break-even, I/O-Optimized is cheaper.

**Worked example — I/O-Optimized migration:**

Aurora PostgreSQL cluster, 1,000 GB storage, 600M I/O requests/month.
- Standard: 1,000 × $0.10 + 600 × $0.20 = $100 + $120 = $220/month
- I/O-Optimized: 1,000 × $0.18 + $0 = $180/month
- Monthly savings: $40
- Annual savings: $480
- Switch with `modify-db-cluster --storage-type aurora-iopt1` (Aurora
  PostgreSQL 14+/MySQL 8+); non-disruptive, takes effect within minutes.

If I/O is only 200M/month, Standard stays cheaper:
- Standard: $100 + $40 = $140
- I/O-Optimized: $180
- Stay on Standard.

### Step 7: Storage, snapshot, and backtrack cleanup

| Observation | Recommendation | Savings |
|---|---|---|
| Manual snapshots > 90 days, no retention policy | Apply 30/60/90-day tiered cleanup | $0.095/GB-month per snapshot removed |
| Automated snapshots retained after cluster deletion | Convert to manual if needed, or delete | Same |
| Backtrack window > 24h on high-change cluster | Reduce to 24h (default); backtrack storage is per-GB-month of change log | Variable |
| Backtrack never used in 90 days | Disable backtrack; rely on snapshots | Full backtrack storage |
| Backtrack + frequent snapshots both active | Pick one — both is redundant | Backtrack storage |
| Volume growth > 10%/month with no lifecycle | Add data archival to S3 Glacier | Storage cost delta |
| Aurora storage unused after large DELETE | Aurora auto-shrinks in 10-GB increments; verify | None — automatic |

### Step 8: Aurora Global Database cost

| Observation | Recommendation | Savings |
|---|---|---|
| DR-region reader CPU < 5% | Downsize DR reader one step | ~30-50% of DR instance |
| DR-region reader idle > 90% of time | Cross-region read replica vs full Global DB | Variable |
| Global DB but no DR test in 12 months | Validate DR; if unused, evaluate removal | Full DR cluster cost |
| Multi-region writes (active-active) | Keep Global DB; right-size per region | N/A |

### Step 9: Performance Insights waste detection

`pi describe-dimension-keys` returns top-SQL by DBLoad. A single query
> 30% of DBLoad often indicates a missing index or inefficient join.
Fixing it can enable a further downsize.

| Top-SQL profile | Recommendation | Cost impact |
|---|---|---|
| Single query > 30% of DBLoad, missing index | DBA adds index → DBLoad drops → cluster can downsize | 25-50% of compute via downsize |
| Top-SQL is full-table scan | DBA optimises query plan | Same |
| Top-SQL is lock wait | Investigate transaction isolation / lock contention | Improves latency, enables downsize |
| Top-SQL is commit/sync (fsync) | Already write-bound; keep instance class | None |
| Top-SQL evenly distributed | Query tuning won't help; right-size only | None from PI |

### Step 10: Aurora Limitless Database cost (2024+)

Each shard is an Aurora instance with a routing layer (SLG). Cost
levers differ from standard right-sizing.

| Limitless observation | Recommendation | Savings |
|---|---|---|
| Shards at low CPU < 10% | Consolidate shards | Per-shard instance cost |
| Router (SLG) over-provisioned | Right-size router instance | Per-instance |
| Single-shard workload, never horizontal-scaled | Migrate from Limitless to standard Aurora | Limitless premium |
| Cross-shard queries frequent | Reconsider shard key | Variable |

### Step 11: Reserved Instance evaluation

```bash
aws rds describe-reserved-db-instances-offerings \
  --db-instance-class db.r6g.2xlarge \
  --product-description "aurora postgresql" \
  --offering-type "No Upfront" --duration 31536000 --output json
```

| Pattern | Recommendation | Savings vs On-Demand |
|---|---|---|
| Aurora On-Demand, uptime > 6 months, steady load | 1-yr No Upfront RI on writer + primary readers | ~40% |
| Aurora On-Demand, uptime > 18 months, mission-critical | 3-yr No Upfront or Partial Upfront | ~60% |
| Burst-reader with spiky load | Keep On-Demand (RI wastes on idle) | None |
| Cluster scheduled for migration in < 6 months | No RI (commit outlasts the cluster) | None |
| Multiple clusters with mixed instance classes | RI each longest-running class separately | Per class |

### Step 12: Final verdict

The verdict is the worst-case (most-actionable) finding across all
seven dimensions:

- If ANY dimension has a concrete recommendation with quantified
  savings, verdict is **OPPORTUNITY_FOUND**.
- If a change was applied and verified this session, verdict is
  **OPTIMIZED**.
- If all dimensions are at cost-optimal config AND RI evaluation has
  been considered, verdict is **ALREADY_OPTIMAL**.

## Output format

### Worked example — multi-dimension opportunity

```text
TARGET: orders-prod-cluster
VERDICT: OPPORTUNITY_FOUND
REASON: CE shows I/O 35% of Aurora bill ($420/month on 600M I/O
  requests vs $200 storage on Standard tier), writer CPU avg 15%
  / max 28% on db.r6g.2xlarge, readers mirrored at avg 8% CPU,
  and no RI on a cluster running 14 months steady-state. Four
  dimensions have actionable opportunities.
RECOMMENDATION:
  Current:
    Compute: writer db.r6g.2xlarge ($730), 2 readers db.r6g.2xlarge
      each ($730 each)
    Storage: Standard, 1,000 GB × $0.10 = $100/month
    I/O: 600M × $0.20 = $120/month (CE shows $420 incl. overhead)
    Pricing: On-Demand (no RI); Global DB: not in use; backtrack: off
  Proposed:
    - Right-sizing: writer → db.r6g.xlarge ($0.50/h) per CPU 15/28%;
      readers → db.r6g.large ($0.25/h) per CPU 8/18%.
    - I/O tier: I/O-Optimized — 600M I/O exceeds the 400M break-even
      for 1,000 GB storage.
    - RI: 1-yr No Upfront RI on the new writer class once right-size
      is applied; hold on reader RI until reader count stabilises.
    - Performance Insights: top-SQL = orders_join_by_customer at 38%
      of DBLoad (missing index on orders.customer_id). DBA ticket.
  Confidence: HIGH — CE confirms I/O share; CloudWatch confirms CPU
    headroom; PI confirms top-SQL dominance.
ESTIMATED_SAVINGS:
  Monthly (right-sizing): $1,095  (writer $365 + 2 readers $730)
  Monthly (I/O-Optimized): $40    ($220 Standard → $180 I/O-Optimized)
  Monthly (RI on writer): $146    (40% off db.r6g.xlarge $365)
  Monthly (Global DB / backtrack): $0
  Annual total: $15,372
  Assumptions: us-east-1 pricing, 730h/month, right-size occurs
    before RI purchase so RI matches the new instance class.
MIGRATION_STEPS:
  1. Snapshot the cluster before any change:
     aws rds create-db-cluster-snapshot \
       --db-cluster-identifier orders-prod-cluster \
       --db-cluster-snapshot-identifier pre-opt-$(date +%s)
  2. Right-size the writer:
     aws rds modify-db-instance \
       --db-instance-identifier orders-prod-writer \
       --db-instance-class db.r6g.xlarge --apply-immediately
     # Wait for status=available; verify CPU stays < 70% in 24h
  3. Right-size readers one at a time (keep one full-size for failover):
     aws rds modify-db-instance \
       --db-instance-identifier orders-prod-reader-1 \
       --db-instance-class db.r6g.large --apply-immediately
  4. Switch to I/O-Optimized tier (non-disruptive, separate window):
     aws rds modify-db-cluster \
       --db-cluster-identifier orders-prod-cluster \
       --storage-type aurora-iopt1 --apply-immediately
  5. After right-size settles (7 days), purchase RI on writer:
     aws rds purchase-reserved-db-instances-offering \
       --reserved-db-instances-offering-id <offering-id> \
       --reserved-db-instance-id orders-writer-ri-1yr
  6. File DBA ticket for the missing index on orders.customer_id.
CONFIRM: Before each state-changing CLI, emit and await operator
  approval. Stage changes one dimension per window; never batch
  the writer right-size + I/O tier switch.
```

### Worked example — already optimal

```text
TARGET: reporting-cluster-prod
VERDICT: ALREADY_OPTIMAL
REASON: All seven dimensions verified at cost-optimal config:
  Aurora I/O-Optimized enabled; Serverless v2 Min=2/Max=16 with
  steady ACU 6-10; writer and readers rightsized to CPU avg 45%;
  1-yr RI on writer and primary reader; no Global DB waste; no
  backtrack; Performance Insights top-SQL evenly distributed.
RECOMMENDATION:
  Current: All dimensions optimal
  Proposed: no change
  Confidence: HIGH — CE confirms 30-day spending pattern stable;
    Performance Insights shows no dominant SQL.
ESTIMATED_SAVINGS:
  Monthly (all dimensions): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Continue monthly CE review.
  - Re-evaluate at next growth forecast — Serverless v2 Max may
    need to scale if reader count doubles.
```

## Anti-Patterns — NEVER do these things

- **NEVER recommend Aurora I/O-Optimized without computing the
  break-even.** I/O-Optimized raises storage cost ~70%; for low-I/O
  workloads it makes the bill WORSE. Always compute the break-even
  I/O count for the current storage volume first.

- **NEVER recommend dropping Aurora Serverless v2 MinCapacity below
  the workload's cold-start SLA.** Sub-second latency requirements
  may demand MinCapacity ≥ 4. Always confirm the p99 latency tolerance
  before tuning the floor.

- **NEVER recommend a 3-year RI on a cluster with active migration
  plans.** The RI outlasts the cluster and the commitment is billed
  whether or not the cluster exists. Match RI term to expected
  cluster lifetime.

- **NEVER recommend right-sizing an Aurora writer based solely on
  CPUUtilization.** CPU headroom doesn't catch write-queue / commit-
  sync saturation. Always cross-check Performance Insights DBLoad and
  buffer-cache hit ratio before downsizing the writer.

- **NEVER migrate RDS to Aurora solely for cost.** Aurora is slightly
  more expensive per compute unit; the cost wins come from I/O tier,
  free Multi-AZ replication, and reader scale. Trigger migration for
  HA / performance / storage auto-scaling reasons; treat cost as a
  secondary benefit.

- NEVER recommend removing a Global Database reader in the DR region
  without confirming the DR RTO/RPO requirements.
- NEVER recommend disabling backtrack without confirming the operator's
  recovery strategy. Backtrack is the fastest undo; snapshots are slower.
- NEVER right-size readers below the failover-promotion size if they
  are failover targets.
- NEVER apply the I/O-Optimized tier switch and a major version upgrade
  in the same maintenance window — both modify the cluster.
- NEVER purchase an RI for a Serverless v2 ACU. RIs apply to provisioned
  instance classes only; Serverless v2 spends via ACU-hours with no
  commit discount.

## Quick navigation

| You want to... | Jump to |
|---|---|
| Evaluate I/O-Optimized vs Standard | Step 6 — I/O-Optimized tier |
| Tune Serverless v2 ACU floor | Step 5 — ACU tuning |
| Right-size writer / readers | Step 4 — Instance right-sizing |
| Decide on a Reserved Instance | Step 11 — RI evaluation |
| Audit storage / snapshot / backtrack | Step 7 — Storage cleanup |
| Right-size Global DB DR | Step 8 — Global Database |
| Identify waste-driving SQL | Step 9 — Performance Insights |
| Handle missing data | Step 1 — Validate input |
| Look up pricing / instance classes | references/aurora-pricing-reference.md |

## Expert heuristic — the 60-second triage

When handed an Aurora bill and asked "why is this so high?", run this
60-second triage before deep-diving any single dimension:

1. **Pull CE Aurora USAGE_TYPE breakdown.** If `Aurora:IOUsage` > 30%
   on Standard tier, deep-dive Step 6 (I/O-Optimized).
2. **Pull cluster inventory + ACU config.** Serverless v2 with
   MinCapacity > 2 and low CPU = guaranteed ACU floor waste.
3. **Pull writer / reader CPU.** Avg CPU < 20% on a large instance
   class = right-size opportunity.
4. **Pull RI inventory.** Long-running clusters On-Demand with no RI
   = RI opportunity.
5. **Pull Performance Insights top-SQL.** One query > 30% of DBLoad =
   waste-driving SQL that, once fixed, enables further rightsizing.
6. **Pull Global DB + backtrack.** DR region CPU < 5% or backtrack
   window > 24h on high-change = cleanup opportunity.

If any of the six checks hits, deep-dive the corresponding step. If all
six pass, the cluster is likely ALREADY_OPTIMAL — verify with the full
ordered process.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`modify-db-cluster`, `modify-db-instance`, `create-db-cluster-
  snapshot`, `delete-db-snapshot`, `purchase-reserved-db-instances-
  offering`), emit and await operator approval.
- **Snapshot before any change.** Capture a cluster snapshot:
  ```bash
  aws rds create-db-cluster-snapshot \
    --db-cluster-identifier $CLUSTER \
    --db-cluster-snapshot-identifier pre-opt-$(date +%s)
  ```
- **One dimension per maintenance window.** Right-size, I/O tier
  switch, and RI purchase each alter cost / capacity; stacking them
  obscures which change produced any observed impact.
- **Verify writer CPU after downsize.** Watch CPUUtilization for 24h;
  if avg exceeds 70%, roll back to the prior instance class.
- **Reader right-size one at a time.** Keep one reader at full size
  during the transition so failover capacity is preserved.
- **Bulk-operation safety limit.** When optimising a fleet of clusters:
  sort by estimated savings (largest first); slice into batches of at
  most 3 clusters; emit per-cluster MIGRATION_STEPS with a single
  CONFIRM per batch; re-query with `describe-db-clusters` and verify
  availability before emitting the NEXT batch; abort the sweep if any
  cluster fails to stabilise within 30 min. The skill MUST NOT emit
  remediation CLI for more than 3 clusters in a single output block.

## Verdict semantics

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension has a savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; CE line items confirm the new pattern. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All seven dimensions at cost-optimal config AND RI evaluation considered. | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed: CE access denied, PI not enabled, window < 14 days. | Pre-decision — emit per-dimension; other dimensions can still emit OPPORTUNITY_FOUND. |

## Recent AWS features (2024-2026)

- **Aurora I/O-Optimized (2024):** Flat-rate storage tier eliminating
  per-I/O-request charges. Break-even at ~0.4M I/O per GB of storage
  per month. Switch via `modify-db-cluster --storage-type aurora-iopt1`.
- **Aurora Limitless Database (2024+):** Horizontal sharding with a
  routing layer (SLG). Cost premium per shard; right-size shards and
  the router instance.
- **Aurora Serverless v2 ACU seconds-level billing (2023-2024):**
  Per-second ACU billing with 1-minute minimum. MinCapacity floor is
  the dominant cost lever.
- **Aurora Global Database managed planned failover (2024):** Engine-
  level planned failover preserving replication topology; no cost change.
- **Aurora PostgreSQL 16 / MySQL 8.4 (2024-2025):** Verify RI product-
  description matches the new engine before purchase.
- **Performance Insights anomaly detection (2024-2025):** Automatic
  DBLoad anomaly flagging. Aurora Zero-ETL to Redshift (2024-2025)
  offloads analytics from OLTP readers; cost is Redshift-side.

## AWS documentation

Domain: AWS CloudOps / Databases — Amazon Aurora cost optimisation.

- **Amazon Aurora pricing** — https://aws.amazon.com/rds/aurora/pricing/
- **Aurora I/O-Optimized** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/Aurora.Overview.Storage.html
- **Aurora Serverless v2** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-serverless-v2.html
- **Aurora Limitless / Global Database** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/aurora-limitless.html
- **Aurora Backtrack** — https://docs.aws.amazon.com/AmazonRDS/latest/AuroraUserGuide/AuroraMySQL.Managing.Backtrack.html
- **Performance Insights** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_PerfInsights.html
- **Reserved Instances** — https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_WorkingWithReservedDBInstances.html
- **AWS Cost Explorer** — https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
- **Well-Architected — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
