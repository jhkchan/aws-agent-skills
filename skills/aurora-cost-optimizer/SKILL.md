---
name: aurora-cost-optimizer
description: Optimises Amazon Aurora cluster cost across seven dimensions — instance-class right-sizing for Aurora Standard (db.r6/r7 vs db.t3/t4 burstable), Aurora Serverless v2 ACU min/max tuning (eliminate idle ACU floor, scale to peak), Aurora I/O-Optimized storage tier (flat-rate I/O for I/O-heavy workloads, 40-60% I/O cost reduction vs Standard), storage and automated snapshot cleanup, Global Database cross-region read-replica instance cost, backtrack storage cost, Performance Insights waste detection (top-SQL tuning targets that reduce instance-class requirements), and Reserved Instance vs On-Demand (1-yr/3-yr commit break-even). Distinguishes Aurora vs RDS for cost (Aurora slightly higher per unit but better HA/performance; free Multi-AZ replication). Covers Aurora Limitless Database (2024+) horizontal sharding cost trade-offs. Emits OPTIMIZED, OPPORTUNITY_FOUND, or ALREADY_OPTIMAL per cluster with estimated monthly savings. Use when reviewing Aurora spend, tuning Serverless v2 ACU, evaluating I/O-Optimized.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted cluster configuration, Performance Insights summaries, and billing line items. Live-account optimisation uses aws rds describe-db-clusters, describe-db-instances, describe-global-clusters, describe-db-proxies, aws pi describe-dimension-keys and get-resource-metrics for DBLoad top-SQL, aws ce get-cost-and-usage filtered to Amazon Aurora USAGE_TYPEs (Aurora:InstanceUsage...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Reviewing Amazon Aurora cluster spend, right-sizing Aurora writer and reader instance classes, tuning Aurora Serverless v2 ACU min and max, evaluating Aurora I/O-Optimized vs Standard storage tier, sizing Aurora Global Database read replicas, auditing backtrack storage cost, using Performance Insights to identify waste-driving SQL, deciding between On-Demand and Reserved Instances for steady-state Aurora, or evaluating Aurora Limitless Database for horizontal scaling workloads.
  when_not_to_use: RDS for MySQL/PostgreSQL/Oracle/SQL Server cost optimisation (use rds-cost-optimizer — this skill is Aurora-specific), DynamoDB capacity-mode optimisation (use a DynamoDB specialist), Redshift cluster right-sizing, query performance tuning as the primary goal (use a DBA / Performance Insights query-tuning workflow; this skill uses Performance Insights only to identify cost waste), or Aurora failover operations (use aurora-failover-operator).
  activation_triggers: optimise Aurora cost, right-size Aurora instance, Aurora Serverless v2 ACU, Aurora I/O-Optimized, Aurora Standard vs I/O-Optimized, Aurora Reserved Instance, Aurora Global Database cost, Aurora backtrack cost, Aurora vs RDS cost, Aurora Limitless Database cost, Aurora reader replica sizing, Aurora storage optimization, Aurora Performance Insights waste, Aurora idle ACU, Aurora FinOps review
  invocation_schema: 'Input: either (a) an Aurora cluster identifier + live-account context, (b) a cluster configuration document (engine, instance classes, ACU range, storage, I/O volume, Multi-AZ, pricing model, Performance Insights summary), OR (c) a fleet description for batch optimisation. Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block per cluster, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL}.'
  invocation_example: "# Minimal valid input (offline classification):\nCluster: orders-prod-cluster\nEngine: aurora-mysql (8.0)\nRegion: us-east-1\nInstances:\n  - writer: db.r6g.2xlarge (8 vCPU, 64 GB)\n  - reader-1: db.r6g.2xlarge\n  - reader-2: db.r6g.2xlarge\nStorage: Standard tier, 800 GB used\nI/O (last 30 days): 18,000,000 I/O requests\nPricing: On-Demand (no RI)\nCloudWatch metrics (last 30 days):\n  - writer CPUUtilization: avg=15%, max=28%\n  - reader CPUUtilization: avg=8%, max=18%\n  - DatabaseConnections (writer): avg=40, max=80\nPerformance Insights:\n  - writer DBLoad: avg=1.2, max=4.5 (low for 8 vCPU)\n  - top-SQL: 1 query = 40% of DBLoad (missing index)\nEmit the standard optimisation block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Amazon Aurora, Aurora MySQL, Aurora PostgreSQL, Aurora Serverless v2, Aurora I/O-Optimized, Aurora Limitless, Aurora Global Database, ACU, instance right-sizing, Performance Insights, DBLoad, Reserved Instance, backtrack, Aurora Standard, storage optimization, FinOps, database cost
  tags: aurora, databases, cost-optimization, finops, serverless, right-sizing
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

### Decision tree leading to the output

```text
1. Cost Explorer access available AND ≥14 days of data?
   ├─ NO  → VERDICT: NEED_MORE_INFO (emit the Step 1 template)
   └─ YES → go to 2
2. Aurora:IOUsage > 30% of total Aurora bill AND on Standard tier?
   ├─ YES → flag I/O-Optimized tier (Step 6); compute break-even
   └─ NO  → I/O tier ✓ — continue
3. Serverless v2 MinCapacity > 2 ACU AND avg CPU < 10%?
   ├─ YES → flag ACU floor tuning (Step 5)
   └─ NO  → ACU ✓ — continue
4. Writer CPU avg < 20% on db.r6g.2xlarge+ OR reader CPU avg < 10%
   on the writer's class?
   ├─ YES → flag right-sizing (Step 4); cross-check PI DBLoad
   └─ NO  → right-size ✓ — continue
5. Cluster On-Demand, uptime > 6 months, no RI?
   ├─ YES → flag RI evaluation (Step 11)
   └─ NO  → RI ✓ — continue
6. Manual snapshots > 90 days old OR backtrack window > 24h?
   ├─ YES → flag storage / backtrack cleanup (Step 7)
   └─ NO  → storage ✓ — continue
7. Any flag set?
   ├─ YES → VERDICT: OPPORTUNITY_FOUND; emit per-dimension $ savings
   └─ NO  → VERDICT: ALREADY_OPTIMAL
```

### FORBIDDEN output patterns

All seven FORBIDDEN output-pattern rules (no prose before TARGET, no OPPORTUNITY_FOUND with $0 savings, balanced savings math, break-even citation before recommending I/O-Optimized, RI term/offering-class/instance-class specifics, no writer right-size on CPU alone, full-precision intermediate math): [Error handling](references/error-handling.md).

## Quick start

Quick-start rules (I/O-Optimized leverage for I/O-heavy workloads, ACU min as a recurring bill, independent writer/reader right-sizing, Aurora vs RDS net-cost framing, RI as the biggest steady-state lever): [Advanced patterns](references/advanced-patterns.md).

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

The four required data-source CLI captures (Cost Explorer Aurora breakdown, cluster/instance/global/RI topology, backtrack inventory, per-instance CloudWatch CPU + Performance Insights top-SQL): [Diagnostic commands](references/diagnostic-commands.md).

### Data-quality short-circuits

Data-quality short-circuit table (CE access denied, window < 14 days, PI not enabled, transient cluster states, auto-pause floor, already I/O-Optimized, Limitless routing): [Advanced patterns](references/advanced-patterns.md).

## Process — Optimisation logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

All nine Step-0 non-obvious behaviours (I/O-Optimized per-GB pricing with break-even math, ACU = compute + memory bundle, independent writer/reader billing, free Multi-AZ replication, Global DB replica billing, backtrack change-log cost, RI class/engine/region binding, Limitless shard cost, PI top-SQL as a downsizing enabler): [Advanced patterns](references/advanced-patterns.md).

### Step 1: Validate input and data sufficiency

If Cost Explorer access is unavailable AND the caller has not pasted
billing line items, emit NEED_MORE_INFO:
NEED_MORE_INFO output template for missing Cost Explorer access (with the ce:GetCostAndUsage IAM remediation): [Error handling](references/error-handling.md).

### Step 2: Cost Explorer reconciliation

Cost Explorer reconciliation CLI, the USAGE_TYPE → dimension table, and the > 30% I/O / Serverless-dominance triggers: [Diagnostic commands](references/diagnostic-commands.md).

### Step 3: Cost classification

Cost-profile classification table (I/O-heavy, serverless waste, over-provisioned compute, RI candidate, storage/backtrack creep, Global DB DR, mixed): [Advanced patterns](references/advanced-patterns.md).

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
Worked example — writer db.r6g.2xlarge → xlarge and mirrored readers → large ($1,460/month): [Worked examples](references/worked-examples.md).

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
Worked example — MinCapacity 8 → 2 (~$306.60/month floor savings): [Worked examples](references/worked-examples.md).

### Step 6: Aurora I/O-Optimized tier

Break-even math (break_even_IO_millions = storage_GB × 0.4) and the per-storage-size break-even table: [Advanced patterns](references/advanced-patterns.md).

**Worked example — I/O-Optimized migration:**
Worked example — 1,000 GB + 600M I/O saves $40/month on I/O-Optimized; 200M I/O stays on Standard: [Worked examples](references/worked-examples.md).

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

RI-offering lookup CLI (describe-reserved-db-instances-offerings): [Diagnostic commands](references/diagnostic-commands.md).

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

### Worked example — multi-dimension opportunity with explicit cost breakdown

```text
TARGET: orders-prod-cluster
VERDICT: OPPORTUNITY_FOUND
REASON: CE shows I/O 35% of Aurora bill ($420/month on 600M I/O
  requests vs $200 storage on Standard tier), writer CPU avg 15%
  / max 28% on db.r6g.2xlarge, readers mirrored at avg 8% CPU,
  and no RI on a cluster running 14 months steady-state. Four
  dimensions have actionable opportunities.

CURRENT MONTHLY COST BREAKDOWN (us-east-1, 730h/month):
  Compute (instance right-size):
    Writer  db.r6g.2xlarge  8 vCPU/64 GB  $1.00/h × 730h = $730.00
    Reader1 db.r6g.2xlarge  8 vCPU/64 GB  $1.00/h × 730h = $730.00
    Reader2 db.r6g.2xlarge  8 vCPU/64 GB  $1.00/h × 730h = $730.00
                                                          ──────────
    Compute subtotal:                                    $2,190.00
  Storage (Standard tier):
    1,000 GB × $0.10/GB-month                            = $100.00
  I/O (Standard tier):
    600M requests × $0.20/million                        = $120.00
  Backup (automated snapshots + backtrack):
    800 GB snapshot storage × $0.095/GB-month            = $76.00
    Backtrack change log 120 GB × $0.095/GB-month        = $11.40
    Backup subtotal:                                      = $87.40
  Global DB:  not in use                                  = $0.00
  Reserved Instance discount: none (On-Demand)            = $0.00
                                                          ════════
  CURRENT MONTHLY TOTAL:                                $2,497.40

RECOMMENDATION:
  Current:
    Compute: writer db.r6g.2xlarge ($730), 2 readers db.r6g.2xlarge
      each ($730 each)
    Storage: Standard, 1,000 GB × $0.10 = $100/month
    I/O: 600M × $0.20 = $120/month (CE shows $420 incl. overhead)
    Backup: 800 GB automated snapshots + 120 GB backtrack = $87.40/month
    Pricing: On-Demand (no RI); Global DB: not in use; backtrack: on
  Proposed:
    - Right-sizing: writer → db.r6g.xlarge ($0.50/h) per CPU 15/28%;
      readers → db.r6g.large ($0.25/h) per CPU 8/18%.
    - I/O tier: I/O-Optimized — 600M I/O exceeds the 400M break-even
      for 1,000 GB storage (break-even = 1000 × 0.4 = 400M I/O/mo).
    - Backup: reduce backtrack window 72h → 24h (cuts 90 GB → 30 GB
      change log); tier manual snapshots to 30/60/90-day cleanup.
    - RI: 1-yr No Upfront RI on the new writer class once right-size
      is applied; hold on reader RI until reader count stabilises.
    - Performance Insights: top-SQL = orders_join_by_customer at 38%
      of DBLoad (missing index on orders.customer_id). DBA ticket.
  Confidence: HIGH — CE confirms I/O share; CloudWatch confirms CPU
    headroom; PI confirms top-SQL dominance.

ESTIMATED_SAVINGS:
  Monthly (right-sizing): $1,460.00
    writer: ($1.00 − $0.50) × 730h = $365.00
    2 readers: ($1.00 − $0.25) × 730h × 2 = $1,095.00
    Combined: $365.00 + $1,095.00 = $1,460.00
  Monthly (I/O-Optimized tier): $40.00
    Standard: $100 storage + $120 I/O = $220.00
    I/O-Optimized: $180 storage + $0 I/O = $180.00
    Saving: $220.00 − $180.00 = $40.00
  Monthly (backup/backtrack): $24.70
    Backtrack: 90 GB → 30 GB = 60 GB × $0.095 = $5.70
    Snapshots: 30/60/90 cleanup removes ~200 GB × $0.095 = $19.00
    Backup subtotal saving: $5.70 + $19.00 = $24.70
  Monthly (Global DB): $0.00 (Global DB not in use)
  Monthly (RI on writer): $146.00
    db.r6g.xlarge On-Demand $365/mo; 1-yr No-Upfront RI ≈ $219/mo
    Saving: $365 − $219 = $146/mo (40% off)
  ─────────────────────────────────
  Monthly total: $1,460.00 + $40.00 + $24.70 + $146.00 = $1,670.70
  Annual total: $1,670.70 × 12 = $20,048.40
  Assumptions: us-east-1 pricing, 730h/month, right-size occurs
    before RI purchase so RI matches the new instance class.

PROJECTED MONTHLY COST: $2,497.40 − $1,670.70 = $826.70

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
  5. Reduce backtrack window to 24h:
     aws rds modify-db-cluster \
       --db-cluster-identifier orders-prod-cluster \
       --backtrack-window 86400 --apply-immediately
  6. Delete manual snapshots older than 90 days (tiered cleanup):
     aws rds describe-db-snapshots --snapshot-type manual \
       --output json | jq -r '.DBSnapshots[] | select(.SnapshotCreateTime < "2026-05-12") | .DBSnapshotIdentifier'
     # Review list, then: aws rds delete-db-snapshot --db-snapshot-identifier <id>
  7. After right-size settles (7 days), purchase RI on writer:
     aws rds purchase-reserved-db-instances-offering \
       --reserved-db-instances-offering-id <offering-id> \
       --reserved-db-instance-id orders-writer-ri-1yr
  8. File DBA ticket for the missing index on orders.customer_id.
CONFIRM: Before each state-changing CLI, emit and await operator
  approval. Stage changes one dimension per window; never batch
  the writer right-size + I/O tier switch.
```

### Worked example — already optimal

Two worked examples (the identical ALREADY_OPTIMAL baseline, reporting-cluster-prod, preserved verbatim): [Worked examples](references/worked-examples.md).

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

The 60-second triage checklist (CE USAGE_TYPE breakdown, ACU config, writer/reader CPU, RI inventory, PI top-SQL, Global DB + backtrack): [Advanced patterns](references/advanced-patterns.md).

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

Recent AWS features (I/O-Optimized, Limitless, Serverless v2 per-second billing, managed planned failover, PostgreSQL 16 / MySQL 8.4 RI matching, PI anomaly detection, Zero-ETL): [Advanced patterns](references/advanced-patterns.md).

## References (load on demand)

- [Advanced patterns](references/advanced-patterns.md) — quick-start rules, data-quality short-circuits, Step-0 non-obvious behaviours, cost-profile classification, I/O-Optimized break-even math, 60-second triage, recent AWS features
- [Worked examples](references/worked-examples.md) — per-step worked examples (right-sizing, ACU floor, I/O-Optimized migration) and the ALREADY_OPTIMAL baseline
- [Error handling](references/error-handling.md) — FORBIDDEN output-pattern rules and the NEED_MORE_INFO template for missing Cost Explorer access
- [Diagnostic commands](references/diagnostic-commands.md) — required data-source CLI captures, Cost Explorer reconciliation, RI offering lookup
- `references/aurora-pricing-reference.md` — instance-class pricing, storage/backup/Global pricing, ACU tuning math, RI discount matrix, backtrack projections, top-SQL remediation playbook

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
