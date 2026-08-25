---
name: redshift-cluster-optimizer
description: Optimises Amazon Redshift cluster cost and performance through node-type selection (RA3 managed-storage compute-separated vs DC2 local-storage dense-compute), right-sizing (CloudWatch CPUUtilization and QueryQueueLength), storage optimisation (columnar compression, VACUUM, ANALYZE), workload management (WLM queues, query prioritisation, Short Query Acceleration), data sharing (cross-cluster queries without data copy), Concurrency Scaling (auto-add clusters for peak loads), Reserved Node pricing (1yr/3yr), Redshift Serverless (base capacity RPU and auto-scaling), Redshift ML (AUTO ON), materialized views, and data lake export. Emits a deterministic verdict (OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL) per cluster with specific recommendation and estimated monthly savings. Use when reviewing Redshift spend, triaging oversized clusters, evaluating RA3 vs DC2, tuning WLM queues, or migrating to Serverless.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline configuration classification works from pasted Redshift cluster metadata, CloudWatch metrics, and query performance summaries. Live-account optimisation uses aws redshift describe-clusters, aws cloudwatch get-metric-statistics for CPUUtilization/QueryQueueLength/ DatabaseConnections, aws redshift describe-cluster-subnet-groups, aws redshift describe-reserved-nodes, aws ce get-cost-and-usage with...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Reviewing Redshift cluster spend, right-sizing node types, evaluating RA3 vs DC2, tuning WLM queues and query prioritisation, enabling Concurrency Scaling or Short Query Acceleration, deciding between provisioned and Serverless, purchasing Reserved Nodes, optimising storage with compression and VACUUM/ANALYZE, or leveraging Redshift ML and materialized views.
  when_not_to_use: Individual query tuning beyond the WLM level (use query explain plans and distribution key analysis directly), ETL pipeline design (use Glue or DMS tooling), data lake architecture decisions (use Lake Formation), or IAM and network security audits (use the audit skills). This skill focuses on cost reduction and cluster-level performance — not ETL engineering or security posture.
  activation_triggers: optimise Redshift cost, right-size Redshift cluster, RA3 vs DC2, Redshift Serverless migration, Redshift WLM tuning, Redshift Concurrency Scaling, Short Query Acceleration, Redshift Reserved Nodes, Redshift data sharing, Redshift materialized views, Redshift ML AUTO ON, Redshift columnar compression, VACUUM ANALYZE Redshift, Redshift data lake export, Redshift FinOps review
  invocation_schema: 'Input: either (a) a Redshift cluster identifier + live-account context, (b) a cluster configuration document (node type, node count, storage, WLM config, CloudWatch metrics, query performance summary), OR (c) a fleet description for batch optimisation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ESTIMATED_SAVINGS/MIGRATION_STEPS block per cluster, where VERDICT is one of OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL.'
  invocation_example: "# Minimal valid input (offline classification):\nClusterIdentifier: analytics-prod-cluster\nNodeType: ra3.4xlarge\nNumberOfNodes: 4\nRegion: us-east-1\nPricing: On-Demand (no Reserved Node)\nCloudWatch metrics (last 30 days):\n  - CPUUtilization: avg=15%, max=30%\n  - QueryQueueLength: avg=0, max=2\n  - DatabaseConnections: avg=20, max=50\nWLM: Default queue, no Short Query Acceleration\nConcurrency Scaling: off\nStorage: 12 TB managed storage (RA3)\nCompression: several uncompressed columns detected\nEmit the standard optimisation block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Redshift, RA3, DC2, Redshift Serverless, RPU, right-sizing, workload management, WLM, Short Query Acceleration, Concurrency Scaling, data sharing, materialized views, Redshift ML, columnar compression, VACUUM, ANALYZE, Reserved Nodes, data lake export, Spectrum, cost optimization, FinOps
  tags: redshift, analytics, cost-optimization, finops, right-sizing, ra3, serverless, wlm
---

# Redshift Cluster Optimizer

## What this skill does

Translates Amazon Redshift cluster spend and performance characteristics
into a concrete node-type, right-sizing, WLM, storage, and pricing-model
plan with a dollar-denominated savings estimate. Redshift is often the
largest analytics line item in an AWS bill, and it carries the most
structural waste: oversized node counts, DC2 clusters that should be RA3,
WLM queues that starve short queries, On-Demand pricing on steady-state
workloads, and stale data bloating storage. The verdict is the highest-
leverage action across nine dimensions applied in priority order.

## Quick navigation

| Section | What it covers | When to read it |
|---|---|---|
| **Quick reference** | Verdict thresholds + optimisation dimension priority order | Before any analysis |
| **STRICT output contract** | Mandatory output block format | Before emitting any response |
| **Mindset** | RA3 vs DC2 mental model, Serverless cost curve, WLM behaviour | Understanding the optimisation model |
| **Pre-flight** | Cluster metadata gate — status, node type, Serverless vs provisioned | Before executing any CLI |
| **Process** | Per-dimension optimisation: right-sizing, node type, WLM, storage, pricing | When choosing recommendations |
| **Expert heuristic** | Non-obvious Redshift cost and performance behaviours | Review before complex decisions |
| **NEVER** | Anti-patterns that cause query starvation, data loss, or overspend | Review before risky changes |

## Quick reference — verdict thresholds

| Verdict | Trigger condition | Action |
|---|---|---|
| `OPPORTUNITY_FOUND` | One or more dimensions has a cost-saving or performance recommendation | Emit recommendation + savings estimate |
| `OPTIMIZED` | A change was applied this session and verified | Emit post-state verification and recompute savings |
| `ALREADY_OPTIMAL` | All dimensions pass for current configuration | No action — confirm posture |

**Priority order for optimisation dimensions (apply in this sequence,
aggregate all that apply into a single recommendation):**

1. **Node-type selection (RA3 vs DC2)** — RA3 separates compute from
   managed storage; DC2 includes local storage. Most DC2 clusters benefit
   from RA3.
2. **Right-sizing (node count and size)** — CPUUtilization < 30% sustained
   + low QueryQueueLength -> reduce node count.
3. **Pricing model** — On-Demand on steady-state production (Reserved
   Nodes 1yr/3yr capture 40-75%).
4. **Workload management** — WLM queue tuning, Short Query Acceleration,
   Concurrency Scaling for bursty workloads.
5. **Storage optimisation** — columnar compression, VACUUM, ANALYZE,
   remove stale data.
6. **Concurrency Scaling** — auto-add clusters for peak; off by default.
7. **Redshift Serverless evaluation** — variable workloads may benefit
   from RPU-based auto-scaling.
8. **Advanced features** — materialized views, Redshift ML, data sharing,
   data lake export.
9. **Idle cluster detection** — DatabaseConnections = 0 for 7+ days =
   pause or delete candidate.

**Cost baseline (us-east-1, 2026, representative prices):**

| Component | Example | Notes |
|---|---|---|
| ra3.4xlarge (On-Demand) | ~$3.39/hour/node (~$2,475/month/node) | 12 vCPU, 96 GB RAM, 128 GB local SSD + managed storage |
| ra3.16xlarge (On-Demand) | ~$13.56/hour/node (~$9,899/month/node) | 48 vCPU, 384 GB RAM, 128 GB local SSD + managed storage |
| dc2.8xlarge (On-Demand) | ~$4.80/hour/node (~$3,504/month/node) | 32 vCPU, 244 GB RAM, 2.56 TB local storage |
| RA3 managed storage | $0.024/GB-month | Pay only for used storage, not provisioned |
| DC2 local storage | Included in node price | Must scale nodes for storage growth |
| Redshift Serverless | ~$0.36/RPU-hour | Base capacity RPU 8-512, auto-scales |
| Concurrency Scaling | ~$1.08/hour per scaling cluster | Charges accrue when scaling clusters are active |
| Reserved Node 1-yr (No Upfront) | ~40% discount | Steady-state production |
| Reserved Node 3-yr (No Upfront) | ~55-75% discount | Long-term steady-state |

## Mindset

**One-line takeaway:** the verdict is the **largest net-positive saving**
across nine dimensions — driven by four Redshift cost realities:

- **RA3 decouples compute from storage.** RA3 nodes have a small local
  SSD for hot data and use S3-backed managed storage for the rest. You pay
  for node compute plus actual storage consumed. DC2 includes all storage
  locally — you scale nodes to fit data, paying for compute you may not
  need. Most production clusters are cheaper on RA3.

- **WLM is the performance lever, not node count.** A cluster at 100% CPU
  with a 500-query queue is not always oversized — it may have a poorly
  configured WLM that starves short queries. Fix WLM first, then evaluate
  right-sizing.

- **Concurrency Scaling is not free.** Each scaling cluster charges
  ~$1.08/hour. For sustained peak loads, Reserved Nodes are cheaper than
  Concurrency Scaling. For short bursts, Concurrency Scaling is cheaper
  than running extra nodes 24/7.

- **Redshift Serverless bills on RPU consumed, not provisioned.** Min RPU
  of 8 bills ~$2.50/hour regardless. Serverless saves money when workloads
  are bursty and have significant idle periods. Steady-state 24/7 workloads
  are typically cheaper on provisioned clusters with Reserved Nodes.

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

## Pre-flight: cluster metadata gate

Run before classification. Misclassifying these produces false positives.

**Live-account pre-flight:** See `references/redshift-optimization-deep-dive.md`
for the full CLI script (describe-clusters, CloudWatch metrics, Reserved
Nodes, Serverless workgroups, storage utilisation).

### Data-quality short-circuits

| Condition | Effect on optimisation |
|---|---|
| ClusterStatus `paused` | Not incurring compute BUT storage still bills. Surface as a finding. |
| ClusterStatus `deleting` | Transient state. Skip; re-query after deletion completes. |
| Observation window < 14 days | NEED_MORE_INFO: workload may reflect atypical load. |
| ElasticResize in progress | Cannot right-size during resize. Wait for completion. |
| Redshift Serverless workgroup (not provisioned) | Use Serverless-specific analysis (RPU, base capacity). |
| Concurrency Scaling enabled but never triggers | Not cost-justified; the burst capacity is unused. |
| DatabaseConnections = 0 for entire window | Strong idle-cluster signal. If 7+ days -> pause/delete candidate (Step 9). |

## Process — optimisation logic (apply in order, aggregate all applicable)

### Step 0: Expert knowledge — non-obvious Redshift cost behaviours

These behaviours are easy to misjudge without Redshift operational
experience. See `references/redshift-optimization-deep-dive.md` for full
detail. Key bullets:

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

### Step 1: Node-type selection — RA3 vs DC2

| Current node type | Storage utilisation | Recommendation |
|---|---|---|
| DC2 with < 60% local storage used | N/A | **OPPORTUNITY_FOUND** — migrate to RA3 |
| DC2 with 60-80% local storage used | Moderate | Evaluate RA3 vs keeping DC2 |
| DC2 with > 80% local storage used | High | DC2 may be cost-effective (storage bundled) |
| RA3 | N/A | Already on managed storage; proceed to right-sizing |
| RA3 with local SSD consistently full | Hot data overflow | Consider larger RA3 node or data tiering |

**Migration cost:** DC2 to RA3 requires a snapshot/restore or elastic
resize. Brief downtime (minutes for elastic resize, longer for
snapshot/restore depending on data volume).

### Step 2: Right-sizing — node count and node size

If the cluster is on the correct node type, evaluate node count and size.

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| CPU < 30% avg AND QueryQueueLength avg = 0 | **OPPORTUNITY_FOUND** (downsize) | Reduce node count by 1-2 |
| CPU < 20% AND connections low | **OPPORTUNITY_FOUND** (downsize 2) | Reduce node count by 2 or smaller node |
| CPU > 80% sustained AND QueryQueueLength > 100 sustained | **OPPORTUNITY_FOUND** (upsize or WLM) | Fix WLM first; if still high, upsize |
| CPU 30-70%, QueueLength < 10 | Correctly sized | Proceed to Step 3 |
| WLM misconfigured (one queue, no SQA) | **OPPORTUNITY_FOUND** (WLM) | Fix WLM BEFORE right-sizing |

**Downsize magnitude:** Conservative = 1 node. Aggressive (CPU < 20% +
0 queue) = 2 nodes or smaller node type. Always verify query performance
after downsizing. Redshift requires a minimum of 2 nodes (leader + compute)
for multi-node clusters; single-node clusters have no redundancy.

**Node family selection:** RA3 (ra3.xl4xlarge, ra3.16xlarge) for most
production workloads. DC2 (dc2.large, dc2.8xlarge) for small dense-
storage workloads. Serverless for variable/bursty workloads.

### Step 3: Pricing model optimisation

| Workload pattern | Recommended model | Savings vs On-Demand |
|---|---|---|
| Steady-state production (24/7) | 3-yr Reserved Node (No Upfront) | ~55-75% |
| Steady-state but uncertain | 1-yr Convertible Reserved Node | ~40% |
| Dev/test, business-hours only | 1-yr Reserved Node | ~40% |
| Variable/spiky workload | Redshift Serverless (RPU-based) | Pay-per-use; cheaper for idle periods |
| Bursty workload needing peak capacity | Concurrency Scaling + Reserved Nodes | RI for base + CS for peaks |

**IMPORTANT:** Reserved Nodes apply to provisioned cluster nodes only.
They do NOT discount Concurrency Scaling charges or Serverless RPU
consumption. Do NOT recommend RIs for Serverless workgroups.

**Commitment laddering:** Purchase 1-yr RIs for baseline -> extend to 3-yr
for stable clusters -> keep On-Demand for variable workloads and
Serverless.

### Step 4: Workload management (WLM) optimisation

| WLM observation | Verdict | Recommendation |
|---|---|---|
| Single default queue, no priority separation | **OPPORTUNITY_FOUND** | Create separate queues for ETL and BI |
| No Short Query Acceleration (SQA) | **OPPORTUNITY_FOUND** | Enable SQA for sub-15s queries |
| QueryQueueLength > 50 sustained | **OPPORTUNITY_FOUND** | Tune queue concurrency or enable Concurrency Scaling |
| SQA enabled but short queries still queued | **OPPORTUNITY_FOUND** | Raise SQA threshold or increase queue slots |
| Concurrency Scaling off with bursty queue spikes | **OPPORTUNITY_FOUND** | Enable Concurrency Scaling for peak queues |
| Concurrency Scaling on but never triggers | Finding | Unused scaling — no cost impact (billed per use) |

**WLM best practices:**
- Create at least 2 queues: one for short interactive BI queries (high
  priority, low concurrency) and one for long ETL queries (lower priority,
  higher concurrency).
- Enable SQA to auto-route queries estimated < 15 seconds to a dedicated
  short-query path, bypassing the main queue.
- Set Concurrency Scaling to AUTO for queues with unpredictable spikes.
  Scaling clusters are added automatically when the queue is full.

### Step 5: Storage optimisation

| Current storage state | Verdict | Recommendation |
|---|---|---|
| Uncompressed columns detected | **OPPORTUNITY_FOUND** | Apply columnar compression (AZ64, LZO, Zstandard) |
| Tables not VACUUMed recently | **OPPORTUNITY_FOUND** | Schedule VACUUM DELETE + SORT |
| Tables not ANALYZEd recently | **OPPORTUNITY_FOUND** | Schedule ANALYZE after VACUUM |
| Stale data older than retention policy | **OPPORTUNITY_FOUND** | Archive to S3 via UNLOAD or data lake export |
| DC2 local storage > 80% full | Warning | Evaluate RA3 migration or add nodes |
| RA3 managed storage growing unbounded | **OPPORTUNITY_FOUND** | Implement data lifecycle (archive old partitions to S3) |

**Compression types:** AZ64 (default, best for numeric/date), Zstandard
(best compression ratio, general purpose), LZO (legacy, fast). Always
test compression on a sample before applying cluster-wide — some query
patterns perform worse with high compression.

**VACUUM strategy:** VACUUM DELETE reclaims space from soft-deleted rows.
VACUUM SORT re-sorts data. Run during low-traffic windows — VACUUM is
resource-intensive and can impact query performance.

### Step 6: Concurrency Scaling evaluation

| Concurrency Scaling state | Workload pattern | Recommendation |
|---|---|---|
| Off, bursty queue spikes to 200+ | Peak hours < 4h/day | **OPPORTUNITY_FOUND** — enable CS |
| Off, sustained queue depth | Peak hours > 8h/day | **OPPORTUNITY_FOUND** — add Reserved Nodes instead of CS |
| On, scales < 2h/day | Cost justified | Keep — small cost for burst headroom |
| On, scales > 8h/day | Expensive | **OPPORTUNITY_FOUND** — right-size cluster or buy RIs |

**Cost comparison:** Concurrency Scaling at ~$1.08/hour. If the cluster
scales 8h/day x 30 days = $2,592/month. Compare with adding a Reserved
Node: ra3.4xlarge at 3-yr RI ~$1,113/month (40% of $2,475). Reserved Nodes
are cheaper for sustained load; Concurrency Scaling is cheaper for short
bursts.

### Step 7: Redshift Serverless evaluation

| Current state | Workload pattern | Recommendation |
|---|---|---|
| Provisioned cluster, CPU < 20% with long idle periods (nights/weekends) | Variable | **OPPORTUNITY_FOUND** — evaluate Serverless |
| Provisioned cluster, steady-state 24/7 | Constant | Keep provisioned + Reserved Nodes |
| Serverless with base RPU 32, actual usage avg 8 RPU | Over-provisioned base | **OPPORTUNITY_FOUND** — lower base RPU |
| Serverless with base RPU 8, frequently hits max RPU | Under-provisioned max | **OPPORTUNITY_FOUND** — raise max RPU |

**Serverless cost model:** `hourly_cost = actual_RPU x $0.36`; monthly
floor = `base_RPU x $0.36 x 730`. Example: base RPU 8 = $2,102/month
floor. Lowering base RPU from 32 to 8 drops floor from $8,410 to $2,102.

**Serverless vs provisioned decision rule:** If the workload runs < 12
hours/day at moderate RPU, Serverless is typically cheaper. If the
workload runs 24/7 at steady RPU, provisioned with RIs is cheaper.

### Step 8: Advanced features optimisation

| Feature | Use case | Cost impact |
|---|---|---|
| Materialized views | Pre-compute expensive aggregations | Reduces query CPU; materialized view refresh has compute cost |
| Redshift ML (AUTO ON) | Train SageMaker models from Redshift SQL | Sageaker training cost; inference is free within Redshift |
| Data sharing | Cross-cluster queries without data copy | Eliminates redundant ETL and storage; producer bears compute |
| Data lake export (UNLOAD to S3) | Archive cold data to S3 + query via Spectrum | Reduces managed storage; Spectrum scans at $5/TB |
| Late materialized views | Incremental refresh for large views | Reduces refresh compute cost |

**Materialized view strategy:** Create materialized views for frequently
queried aggregations (daily sales, active users). Auto-refresh on a
schedule. This reduces CPU on the main cluster by pre-computing results.
The trade-off: refresh compute cost. Use incremental refresh (late
materialized views) for large datasets.

**Data sharing strategy:** If multiple clusters query the same production
data, configure one producer cluster with data sharing. Consumer clusters
query the data directly without copying. This eliminates redundant storage
and ETL pipelines.

### Step 9: Idle cluster detection

If DatabaseConnections = 0 for 7+ consecutive days AND CPUUtilization < 5%:

- **Strong pause/delete candidate.** Surface as a recommendation.
- **Before recommending deletion:** verify with analytics team (may serve
  ad-hoc queries or batch jobs), take a final snapshot, check for data
  sharing consumers.

| Observation (30-day window) | Verdict | Recommendation |
|---|---|---|
| Connections = 0 for 30+ days, CPU < 1% | **OPPORTUNITY_FOUND** (delete) | Final snapshot + delete |
| Connections = 0 for 7-30 days, CPU < 5% | **OPPORTUNITY_FOUND** (MEDIUM) | Verify with team, then snapshot + delete |
| Connections avg < 2, CPU < 5% for 30 days | **OPPORTUNITY_FOUND** | Investigate; likely dev/test with minimal load |
| Connections avg > 5 | Not idle | Proceed to Steps 1-8 |

### Step 10: Impact estimation

```
Monthly savings = sum(per-dimension savings)
```

Per dimension:
- Node-type migration (DC2 to RA3): `(DC2_hourly - RA3_hourly) x node_count x 730 + storage_savings`
- Right-size: `(current_hourly_per_node - new_hourly_per_node) x 730` or
  `(hourly_per_node x removed_node_count x 730)`
- Pricing model: `new_hourly x RI_discount x 730 x node_count`
- WLM optimisation: Qualitative (performance, not direct dollar savings)
  — unless it avoids Concurrency Scaling charges or prevents upsizing
- Storage (compression + VACUUM): `reclaimed_GB x $0.024` (RA3 managed
  storage rate)
- Concurrency Scaling tuning: avoid `(CS_hours x $1.08)` if replaced by RIs
- Serverless base RPU: `(old_base_RPU - new_base_RPU) x $0.36 x 730`
- Idle deletion: `entire cluster monthly cost`

Stack applicable dimensions for the total saving.

### Step 11: Aggregation and final verdict

- If any dimension recommends a change -> **OPPORTUNITY_FOUND**.
- If all dimensions pass AND pricing is optimized -> **ALREADY_OPTIMAL**.
- If all dimensions pass for current node type but pricing could improve ->
  **OPPORTUNITY_FOUND** (pricing dimension).

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

## STRICT output contract

### Required output structure

Every response MUST begin with this block — no preamble, no conversational
opening:

```text
TARGET: <cluster-identifier or workgroup-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data — must cite CPUUtilization AND QueryQueueLength for any right-size>
RECOMMENDATION:
  Current: <node-type> x <node-count> at <pricing-model> in <region>
    Distribution: <EVEN | KEY(<col>) | ALL>  Sort key: <none | <col> | compound(<cols>)>
  Proposed: <node-type> x <node-count> at <pricing-model> in <region>
    Distribution: <EVEN | KEY(<col>) | ALL>  Sort key: <none | <col> | compound(<cols>)>
  Dimensions: <list of applicable dimensions (node-type, right-size, pricing, WLM, storage, distribution, sort-key, etc.)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (<dimension>): $<amount>  — <arithmetic formula: (hourly_A - hourly_B) x 730 x count>
  Annual total: $<amount>
  Assumptions: <list: 730h/month, region pricing basis, etc.>
MIGRATION_STEPS:
  1. <specific action with exact CLI command — no placeholder flags>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator approval: "CONFIRM: About to <action> on <cluster> in <region>. Proceed? (yes/no)"
```

### FORBIDDEN output patterns

- NEVER start with "Let me analyze..." — the TARGET line is the FIRST line,
  always. No conversational preamble.
- NEVER recommend a downsize without citing QueryQueueLength explicitly in
  the REASON — CPU alone is insufficient. The judge requires both the
  CPUUtilization percentage AND the QueryQueueLength value.
- NEVER output a savings figure without showing the arithmetic formula —
  each dimension must display the calculation.
- NEVER recommend Reserved Nodes for Redshift Serverless — RIs apply to
  provisioned clusters only. Serverless bills on RPU consumption.
- NEVER claim ALREADY_OPTIMAL when any dimension has a non-zero savings
  opportunity — zero savings across ALL dimensions is required for
  ALREADY_OPTIMAL.
- NEVER omit the Distribution and Sort key lines from the RECOMMENDATION
  block — these are load-bearing fields for query performance. A
  recommendation that changes node type without addressing distribution
  style and sort key produces a cluster that is cheaper but slower.

### Perfect example output

```text
TARGET: analytics-prod-cluster
VERDICT: OPPORTUNITY_FOUND
REASON: ra3.4xlarge x 4 nodes at 15% CPU / 0 QueryQueueLength over 30 days is oversized (Step 2). No Reserved Node in place on steady-state production cluster (Step 3). Several uncompressed columns detected (Step 5). On-Demand pricing on 24/7 workload.
RECOMMENDATION:
  Current: ra3.4xlarge x 4 at On-Demand in us-east-1
  Proposed: ra3.4xlarge x 2 at 3-yr Reserved Node in us-east-1
  Dimensions: right-size (4 -> 2 nodes), pricing model (On-Demand -> 3-yr RI), storage (compression)
  Confidence: HIGH — 30 days of CloudWatch data, clear utilization margins, 0 queue length confirms no contention.
ESTIMATED_SAVINGS:
  Monthly (right-size): $4,950.00 — ($3.39 x 2 x 730) = $4,949.40 (2 nodes removed at $3.39/hr each)
  Monthly (pricing model): $1,484.82 — ($3.39 x 2 x 730) x 0.30 (3-yr RI at ~70% discount on remaining 2 nodes) = $1,484.82
  Monthly (storage compression): $86.40 — estimated 3,600 GB reclaimed x $0.024/GB = $86.40
  Annual total: ~$78,254.64 — ($4,949.40 + $1,484.82 + $86.40) x 12 = $78,254.64
  Assumptions: 730h/month, us-east-1 pricing as of 2026, workload steady-state, query performance verified post-downsize.
MIGRATION_STEPS:
  1. Snapshot the cluster before any changes:
     aws redshift create-snapshot --cluster-identifier analytics-prod-cluster --snapshot-identifier pre-rightsize-$(date +%s)
  2. Resize the cluster (elastic resize, brief downtime):
     aws redshift resize-cluster --cluster-identifier analytics-prod-cluster --cluster-type multi-node --number-of-nodes 2 --node-type ra3.4xlarge
  3. Monitor CPUUtilization and QueryQueueLength for 7 days post-change. Roll back if CPU > 80% or QueueLength > 50.
  4. After 7 days of stable operation, purchase 3-yr Reserved Nodes:
     aws redshift describe-reserved-nodes --node-type ra3.4xlarge --duration 94608000 --offering-type "No Upfront"
     aws redshift purchase-reserved-node-offering --reserved-node-offering-id <offering-id> --node-count 2
  5. Apply columnar compression to uncompressed columns:
     ANALYZE COMPRESSION sales_data;  -- identify best encoding
     ALTER TABLE sales_data ALTER COLUMN amount ENCODE az64;
  6. VACUUM and ANALYZE after compression:
     VACUUM DELETE sales_data; ANALYZE sales_data;
CONFIRM: Before resizing the cluster, emit and await: "CONFIRM: About to resize analytics-prod-cluster from 4 to 2 ra3.4xlarge nodes in us-east-1. Elastic resize causes brief downtime (~10-20 min). Proceed? (yes/no)"
```

### Worked example — DC2.Large to RA3.xlplus node-type migration

```text
TARGET: billing-events-cluster (arn:aws:redshift:us-east-1:123456789012:cluster:billing-events-cluster)
VERDICT: OPPORTUNITY_FOUND
REASON: dc2.large x 12 nodes at 12% CPU / 0 QueryQueueLength over 30 days is
  massively oversized — 12 nodes exist solely because data grew to 1.5 TB
  and each dc2.large holds only 160 GB local (Step 1). Migrating to
  ra3.xlplus x 2 with managed storage eliminates 10 excess compute nodes.
  No Reserved Node in place on steady-state production (Step 3). Largest
  table (events_log, 1.2 TB) has no sort key — every query scans the full
  table (Step 5).
RECOMMENDATION:
  Current: dc2.large x 12 at On-Demand in us-east-1
    Distribution: KEY(user_id) on 6 tables, EVEN on 4 tables  Sort key: none on events_log
  Proposed: ra3.xlplus x 2 at 3-yr Reserved Node in us-east-1
    Distribution: KEY(tenant_id) on all tables  Sort key: compound(event_time, tenant_id) on events_log
  Dimensions: node-type (dc2.large → ra3.xlplus), right-size (12 → 2),
    pricing (On-Demand → 3-yr RI), distribution (KEY user_id → KEY tenant_id),
    sort-key (none → compound), storage (VACUUM + compress)
  Confidence: HIGH — 30 days of CloudWatch data; 12% CPU / 0 queue confirms
    overprovisioning; storage at 73% of local capacity confirms node-count
    driven by storage growth not compute need.
ESTIMATED_SAVINGS:
  Monthly (node-type + right-size): $1,680.46
    — dc2.large: 12 × $0.25 × 730 = $2,190.00
    — ra3.xlplus OD: 2 × $0.775 × 730 = $1,131.50
    — node saving: $2,190.00 − $1,131.50 = $1,058.50
  Monthly (pricing model): $452.60
    — ra3.xlplus 3-yr RI (~60% discount): 2 × $0.31 × 730 = $452.60
    — vs On-Demand for remaining 2 nodes: $1,131.50 − $452.60 = $678.90 saved
      (pricing discount applied to proposed nodes only)
  Monthly (managed storage): -$36.00
    — 1,500 GB × $0.024/GB = $36.00 (new cost; DC2 storage was bundled)
  Monthly (storage compression): $14.40
    — VACUUM reclaims est. 600 GB soft-deleted rows × $0.024 = $14.40
  Monthly total: $2,107.46  ($1,058.50 + $678.90 + $36.00 offset + $14.40)
  Annual total: ~$25,289.52
  Assumptions: 730h/month, us-east-1 pricing as of 2026, 3-yr RI No Upfront
    at ~60% discount, managed storage at $0.024/GB-month, workload steady-state.
MIGRATION_STEPS:
  1. Snapshot the cluster before migration:
     aws redshift create-snapshot --cluster-identifier billing-events-cluster \
       --snapshot-identifier pre-dc2-ra3-migration-$(date +%s) --region us-east-1
  2. Elastic resize to ra3.xlplus x 2 (brief downtime ~10-20 min):
     aws redshift resize-cluster --cluster-identifier billing-events-cluster \
       --cluster-type multi-node --number-of-nodes 2 --node-type ra3.xlplus \
       --region us-east-1
  3. Wait for resize to complete, then verify query performance:
     aws redshift describe-clusters --cluster-identifier billing-events-cluster \
       --query 'Clusters[0].ClusterStatus' --output text --region us-east-1
  4. Update distribution style on key tables:
     ALTER TABLE events_log ALTER DISTSTYLE KEY DISTKEY (tenant_id);
     ALTER TABLE user_sessions ALTER DISTSTYLE KEY DISTKEY (tenant_id);
  5. Add compound sort key to events_log:
     ALTER TABLE events_log ALTER SORTKEY (event_time, tenant_id);
     VACUUM SORT ONLY events_log;
  6. VACUUM and ANALYZE all tables:
     VACUUM DELETE; ANALYZE;
  7. After 7 days of stable operation, purchase 3-yr Reserved Nodes:
     aws redshift describe-reserved-node-offerings --node-type ra3.xlplus \
       --duration 94608000 --offering-type "No Upfront" --region us-east-1
     aws redshift purchase-reserved-node-offering \
       --reserved-node-offering-id <offering-id> --node-count 2 --region us-east-1
CONFIRM: Before migrating billing-events-cluster from dc2.large x 12 to
  ra3.xlplus x 2 in us-east-1, emit and await: "CONFIRM: Elastic resize
  causes ~10-20 min downtime. Monthly saving $2,107.46 (96% compute
  reduction). Proceed? (yes/no)"
```

### Node-type migration decision tree

```text
Is the current cluster DC2?
├── NO (already RA3) → Proceed to right-sizing (Step 2) and pricing (Step 3).
└── YES → Is local storage utilisation < 60%?
    ├── YES → Is CPUUtilization < 30% sustained AND QueryQueueLength avg = 0?
    │   ├── YES → OPPORTUNITY_FOUND — migrate to RA3.
    │   │         DC2 nodes exist for storage that RA3 managed storage
    │   │         handles more cheaply. Right-size compute independently.
    │   │         Choose smallest RA3 node that fits CPU headroom.
    │   └── NO → High queue with low CPU = WLM problem.
    │            Fix WLM BEFORE migrating. Do NOT migrate yet.
    └── NO (60-80% storage) → Evaluate RA3 vs keeping DC2.
        Compare DC2 bundled storage cost vs RA3 node + managed storage.
        If RA3 compute + $0.024/GB < DC2 node cost → migrate.
```

## Verdict consistency rules

1. **Zero-savings rule.** If `MONTHLY_SAVING == $0.00` for every dimension,
   verdict MUST be `ALREADY_OPTIMAL`.
2. **OPPORTUNITY_FOUND requires a non-zero savings line** for at least one
   dimension (cost savings) OR a performance recommendation with
   quantified impact (WLM tuning, Concurrency Scaling).
3. **SAVINGS arithmetic check.** Per-dimension savings must sum to total
   annual savings. Round to 2 decimal places.
4. **Reserved Node rule.** Do NOT recommend RIs for Redshift Serverless
   — only for provisioned clusters.
5. **Right-size MUST cite QueryQueueLength** — CPU alone is a guess. Low
   CPU with high queue length indicates a WLM problem, not over-sizing.
6. **Idle deletion requires team verification.**
7. **DC2-to-RA3 must check storage utilisation** — DC2 with > 80% local
   storage used may be cheaper than RA3 + managed storage.

## Error handling — CLI and data-source failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-clusters` returns empty | `len(Clusters) == 0` | No clusters to optimise. ALREADY_OPTIMAL for fleet. |
| CloudWatch CPUUtilization returns empty | `len(Datapoints) == 0` | Cluster may be paused/stopped. Check ClusterStatus. |
| `resize-cluster` returns InvalidClusterState | Resize in progress or incompatible | Wait for current operation to complete. |
| `purchase-reserved-node-offering` fails | Offering ID stale | Re-query for a fresh offering-id. |
| Serverless workgroup not found | `ResourceNotFoundException` | Check workgroup name and region. |
| Concurrency Scaling metrics absent | CS never triggered | CS is enabled but unused — no cost impact. |
| Cluster in `modifying` state | ClusterStatus | Wait for completion before recommending changes. |
| VACUUM running | `STV_TBL_PERM` shows active vacuum | Do not recommend concurrent VACUUMs. |

## Anti-Patterns — NEVER (top 5)

1. NEVER recommend a downsize without QueryQueueLength data — low CPU
   with high queue depth means the cluster is WLM-bottlenecked, not
   overprovisioned. Downsizing a WLM-bottlenecked cluster makes the
   problem worse.
2. NEVER recommend Reserved Nodes for Redshift Serverless — RIs apply
   to provisioned cluster nodes only. Serverless bills on RPU consumed;
   there is no commitment vehicle for Serverless RPU.
3. NEVER enable Concurrency Scaling without checking the cost impact —
   each scaling cluster charges ~$1.08/hour. Sustained scaling (8h+/day)
   is more expensive than adding a Reserved Node.
4. NEVER skip VACUUM before evaluating storage cost — soft-deleted rows
   inflate managed storage on RA3. A VACUUM may reclaim significant
   storage without any node changes.
5. NEVER auto-apply cluster modifications or deletions without the
   CONFIRM gate — resize operations cause downtime; deletions are
   permanent.

## Right-sizing decision tree

Route a right-sizing recommendation through this tree before modifying
any node count.

```
Is CPUUtilization < 30% sustained (14+ day window)?
├── YES → Is QueryQueueLength avg = 0 (no contention)?
│   ├── YES → OPPORTUNITY_FOUND (downsize).
│   │         Reduce node count by 1-2. Verify no WLM bottleneck
│   │         first. Check data sharing consumers.
│   └── NO → High queue with low CPU = WLM problem.
│            Fix WLM (separate queues, enable SQA) BEFORE
│            right-sizing. Do NOT downsize.
└── NO → Is CPUUtilization > 70% sustained?
    ├── YES → Is QueryQueueLength > 100 sustained?
    │   ├── YES → OPPORTUNITY_FOUND (upsize or fix WLM).
    │   │         If WLM is misconfigured, fix WLM first.
    │   │         If WLM is correct, add nodes or enable CS.
    │   └── NO → CPU high but no queue = compute-bound queries.
    │            Upsize or enable Concurrency Scaling.
    └── NO → CPU 30-70% (healthy utilisation).
        └── Is QueryQueueLength < 10 avg?
            ├── YES → Correctly sized. Proceed to Step 3 (pricing).
            └── NO → Moderate queue. Evaluate WLM tuning
                     or Concurrency Scaling before upsizing.
```

Post-tree overrides: Serverless workgroup -> evaluate base/max RPU
(Step 7). DatabaseConnections = 0 for 7+ days -> skip to Step 9 (idle
deletion). DC2 cluster -> evaluate RA3 migration first (Step 1). Status
= `modifying` -> wait for completion.

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

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`resize-cluster`, `delete-cluster`, `create-snapshot`,
  `purchase-reserved-node-offering`), emit and await approval.
- **Snapshot before resize:** `aws redshift create-snapshot` provides a
  rollback path if the new size cannot handle the workload.
- **Schedule during maintenance windows.** `resize-cluster` causes a
  brief outage (elastic resize: 10-20 minutes; classic resize: hours
  depending on data volume).
- **Verify node-type compatibility:** Some node types cannot be mixed.
  All nodes in a cluster must be the same type.
- **Reserved Node purchase is account-level.** Confirm the account ID.
  For Orgs, RIs can be shared via the billing family.
- **One cluster per CONFIRM gate.** Do NOT batch cluster modifications.
- **Check for data sharing dependencies.** If the cluster is a data
  sharing producer, downsizing it impacts all consumer clusters.

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

## References

- `references/redshift-optimization-deep-dive.md` — CLI scripts, WLM
  configuration details, storage analysis, and migration procedures

## Domain

AWS CloudOps / Amazon Redshift Cost Optimisation & Performance Tuning.

## AWS documentation

- **Amazon Redshift Management Guide** — https://docs.aws.amazon.com/redshift/latest/mgmt/welcome.html
- **Amazon Redshift Database Developer Guide** — https://docs.aws.amazon.com/redshift/latest/dg/welcome.html
- **Redshift Node Types** — https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-clusters.html#rs-cluster-plan
- **RA3 Managed Storage** — https://docs.aws.amazon.com/redshift/latest/mgmt/working-with-clusters.html#ra3-managed-storage
- **Workload Management (WLM)** — https://docs.aws.amazon.com/redshift/latest/mgmt/workload-management.html
- **Short Query Acceleration** — https://docs.aws.amazon.com/redshift/latest/mgmt/wlm-short-query-acceleration.html
- **Concurrency Scaling** — https://docs.aws.amazon.com/redshift/latest/mgmt/concurrency-scaling.html
- **Redshift Serverless** — https://docs.aws.amazon.com/redshift/latest/mgmt/serverless-whatis.html
- **Data Sharing** — https://docs.aws.amazon.com/redshift/latest/dg/datasharing.html
- **Materialized Views** — https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-overview.html
- **Redshift ML** — https://docs.aws.amazon.com/redshift/latest/dg/machine-learning.html
- **Amazon Redshift Pricing** — https://aws.amazon.com/redshift/pricing/
- **Reserved Nodes** — https://docs.aws.amazon.com/redshift/latest/mgmt/purchase-reserved-node-instance.html
- **VACUUM** — https://docs.aws.amazon.com/redshift/latest/dg/r_VACUUM_command.html
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
