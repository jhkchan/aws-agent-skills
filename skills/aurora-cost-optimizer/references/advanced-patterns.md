# Advanced Patterns — Aurora Cost Optimizer

Load-on-demand deep dives moved verbatim from SKILL.md: quick-start rules, data-quality short-circuits, Step-0 expert knowledge, cost classification, break-even math, 60-second triage, recent features.

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

## Data-quality short-circuits

| Condition | Effect on optimisation |
|---|---|
| Cost Explorer access denied | NEED_MORE_INFO for cost quantification; topology still analysable. |
| Observation window < 14 days | NEED_MORE_INFO: workload may reflect atypical load. Min 14 days; 30 preferred. |
| Performance Insights not enabled | NEED_MORE_INFO for DBLoad / top-SQL; right-sizing still works from CPU. |
| Aurora cluster in `creating` / `modifying` / `failing-over` | Wait for `available` before emitting a change recommendation. |
| Serverless v2 with auto-pause enabled | Min ACU floor is 0 when paused; don't flag the floor as waste. |
| I/O-Optimized already enabled | Skip the I/O tier dimension — already optimal. |
| Cluster part of Aurora Limitless Database | Route to Step 10 (Limitless) — standard right-sizing does not apply. |

## Step 0: Non-obvious behaviours that change the recommendation

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

## Step 3: Cost classification

| Cost profile | Indicators | Emphasis |
|---|---|---|
| I/O-heavy | Aurora:IOUsage > 30% of total | I/O-Optimized tier (Step 6) |
| Serverless waste | ServerlessUsage high, CPU < 10% | ACU min tuning (Step 5) |
| Compute-heavy, low CPU | InstanceUsage high, avg CPU < 20% | Right-sizing (Step 4) |
| Compute-heavy, On-Demand | No RI, uptime > 6 months | Reserved Instance (Step 11) |
| Storage / backtrack creep | StorageUsage/BackupUsage growing | Storage cleanup (Step 7) |
| Global DB DR | ReplicaUsage in DR region, CPU < 5% | Replica right-sizing (Step 8) |
| Mixed (no single dimension > 30%) | Even distribution | Apply all dimensions in parallel |

## Step 6: Aurora I/O-Optimized tier — break-even calculation

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
