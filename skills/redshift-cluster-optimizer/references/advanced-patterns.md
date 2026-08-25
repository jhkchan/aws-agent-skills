# Advanced Patterns — Redshift Deep Dives

Deep-dive explanatory content moved verbatim from SKILL.md for
progressive disclosure.

## Philosophy

Four behaviours separate a senior Redshift FinOps engineer from a
generalist:

- **CPUUtilization + QueryQueueLength together determine right-sizing.**
  15% CPU with 0 queue length = overprovisioned. 60% CPU with a 200-query
  queue = under-provisioned or WLM-misconfigured. 15% CPU with a 500-query
  queue = WLM problem, not a capacity problem.
- **RA3 managed storage is cheaper for data that grows.** DC2 local
  storage forces you to buy compute to hold data. RA3 lets you right-size
  compute independently.
- **VACUUM and ANALYZE are cost levers, not just maintenance.** Unvacuumed
  tables hold deleted rows (bloat) that consume storage and slow scans.
  Unanalyzed tables produce bad query plans that burn CPU. Both inflate
  cost indirectly.
- **Data sharing eliminates redundant clusters.** If three clusters each
  query the same production data, data sharing lets one producer cluster
  serve multiple consumer clusters without copying data — cutting compute
  by 60-70%.

## Step 0: Expert knowledge — non-obvious Redshift cost behaviours (key bullets)

- **RA3 managed storage bills on actual usage, not provisioned.** Unlike
  DC2 where you pay for the full local disk, RA3 charges $0.024/GB-month
  for data actually stored in managed storage. Deleting stale data directly
  reduces the bill.
- **DC2 to RA3 migration is not always cheaper.** DC2 includes local
  storage in the node price. If a cluster uses < 60% of DC2 local storage
  AND has low CPU, RA3 is cheaper. If the cluster uses > 80% of DC2 local
  storage, DC2 may be more cost-effective (storage is "free" with compute).
- **Concurrency Scaling charges accrue per active second.** If a cluster
  scales 8 hours/day, that is ~$314/month in scaling charges. Compare with
  Reserved Nodes for the equivalent capacity.
- **Redshift Serverless RPU billing is per-second with 1-minute minimum.**
  Base capacity RPU sets the floor. A Serverless workgroup with base RPU
  8 and max RPU 32 bills at least 8 x $0.36 = $2.88/hour even when idle.
- **Reserved Nodes do NOT apply to Concurrency Scaling charges.** RIs
  discount the provisioned cluster nodes only. Scaling clusters always
  bill at On-Demand rates.
- **VACUUM DELETE reclaims disk space from deleted rows.** Without
  VACUUM, deleted rows are soft-deleted (marked for deletion) and still
  consume storage. On RA3, this directly increases managed-storage cost.
- **ANALYZE updates table statistics for the query planner.** Without
  recent statistics, the planner may choose a broadcast join instead of a
  redistribute join, causing unnecessary network traffic and CPU burn.
- **Data sharing producer clusters bear the compute cost.** Consumer
  clusters query the data without storing or computing it. The producer
  cluster's compute is shared across all consumers.

## Per-step detail notes

### Step 1

**Migration cost:** DC2 to RA3 requires a snapshot/restore or elastic
resize. Brief downtime (minutes for elastic resize, longer for
snapshot/restore depending on data volume).

### Step 2

**Downsize magnitude:** Conservative = 1 node. Aggressive (CPU < 20% +
0 queue) = 2 nodes or smaller node type. Always verify query performance
after downsizing. Redshift requires a minimum of 2 nodes (leader + compute)
for multi-node clusters; single-node clusters have no redundancy.

**Node family selection:** RA3 (ra3.xl4xlarge, ra3.16xlarge) for most
production workloads. DC2 (dc2.large, dc2.8xlarge) for small dense-
storage workloads. Serverless for variable/bursty workloads.

### Step 3

**IMPORTANT:** Reserved Nodes apply to provisioned cluster nodes only.
They do NOT discount Concurrency Scaling charges or Serverless RPU
consumption. Do NOT recommend RIs for Serverless workgroups.

**Commitment laddering:** Purchase 1-yr RIs for baseline -> extend to 3-yr
for stable clusters -> keep On-Demand for variable workloads and
Serverless.

### Step 4

**WLM best practices:**
- Create at least 2 queues: one for short interactive BI queries (high
  priority, low concurrency) and one for long ETL queries (lower priority,
  higher concurrency).
- Enable SQA to auto-route queries estimated < 15 seconds to a dedicated
  short-query path, bypassing the main queue.
- Set Concurrency Scaling to AUTO for queues with unpredictable spikes.
  Scaling clusters are added automatically when the queue is full.

### Step 5

**Compression types:** AZ64 (default, best for numeric/date), Zstandard
(best compression ratio, general purpose), LZO (legacy, fast). Always
test compression on a sample before applying cluster-wide — some query
patterns perform worse with high compression.

**VACUUM strategy:** VACUUM DELETE reclaims space from soft-deleted rows.
VACUUM SORT re-sorts data. Run during low-traffic windows — VACUUM is
resource-intensive and can impact query performance.

### Step 6

**Cost comparison:** Concurrency Scaling at ~$1.08/hour. If the cluster
scales 8h/day x 30 days = $2,592/month. Compare with adding a Reserved
Node: ra3.4xlarge at 3-yr RI ~$1,113/month (40% of $2,475). Reserved Nodes
are cheaper for sustained load; Concurrency Scaling is cheaper for short
bursts.

### Step 7

**Serverless cost model:** `hourly_cost = actual_RPU x $0.36`; monthly
floor = `base_RPU x $0.36 x 730`. Example: base RPU 8 = $2,102/month
floor. Lowering base RPU from 32 to 8 drops floor from $8,410 to $2,102.

**Serverless vs provisioned decision rule:** If the workload runs < 12
hours/day at moderate RPU, Serverless is typically cheaper. If the
workload runs 24/7 at steady RPU, provisioned with RIs is cheaper.

### Step 8

**Materialized view strategy:** Create materialized views for frequently
queried aggregations (daily sales, active users). Auto-refresh on a
schedule. This reduces CPU on the main cluster by pre-computing results.
The trade-off: refresh compute cost. Use incremental refresh (late
materialized views) for large datasets.

**Data sharing strategy:** If multiple clusters query the same production
data, configure one producer cluster with data sharing. Consumer clusters
query the data directly without copying. This eliminates redundant storage
and ETL pipelines.
## Output format (per cluster)

```text
TARGET: <cluster-identifier or workgroup-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <node-type> x <node-count> at <pricing-model> in <region>
    Distribution: <EVEN | KEY(<col>) | ALL>  Sort key: <none | <col> | compound(<cols>)>
  Proposed: <node-type> x <node-count> at <pricing-model> in <region>
    Distribution: <EVEN | KEY(<col>) | ALL>  Sort key: <none | <col> | compound(<cols>)>
  Dimensions: <list of applicable dimensions>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (node-type): $<amount>
  Monthly (right-size): $<amount>
  Monthly (pricing model): $<amount>
  Monthly (other): $<amount>
  Annual total: $<amount>
  Assumptions: <list (730h/month, us-east-1 pricing, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <cluster> in <region>. Proceed?
  (yes/no)"
```

## Expert heuristic — non-obvious Redshift behaviours

| Heuristic | Impact on optimisation |
|---|---|
| RA3 managed storage bills on actual usage, not provisioned | Deleting stale data and VACUUM directly reduces monthly cost |
| DC2 local storage is bundled with compute | DC2 with > 80% storage usage may be cheaper than RA3 + managed storage |
| Concurrency Scaling charges per active second | Sustained CS (8h+/day) costs more than a Reserved Node |
| Reserved Nodes do NOT discount Concurrency Scaling | CS always bills at On-Demand; budget CS separately |
| Serverless base RPU sets the floor cost | Min RPU 8 = $2,102/month floor even when idle |
| VACUUM reclaims soft-deleted rows | Without VACUUM, deleted rows still consume storage and slow scans |
| ANALYZE updates planner statistics | Stale stats cause bad joins — broadcast instead of redistribute burns CPU |
| Data sharing producer bears compute | One producer can serve many consumers, eliminating redundant clusters |
| SQA bypasses the main WLM queue | Enable SQA for sub-15s queries to prevent short queries being stuck behind long ETL |
| Materialized views reduce main-cluster CPU | Pre-computed aggregations trade refresh cost for query savings |
| Redshift ML AUTO ON delegates to SageMaker | Training costs accrue in SageMaker; inference is free in Redshift |
| Spectrum scans S3 at $5/TB | Cheaper than storing cold data in Redshift managed storage |
| Elastic resize has brief downtime (~10-20 min) | Plan during maintenance window; snapshot before resize |

## Recent AWS features (2024-2026)

- **Redshift RA3 node types expanded (2024-2025):** ra3.4xlarge and
  ra3.16xlarge remain the standard. Managed storage now supports up to
  10 PB per cluster. Evaluate DC2 clusters for RA3 migration.
- **Redshift Serverless general availability + enhancements (2024-2025):**
  Base capacity RPU 8-512, auto-scaling, cross-account data sharing.
  Evaluate for variable workloads with significant idle periods.
- **Concurrency Scaling improvements (2024):** Faster scaling cluster
  spin-up (30 seconds vs 2 minutes previously). More cost-effective for
  short bursts.
- **Redshift ML AUTO ON (2024-2025):** Automatically trains and deploys
  SageMaker Autopilot models from Redshift SQL. Inference runs in
  Redshift without separate SageMaker endpoint costs.
- **Materialized views with incremental refresh (2024-2025):** Late
  materialized views support incremental refresh, reducing the compute
  cost of keeping views current.
- **Data sharing general availability (2024):** Cross-account and cross-
  region data sharing. One producer cluster serves multiple consumers
  without data duplication.
- **AZ64 compression (2024):** Default encoding for new tables. 30-40%
  better compression than LZO for numeric and date columns with faster
  decompression.
- **Data lake export (UNLOAD to S3, 2024-2025):** Native export of query
  results to S3 in Parquet format for cold data archival and Spectrum
  querying.
