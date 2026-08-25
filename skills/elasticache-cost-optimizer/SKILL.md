---
name: elasticache-cost-optimizer
description: Optimises Amazon ElastiCache cost across seven dimensions — node-type right-sizing (CloudWatch EngineCPUUtilization, CPUUtilization, CurrConnections), Graviton node migration (cache.r6g/r7g ~20% cheaper than cache.m5/r5), Reserved Node vs On-Demand (1yr/3yr, modify-reserved-cache-nodes-offering exchange), replication group topology (fewer larger nodes vs many small, replica count, cluster mode sharding cost), ElastiCache Serverless (auto-scaling, per-GB-hour pricing), persistence cost (AOF vs RDB snapshots), and data tiering (r6gd/r7gd SSD-backed). Distinguishes Redis vs Memcached for cost. Covers latest Serverless, Graviton r7g, and data tiering. Emits OPTIMIZED, OPPORTUNITY_FOUND, or ALREADY_OPTIMAL per cluster with estimated monthly savings.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted cluster configuration, CloudWatch summaries, and billing line items. Live-account optimisation uses aws elasticache describe-replication-groups, describe-cache-clusters --show-cache-node-info, describe-reserved-cache-nodes, describe-reserved-cache-nodes-offerings, aws cloudwatch get-metric-statistics for AWS/ElastiCache CPUUtilization, EngineCPUUtilization...
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
  when_to_use: Reviewing Amazon ElastiCache cluster spend, right-sizing cache node types, evaluating Graviton-based nodes (cache.r6g/r7g vs cache.m5/r5), deciding between On-Demand and Reserved Nodes for steady-state cache clusters, tuning replication group topology (fewer larger nodes vs many small), evaluating ElastiCache Serverless for variable workloads, auditing AOF persistence cost, or evaluating data tiering (r6gd/r7gd) for large datasets.
  when_not_to_use: RDS or Aurora cost optimisation (use rds-cost-optimizer or aurora-cost-optimizer), DynamoDB capacity-mode optimisation (use a DynamoDB specialist), Redis self-managed on EC2 cost optimisation (this skill covers the managed ElastiCache service only), cache performance tuning or eviction policy tuning as the primary goal (use a cache operations workflow; this skill uses metrics only to identify cost waste), or ElastiCache failover operations (use elasticache-failover-operator).
  activation_triggers: optimise ElastiCache cost, right-size ElastiCache node, ElastiCache Graviton migration, cache.r6g vs cache.m5, ElastiCache Reserved Node, ElastiCache Serverless, replication group topology cost, ElastiCache cluster mode cost, AOF persistence cost, ElastiCache data tiering, cache node right-sizing, ElastiCache FinOps review, reduce ElastiCache bill, Memcached vs Redis cost
  invocation_schema: 'Input: either (a) an ElastiCache replication group or cache cluster identifier + live-account context, (b) a cluster configuration document (engine, node type, shard count, replicas per shard, persistence mode, pricing model, CloudWatch metrics), OR (c) a fleet description for batch optimisation. Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block per cluster, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL}.'
  invocation_example: "# Minimal valid input (offline classification):\nReplication Group: orders-cache-rg\nEngine: redis (7.0)\nRegion: us-east-1\nNodeType: cache.m5.2xlarge (8 vCPU, 26.36 GB)\nShards: 3 (cluster mode enabled)\nReplicasPerShard: 1 (total 6 nodes)\nPersistence: RDB snapshots (daily)\nPricing: On-Demand (no RN)\nCloudWatch metrics (last 30 days):\n  - CPUUtilization: avg=8%, max=15%\n  - EngineCPUUtilization: avg=5%, max=12%\n  - CurrConnections: avg=120, max=200\nEmit the standard optimisation block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Amazon ElastiCache, ElastiCache for Redis, ElastiCache for Memcached, ElastiCache Serverless, Graviton, cache.r6g, cache.r7g, cache.r6gd, data tiering, Reserved Node, replication group, cluster mode, sharding, right-sizing, AOF persistence, RDB snapshots, FinOps, cache cost
  tags: elasticache, databases, cost-optimization, finops, right-sizing, serverless
---

# ElastiCache Cost Optimizer

## What this skill does

Optimises Amazon ElastiCache cost across seven dimensions: node-type
right-sizing, Graviton-based node migration, Reserved Node evaluation,
replication group topology, ElastiCache Serverless fit, persistence
cost, and data tiering. Emits a deterministic verdict per cluster with
estimated monthly savings and a one-dimension-per-window migration plan.

## STRICT output contract

Every invocation MUST emit exactly one optimisation block per cluster
in this shape — no prose before, no commentary after:

```text
TARGET: <replication-group-id or cache-cluster-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <engine, node-type, shard count, replicas, persistence,
            pricing model, data tiering>
  Proposed: <per-dimension list of changes>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (right-sizing): $<amount>
  Monthly (Graviton migration): $<amount>
  Monthly (reserved node): $<amount>
  Monthly (topology): $<amount>
  Monthly (serverless fit): $<amount>
  Monthly (persistence): $<amount>
  Monthly (data tiering): $<amount>
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

- **Graviton-based nodes (cache.r6g/r7g) are ~20% cheaper than the
  equivalent cache.m5/r5 generation and are the single highest-leverage
  migration for ElastiCache.** Same vCPU and memory, same Redis/Memcached
  engine; the price drop is architectural. A cluster on `cache.m5.2xlarge`
  ($0.832/h) migrates to `cache.r6g.2xlarge` ($0.664/h) for ~20% off
  with no application change. The r7g generation is cheaper still.
- **EngineCPUUtilization, not CPUUtilization, is the right Redis metric
  for right-sizing.** CPUUtilization includes the OS overhead; the Redis
  engine's own CPU (EngineCPUUtilization) is the real constraint. A node
  with avg EngineCPUUtilization < 20% has significant headroom for
  downsize. For Memcached (multi-AZ, multi-threaded), CPUUtilization is
  the correct metric because the engine uses all cores.
- **ElastiCache Serverless (2024+) eliminates node management and auto-
  scales capacity.** It bills per-GB-hour of data plus per-vCPU-hour of
  compute. Workloads with variable load or overnight idle periods can
  save 30-60% vs provisioned nodes that sit idle. Steady-state workloads
  on large nodes are usually cheaper provisioned.
- **Reserved Nodes are ElastiCache's biggest commit lever for steady-
  state clusters.** A 1-yr no-upfront RN on `cache.r6g.2xlarge` yields
  ~40% discount vs On-Demand; a 3-yr is ~60%. RNs are engine-flexible
  within the same family (Redis OSS RN applies to any Redis OSS node of
  that class) but NOT cross-engine (Redis RN does not cover Memcached).
- **Fewer larger nodes are usually cheaper than many small nodes.** Six
  `cache.r6g.large` (6 × $0.167/h = $1.002/h) cost more than three
  `cache.r6g.2xlarge` (3 × $0.334/h = $1.002/h) at parity, but the
  smaller nodes add operational overhead. The cost breaks even at 2:1
  ratios; beyond that, fewer larger nodes win on per-node overhead.

## Mindset

ElastiCache cost structure differs from databases in three ways: there
is no per-I/O charge (all operations are bundled into the node-hour),
memory is the primary capacity constraint (not CPU), and replication
doubles or triples the node cost (each replica is a full node). The
levers are Graviton generation, node size, replica count, persistence
mode, and RN commits. Most ElastiCache waste comes from (a) legacy
cache.m5/r5 nodes that should be Graviton, (b) over-replicated clusters
with more replicas than the read throughput requires, or (c) AOF
persistence enabled on a cache that doesn't need durability.

## Quick reference — verdict thresholds

| Observation | Verdict | Dimension |
|---|---|---|
| Cluster on cache.m5/r5/c4 (pre-Graviton) | **OPPORTUNITY_FOUND** | Graviton migration |
| EngineCPUUtilization avg < 20% on cache.r6g.2xlarge+ | **OPPORTUNITY_FOUND** | Right-sizing |
| CurrConnections avg < 50 with EngineCPU < 10% | **OPPORTUNITY_FOUND** | Right-sizing or removal |
| Cluster On-Demand, steady > 6 months, no RN | **OPPORTUNITY_FOUND** | Reserved Node |
| ReplicasPerShard > 1 with read QPS < single-node capacity | **OPPORTUNITY_FOUND** | Topology |
| AOF persistence on a cache with RDB backup elsewhere | **OPPORTUNITY_FOUND** | Persistence |
| Dataset > 60% of node memory with cold keys | **OPPORTUNITY_FOUND** | Data tiering |
| Variable load, overnight idle > 50% of hours, provisioned | **OPPORTUNITY_FOUND** | Serverless fit |
| All seven dimensions at cost-optimal config | **ALREADY_OPTIMAL** | (continue monitoring) |

## Pre-flight: data gate (run before any optimisation decision)

ElastiCache optimisation requires four data sources: Cost Explorer for
billing line items, cluster configuration (node types, shards,
replicas, persistence), CloudWatch metrics for utilisation, and the
reserved-node inventory.

### Required data sources
CLI data-gathering commands (Cost Explorer, ElastiCache topology, CloudWatch) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when running the live-account pre-flight data gate.

### Data-quality short-circuits

Data-quality short-circuit table (window length, cluster states, Global Datastore, Serverless, Memcached) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when validating observation windows and cluster states before emitting recommendations.
## Process — Optimisation logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation
Step-0 deep dive on non-obvious ElastiCache cost behaviours (Graviton pricing, EngineCPU vs CPU, replica billing, AOF write amplification, Serverless billing model, RN size-flexibility, data tiering, cluster-mode cost) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before classifying a cluster — each behaviour changes the recommendation if ignored.

### Step 1: Validate input and data sufficiency

If Cost Explorer access is unavailable AND the caller has not pasted
billing line items, emit NEED_MORE_INFO:

Full NEED_MORE_INFO output block moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when the Cost Explorer data gate fails.
### Step 2: Cost Explorer reconciliation
Cost Explorer reconciliation CLI (USAGE_TYPE breakdown) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when quantifying per-dimension spend.

| USAGE_TYPE | Dimension | What it represents |
|---|---|---|
| `ElastiCache:NodeUsage` | Compute (provisioned) | Per-node-hour by type |
| `ElastiCache:ServerlessUsage` | Compute (Serverless) | Per-GB-hour + per-vCPU-hour |
| `ElastiCache:BackupUsage` | Snapshots | Per-GB-month of backup storage |

If `ElastiCache:NodeUsage` dominates with nodes on m5/r5 generation, the
Graviton migration is the first lever. If ServerlessUsage is high with
steady load, the workload may be cheaper on provisioned nodes.

### Step 3: Cost classification

| Cost profile | Indicators | Emphasis |
|---|---|---|
| Pre-Graviton | cache.m5/r5/c4 nodes | Graviton migration (Step 5) |
| Over-provisioned | EngineCPU avg < 20%, low connections | Right-sizing (Step 4) |
| Steady On-Demand | No RN, uptime > 6 months | Reserved Node (Step 8) |
| Over-replicated | ReplicasPerShard > 1, low read QPS | Topology (Step 7) |
| High persistence cost | AOF enabled, high write volume | Persistence (Step 9) |
| Large dataset, cold tail | Memory > 60% full, inactive keys | Data tiering (Step 10) |
| Variable load | Overnight idle, spiky daytime | Serverless fit (Step 6) |
| Mixed (no single dimension dominant) | Even distribution | Apply all in parallel |

### Step 4: Node-type right-sizing

**Decision matrix (Redis — use EngineCPUUtilization):**

| EngineCPU profile (30-day) | Recommendation | Savings estimate |
|---|---|---|
| avg < 20%, max < 40% on cache.r6g.2xlarge | Downsize to cache.r6g.xlarge | ~50% of compute |
| avg 20-50%, max < 70% | Keep current size | None |
| avg > 70% frequently | Upsize or add shards | None — already constrained |
| avg < 10%, CurrConnections < 50 | Consider removal or serverless | 100% if removed |

**Decision matrix (Memcached — use CPUUtilization):**

| CPUUtilization profile (30-day) | Recommendation | Savings estimate |
|---|---|---|
| avg < 20%, max < 40% on cache.m6g.2xlarge | Downsize one step | ~50% |
| avg 20-50% | Keep current | None |
| avg > 70% | Upsize (Memcached uses all cores) | None |

**Worked example — Redis right-sizing:**
Full worked example (6 × cache.r6g.2xlarge → xlarge, $1,445/month) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when right-sizing Redis nodes.

### Step 5: Graviton-based node migration

This is the highest-leverage dimension when the cluster is on a pre-
Graviton generation.

| Current generation | Target | Savings | Notes |
|---|---|---|---|
| cache.m5.large ($0.226/h) | cache.r6g.large ($0.167/h) | ~26% | Same 2 vCPU / 6.05 GB |
| cache.m5.2xlarge ($0.452/h) | cache.r6g.2xlarge ($0.334/h) | ~26% | Same 8 vCPU / 26.36 GB |
| cache.r5.large ($0.250/h) | cache.r6g.large ($0.167/h) | ~33% | r5 → r6g architectural drop |
| cache.r5.2xlarge ($0.500/h) | cache.r6g.2xlarge ($0.334/h) | ~33% | Same class upgrade |
| cache.r6g.large ($0.167/h) | cache.r7g.large ($0.153/h) | ~8% | Further Graviton gen |
| cache.c4.* (legacy) | cache.r7g.* equivalent | ~35-40% | c4 is oldest; large savings |

**Worked example — Graviton migration:**
Full worked example (m5.2xlarge → r6g.2xlarge, $517/month, 26%) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when evaluating Graviton migration.

### Step 6: ElastiCache Serverless fit evaluation

Serverless eliminates node management and auto-scales. The break-even
calculation compares the provisioned node's effective utilisation
against the serverless per-GB-hour + per-vCPU-hour rate.

**Break-even logic:**

```
provisioned_monthly = node_count × node_hourly × 730
serverless_monthly  = (data_GB × $0.00383/h × 730) +
                      (compute_vCPU_hours × $0.045/h × 730)
```

A rough heuristic: if the provisioned cluster sits below 30% average
utilisation (EngineCPU or connections), Serverless is likely cheaper.
If the cluster runs above 60% utilisation steady-state, provisioned
with an RN is cheaper.

| Provisioned utilisation | Recommendation | Rationale |
|---|---|---|
| avg < 20%, overnight idle > 50% | Migrate to Serverless | Pay only for data + compute used |
| avg 20-40%, spiky | Evaluate Serverless; compare 30-day cost | Break-even zone |
| avg > 40% steady | Keep provisioned + RN | Provisioned cheaper at steady load |
| Dataset > 100 GB with steady load | Keep provisioned | Serverless per-GB adds up at scale |

**Worked example — Serverless migration:**
Full worked example ($122/month provisioned → $18.39/month serverless, 85%) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when evaluating Serverless fit.

### Step 7: Replication group topology

| Observation | Recommendation | Savings |
|---|---|---|
| ReplicasPerShard=2, read QPS < single-replica capacity | Reduce to 1 replica per shard | ~33% of replica nodes |
| 3 shards, dataset fits in 1 large node | Consolidate to 1 shard + 1 replica | 4 nodes eliminated |
| Non-cluster mode, dataset > single node memory | Enable cluster mode (shard) | None directly; prevents OOM |
| Cluster mode with 1 shard | Revert to non-cluster (simpler, same cost) | None (operational only) |

**Worked example — replica reduction:**
Full worked example (9 → 6 nodes, $366/month) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when reducing replica count.

### Step 8: Reserved Node evaluation
Reserved Node offering query CLI moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when pricing an RN purchase.

| Pattern | Recommendation | Savings vs On-Demand |
|---|---|---|
| On-Demand, uptime > 6 months, steady load | 1-yr No Upfront RN | ~40% |
| On-Demand, uptime > 18 months, mission-critical | 3-yr No Upfront or Partial | ~60% |
| Burst-reader with spiky load | Keep On-Demand | None |
| Cluster scheduled for migration in < 6 months | No RN (commit outlasts cluster) | None |
| Existing RN on old node type (m5), migrating to r6g | Exchange via modify-reserved-cache-nodes-offering | Pro-rated exchange |

**Reserved node exchange:**

Reserved node exchange CLI and exchange rules moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand when migrating node generations with an active RN.
### Step 9: Persistence cost optimisation

| Observation | Recommendation | Savings |
|---|---|---|
| AOF enabled on ephemeral cache (rebuildable) | Disable persistence | Node performance tax eliminated |
| AOF on high-write cache | Switch to RDB snapshots (daily) | Reduces write amplification |
| RDB snapshots with 7-day retention on small dataset | Reduce to 1-day or disable | $0.023/GB-month backup savings |
| AOF + RDB both enabled | Pick one; both is redundant | AOF performance tax |
| Persistence on, but never restored from backup in 12 months | Disable or reduce frequency | Full persistence overhead |

Persistence deep dive (AOF vs RDB mechanics, when to disable persistence) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when auditing persistence cost (Step 9).
### Step 10: Data tiering evaluation (r6gd/r7gd)

Data tiering automatically moves infrequently accessed items to SSD,
halving the effective per-GB cost for datasets with a cold tail.

| Observation | Recommendation | Savings |
|---|---|---|
| Dataset > 60% of node memory, > 50% keys inactive | Migrate to r6gd/r7gd (tiered) | ~45% per-GB cost |
| Dataset < 30% of node memory | Standard r6g/r7g (no tiering needed) | None |
| All keys hot (no cold tail) | Standard r6g/r7g (tiering adds overhead) | None |
| Using 4+ nodes to hold a large dataset | Consolidate to fewer r6gd nodes | Node count reduction |

**Worked example — data tiering:**
Full worked example (6 × r6g.2xlarge → 3 × r7gd.4xlarge) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when evaluating data tiering (Step 10).

### Step 11: Final verdict

The verdict is the worst-case (most-actionable) finding across all
seven dimensions:

- If ANY dimension has a concrete recommendation with quantified
  savings, verdict is **OPPORTUNITY_FOUND**.
- If a change was applied and verified this session, verdict is
  **OPTIMIZED**.
- If all dimensions are at cost-optimal config AND RN evaluation has
  been considered, verdict is **ALREADY_OPTIMAL**.

## Output format

### Worked example — multi-dimension opportunity

```text
TARGET: orders-cache-rg
VERDICT: OPPORTUNITY_FOUND
REASON: Cluster runs cache.m5.2xlarge (pre-Graviton) with
  EngineCPUUtilization avg 12%, 3 shards x 2 nodes, AOF persistence
  on an ephemeral cache, and no Reserved Node after 12 months
  steady-state. Four dimensions have actionable opportunities.
RECOMMENDATION:
  Current:
    Nodes: 6 x cache.m5.2xlarge ($0.452/h each) = $1,980/month
    Topology: 3 shards x 2 nodes (primary + 1 replica)
    Persistence: AOF (append-only file)
    Pricing: On-Demand (no RN)
  Proposed:
    - Graviton migration: cache.m5.2xlarge -> cache.r6g.2xlarge
      ($0.334/h, 26% cheaper). No application change.
    - Right-sizing: EngineCPU avg 12% / max 25% on r6g.2xlarge ->
      downsize to cache.r6g.xlarge ($0.334/h -> $0.167/h).
    - Persistence: disable AOF (cache is rebuilt from RDS on restart;
      persistence is redundant).
    - RN: 1-yr No Upfront RN on cache.r6g.xlarge after migration settles.
  Confidence: HIGH — CloudWatch confirms EngineCPU headroom; CE confirms
    On-Demand spend with no RN discount applied.
ESTIMATED_SAVINGS:
  Monthly (Graviton migration): $517  (6 x ($0.452-$0.334) x 730)
  Monthly (right-sizing): $731    (6 x ($0.334-$0.167) x 730)
  Monthly (persistence): $0       (no direct charge; performance tax)
  Monthly (reserved node): $292   (40% off 6 x $0.167 x 730)
  Monthly (topology): $0
  Annual total: $18,480
  Assumptions: us-east-1 pricing, 730h/month, Graviton + right-size
    applied before RN purchase so RN matches the new node type.
MIGRATION_STEPS:
  1. Snapshot the replication group before any change:
     aws elasticache create-snapshot \
       --cache-cluster-id orders-cache-rg-0001 \
       --snapshot-name pre-opt-$(date +%s)
  2. Create the new replication group on cache.r6g.xlarge:
     aws elasticache create-replication-group \
       --replication-group-id orders-cache-rg-v2 \
       --replication-group-description "Orders cache r6g" \
       --engine redis --cache-node-type cache.r6g.xlarge \
       --num-cache-clusters 6
  3. Sync data via application dual-write or ElastiCache DMS:
     # Start dual-writing to both clusters; wait for sync to converge
  4. Cut over the application endpoint to the new replication group.
  5. Verify EngineCPUUtilization stays < 60% in 24h on the new nodes.
  6. Disable AOF on the new group if not already:
     aws elasticache modify-replication-group \
       --replication-group-id orders-cache-rg-v2 \
       --append-only no --apply-immediately
  7. After 7 days stable, purchase RN:
     aws elasticache purchase-reserved-cache-nodes-offering \
       --reserved-cache-nodes-offering-id <offering-id> \
       --reserved-cache-node-id orders-cache-rn-1yr \
       --cache-node-count 6
  8. Delete the old replication group after verification:
     aws elasticache delete-replication-group \
       --replication-group-id orders-cache-rg
CONFIRM: Before each state-changing CLI, emit and await operator
  approval. Stage changes one dimension per window; never batch
  the Graviton migration + right-size + RN purchase.
```

### Worked example — already optimal
Full ALREADY_OPTIMAL worked example moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand when all seven dimensions pass.

## Anti-Patterns — NEVER do these things

- **NEVER recommend Graviton migration without confirming engine
  module compatibility.** Redis modules (RedisJSON, RedisSearch,
  RedisGraph) may have limited ARM support in older ElastiCache engine
  versions. Verify the engine version supports all loaded modules on
  Graviton before recommending migration.

- **NEVER recommend downsize based on CPUUtilization alone for Redis.**
  Redis is single-threaded for command processing; CPUUtilization (OS-
  level) can look low while the Redis engine thread is saturated.
  Always check EngineCPUUtilization before recommending a Redis node
  downsize. For Memcached, CPUUtilization is correct.

- **NEVER recommend reducing replicas below 1 per shard for a
  production Redis cluster.** A single-node shard has no failover
  target; if the primary fails, the shard is lost. Always retain at
  least 1 replica for HA unless the cluster is explicitly non-critical.

- **NEVER recommend disabling AOF without confirming the cache's
  rebuild strategy.** If the application cannot rebuild the cache from
  a primary database on restart (e.g., computed values with no source),
  disabling persistence means a full cache warm-up cost on every
  failover. Confirm the rebuild path before disabling.

- **NEVER recommend ElastiCache Serverless for a steady-state
  workload above 60% utilisation without computing the break-even.**
  Serverless per-GB-hour + per-vCPU-hour pricing exceeds provisioned
  node cost at high steady utilisation. Always compute the 30-day
  projected Serverless cost and compare against the provisioned +
  RN cost before recommending migration.

- NEVER recommend a 3-year RN on a cluster with active migration plans.
  The RN outlasts the cluster and the commitment is billed whether or
  not the cluster exists. Match RN term to expected cluster lifetime.
- NEVER recommend adding shards for cost savings — sharding is for
  capacity or throughput, not cost. Each shard adds a full primary +
  replicas.
- NEVER exchange an RN via modify-reserved-cache-nodes-offering
  without confirming the new offering's engine and node type match
  the target cluster.
- NEVER batch the Graviton migration + node right-size + RN purchase
  in one maintenance window. Stack the changes one dimension per
  window so any regression can be attributed to a specific change.
- NEVER purchase a Memcached RN expecting size flexibility — Memcached
  RNs are tied to the specific node type; only Redis OSS RNs are
  size-flexible within a family.

## Quick navigation

| You want to... | Jump to |
|---|---|
| Evaluate Graviton migration (m5/r5 -> r6g/r7g) | Step 5 — Graviton migration |
| Right-size cache nodes (Redis) | Step 4 — Node right-sizing |
| Evaluate ElastiCache Serverless | Step 6 — Serverless fit |
| Reduce replica count / topology | Step 7 — Replication group topology |
| Decide on a Reserved Node | Step 8 — RN evaluation |
| Audit AOF / RDB persistence | Step 9 — Persistence cost |
| Evaluate data tiering (r6gd/r7gd) | Step 10 — Data tiering |
| Handle missing data | Step 1 — Validate input |
| Look up pricing / node types | references/elasticache-pricing-reference.md |

## Expert heuristic — the 60-second triage
The 60-second bill triage (six ordered checks mapping symptoms to steps) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when triaging an ElastiCache bill before deep-diving.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-replication-group`, `modify-replication-group`, `delete-
  replication-group`, `create-snapshot`, `purchase-reserved-cache-
  nodes-offering`, `modify-reserved-cache-nodes-offering`), emit and
  await operator approval.
- **Snapshot before any change.** Capture a cache snapshot:
  ```bash
  aws elasticache create-snapshot \
    --cache-cluster-id $CLUSTER \
    --snapshot-name pre-opt-$(date +%s)
  ```
- **One dimension per maintenance window.** Graviton migration, node
  right-size, and RN purchase each alter cost / capacity; stacking
  them obscures which change produced any observed impact.
- **Verify EngineCPU after downsize.** Watch EngineCPUUtilization for
  24h; if avg exceeds 60%, roll back to the prior node type.
- **Replica reduction one shard at a time.** Keep one shard at full
  replica count during the transition so failover capacity is preserved.
- **Bulk-operation safety limit.** When optimising a fleet of clusters:
  sort by estimated savings (largest first); slice into batches of at
  most 3 clusters; emit per-cluster MIGRATION_STEPS with a single
  CONFIRM per batch; re-query with `describe-replication-groups` and
  verify availability before emitting the NEXT batch; abort the sweep
  if any cluster fails to stabilise within 30 min. The skill MUST NOT
  emit remediation CLI for more than 3 clusters in a single output block.

## Verdict semantics

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension has a savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; CE line items confirm the new pattern. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All seven dimensions at cost-optimal config AND RN evaluation considered. | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed: CE access denied, CloudWatch window < 14 days. | Pre-decision — emit per-dimension; other dimensions can still emit OPPORTUNITY_FOUND. |

## Recent AWS features (2024-2026)
Recent AWS features (Serverless billing, r7g, data tiering, Redis 7.2+, Global Datastore, RN exchange) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when checking feature-dependent recommendations.

## References (load on demand)

- [references/worked-examples.md](references/worked-examples.md) — secondary worked examples: NEED_MORE_INFO block, right-sizing, Graviton, Serverless, replica-reduction, data-tiering, and ALREADY_OPTIMAL.
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — pre-flight data-gathering CLI, data-quality short-circuits, Cost Explorer reconciliation, RN offering query and exchange.
- [references/advanced-patterns.md](references/advanced-patterns.md) — Step-0 non-obvious behaviours, persistence deep dive, 60-second bill triage, recent AWS features.
- [references/elasticache-pricing-reference.md](references/elasticache-pricing-reference.md) — node-type pricing lookup.

## AWS documentation

Domain: AWS CloudOps / Databases — Amazon ElastiCache cost optimisation.

- **Amazon ElastiCache pricing** — https://aws.amazon.com/elasticache/pricing/
- **ElastiCache Serverless** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/elasticache-serverless.html
- **ElastiCache node types** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/CacheNodes.SupportedTypes.html
- **Data tiering** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/data-tiering.html
- **Reserved Nodes** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/reserved-nodes.html
- **AOF vs RDB persistence** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/backups.html
- **Global Datastore** — https://docs.aws.amazon.com/AmazonElastiCache/latest/red-ug/Redis-Global-Datastore.html
- **AWS Cost Explorer** — https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
- **Well-Architected — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
