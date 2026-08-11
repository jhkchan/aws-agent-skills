---
name: elasticache-cost-optimizer
description: Optimises Amazon ElastiCache cost across seven dimensions — node-type right-sizing (CloudWatch EngineCPUUtilization, CPUUtilization, CurrConnections), Graviton node migration (cache.r6g/r7g ~20% cheaper than cache.m5/r5), Reserved Node vs On-Demand (1yr/3yr, modify-reserved-cache-nodes-offering exchange), replication group topology (fewer larger nodes vs many small, replica count, cluster mode sharding cost), ElastiCache Serverless (auto-scaling, per-GB-hour pricing), persistence cost (AOF vs RDB snapshots), and data tiering (r6gd/r7gd SSD-backed). Distinguishes Redis vs Memcached for cost. Covers latest Serverless, Graviton r7g, and data tiering. Emits OPTIMIZED, OPPORTUNITY_FOUND, or ALREADY_OPTIMAL per cluster with estimated monthly savings.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted cluster configuration, CloudWatch summaries, and billing line items. Live-account optimisation uses aws elasticache describe-replication-groups, describe-cache-clusters --show-cache-node-info, describe-reserved-cache-nodes, describe-reserved-cache-nodes-offerings, aws cloudwatch get-metric-statistics for AWS/ElastiCache CPUUtilization, EngineCPUUtilization, CurrConnections, NetworkBandwidthIn/Out, FreeableMemory, aws ce get-cost-and-usage filtered to Amazon ElastiCache USAGE_TYPEs (ElastiCache:NodeUsage), and modify-reserved-cache-nodes-offering for RN exchange (AWS CLI v2, SSO or key-based credentials). Pricing is us-east-1 published rates as of 2026; re-state regional rates before producing dollar estimates for other regions.
keywords:
- Amazon ElastiCache
- ElastiCache for Redis
- ElastiCache for Memcached
- ElastiCache Serverless
- Graviton
- cache.r6g
- cache.r7g
- cache.r6gd
- data tiering
- Reserved Node
- replication group
- cluster mode
- sharding
- right-sizing
- AOF persistence
- RDB snapshots
- FinOps
- cache cost
tags:
- elasticache
- databases
- cost-optimization
- finops
- right-sizing
- serverless
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
  when_to_use: Reviewing Amazon ElastiCache cluster spend, right-sizing cache node types, evaluating Graviton-based nodes (cache.r6g/r7g vs cache.m5/r5), deciding between On-Demand and Reserved Nodes for steady-state cache clusters, tuning replication group topology (fewer larger nodes vs many small), evaluating ElastiCache Serverless for variable workloads, auditing AOF persistence cost, or evaluating data tiering (r6gd/r7gd) for large datasets.
  when_not_to_use: RDS or Aurora cost optimisation (use rds-cost-optimizer or aurora-cost-optimizer), DynamoDB capacity-mode optimisation (use a DynamoDB specialist), Redis self-managed on EC2 cost optimisation (this skill covers the managed ElastiCache service only), cache performance tuning or eviction policy tuning as the primary goal (use a cache operations workflow; this skill uses metrics only to identify cost waste), or ElastiCache failover operations (use elasticache-failover-operator).
  activation_triggers:
  - optimise ElastiCache cost
  - right-size ElastiCache node
  - ElastiCache Graviton migration
  - cache.r6g vs cache.m5
  - ElastiCache Reserved Node
  - ElastiCache Serverless
  - replication group topology cost
  - ElastiCache cluster mode cost
  - AOF persistence cost
  - ElastiCache data tiering
  - cache node right-sizing
  - ElastiCache FinOps review
  - reduce ElastiCache bill
  - Memcached vs Redis cost
  invocation_schema: 'Input: either (a) an ElastiCache replication group or cache cluster identifier + live-account context, (b) a cluster configuration document (engine, node type, shard count, replicas per shard, persistence mode, pricing model, CloudWatch metrics), OR (c) a fleet description for batch optimisation. Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block per cluster, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL}.'
  invocation_example: "# Minimal valid input (offline classification):\nReplication Group: orders-cache-rg\nEngine: redis (7.0)\nRegion: us-east-1\nNodeType: cache.m5.2xlarge (8 vCPU, 26.36 GB)\nShards: 3 (cluster mode enabled)\nReplicasPerShard: 1 (total 6 nodes)\nPersistence: RDB snapshots (daily)\nPricing: On-Demand (no RN)\nCloudWatch metrics (last 30 days):\n  - CPUUtilization: avg=8%, max=15%\n  - EngineCPUUtilization: avg=5%, max=12%\n  - CurrConnections: avg=120, max=200\nEmit the standard optimisation block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
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

```bash
# 1. ElastiCache cost breakdown (last 30 days)
START=$(date -u -v-30d +%F 2>/dev/null || date -u -d '-30 days' +%F)
END=$(date -u +%F)
aws ce get-cost-and-usage \
  --time-period Start=$START,End=$END \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon ElastiCache"]}}' \
  --granularity MONTHLY --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE --output json > elasticache-cost.json

# 2. Cluster + replication group + RN topology
aws elasticache describe-replication-groups --output json > elasticache-rgs.json
aws elasticache describe-cache-clusters --show-cache-node-info --output json \
  > elasticache-clusters.json
aws elasticache describe-reserved-cache-nodes --output json > elasticache-rns.json
aws elasticache describe-reserved-cache-nodes-offerings --output json \
  > elasticache-rn-offerings.json

# 3. CloudWatch CPUUtilization, EngineCPUUtilization, CurrConnections (per node)
START_CW=$(date -u -v-30d +%FT%TZ 2>/dev/null || date -u -d '-30 days' +%FT%TZ)
END_CW=$(date -u +%FT%TZ)
for node in $(jq -r '.CacheClusters[].CacheNodes[].CacheNodeId' \
  elasticache-clusters.json); do
  for metric in CPUUtilization EngineCPUUtilization CurrConnections \
    NetworkBandwidthInOut FreeableMemory; do
    aws cloudwatch get-metric-statistics --namespace AWS/ElastiCache \
      --metric-name $metric \
      --dimensions Name=CacheClusterId,Value=$node \
      --start-time $START_CW --end-time $END_CW \
      --period 3600 --statistics Average Maximum --output json
  done
done > elasticache-cw.json
```

### Data-quality short-circuits

| Condition | Effect on optimisation |
|---|---|
| Cost Explorer access denied | NEED_MORE_INFO for cost quantification; topology still analysable. |
| Observation window < 14 days | NEED_MORE_INFO: workload may reflect atypical load. Min 14 days; 30 preferred. |
| Cluster in `creating` / `modifying` / `snapshotting` | Wait for `available` before emitting a change recommendation. |
| Global Datastore enabled | Cross-region replication adds full node cost in secondary region; analyse separately. |
| ElastiCache Serverless already in use | Skip the serverless-fit dimension; analyse per-GB-hour billing instead of node-hour. |
| Memcached with no replicas | Replica count dimension not applicable; focus on node size and Graviton. |

## Process — Optimisation logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

- **Graviton (r6g/r7g) is a flat ~20% price cut vs m5/r5, not a
  performance trade-off.** The r6g and r7g generations use AWS Graviton
  processors; for Redis and Memcached workloads they deliver equivalent
  or better throughput at ~20% lower hourly cost. There is no reason to
  stay on m5/r5 unless a specific library or module lacks ARM support.

- **Redis EngineCPUUtilization is the engine's own CPU, not the OS
  total.** Redis is single-threaded for command processing; a node with
  8 vCPU but EngineCPUUtilization avg=60% is near saturation on one
  core. Downsize only when EngineCPUUtilization has clear headroom. For
  Memcached, use CPUUtilization (the engine uses all cores).

- **Each Redis replica is a full node billed at the same hourly rate.**
  ReplicasForShard=2 means 3 nodes per shard (1 primary + 2 replicas).
  The cost scales linearly: 3 shards × 3 nodes = 9 nodes. Most read-
  heavy workloads need only 1 replica per shard for failover; additional
  replicas are only justified when read QPS exceeds a single replica's
  capacity.

- **AOF (append-only file) persistence adds write amplification cost.**
  Every write is appended to the AOF on disk; for high-write workloads,
  this consumes network and I/O that could otherwise serve clients. AOF
  is billed as part of the node (no separate storage charge), but the
  performance tax may force a larger node than otherwise needed. RDB
  snapshots are periodic and lighter. If the cache is truly ephemeral,
  disable persistence entirely.

- **ElastiCache Serverless bills per-GB-hour of data and per-vCPU-hour
  of compute, with no minimum capacity fee.** A serverless cache sitting
  at 1 GB overnight pays only for 1 GB-hour. Provisioned nodes bill the
  full node-hour regardless of usage. The break-even is when the
  workload's steady-state data + compute exceeds ~60-70% of an
  equivalent provisioned node's cost.

- **Reserved Nodes are size-flexible within a family for Redis OSS.** A
  `cache.r6g.large` Redis RN applies to any `cache.r6g.*` Redis node of
  equal or smaller size. Memcached RNs are NOT size-flexible — they are
  tied to the specific node type purchased. Use `modify-reserved-cache-
  nodes-offering` to exchange an unused RN for a different offering
  within the same family (no penalty, pro-rated).

- **Data tiering (r6gd/r7gd) uses SSD-backed cold storage for values
  below a configurable threshold.** This halves the effective cost for
  large datasets with a cold tail (e.g., session stores where 80% of
  keys are inactive). The tiered nodes cost ~10% more per hour but hold
  2x the effective data, so per-GB cost drops ~45%.

- **Cluster mode (sharding) adds a cost: each shard is a full primary +
  replicas.** A 3-shard cluster with 1 replica each = 6 nodes. Sharding
  is for capacity (data doesn't fit one node) or throughput (single
  core saturated), not cost savings. If the dataset fits in one large
  node, non-cluster mode with 1 replica (2 nodes) is cheaper than 3
  shards × 1 replica (6 nodes).

### Step 1: Validate input and data sufficiency

If Cost Explorer access is unavailable AND the caller has not pasted
billing line items, emit NEED_MORE_INFO:

```text
TARGET: <cluster-identifier>
VERDICT: NEED_MORE_INFO
REASON: Cost Explorer access is required to quantify per-dimension
  savings. Without USAGE_TYPE granularity (ElastiCache:NodeUsage), the
  seven dimensions can be analysed qualitatively but the dollar
  savings cannot be computed.
RECOMMENDATION:
  1. Grant the auditor role `ce:GetCostAndUsage`.
  2. Or, paste the top 10 ElastiCache USAGE_TYPE line items from the
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
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon ElastiCache"]}}' \
  --output json | \
  jq '.ResultsByTime[].Groups[] | {usage: .Keys[0],
    cost: (.Metrics.BlendedCost.Amount | tonumber)}'
```

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

Replication group with 3 shards × 2 nodes (primary + replica) on
`cache.r6g.2xlarge` ($0.664/h each in us-east-1). EngineCPUUtilization
avg=12%, max=25%. CurrConnections avg=150. Downsize all nodes to
`cache.r6g.xlarge` ($0.334/h):
- Current: 6 nodes × $0.664 × 730h = $2,908/month
- New: 6 nodes × $0.334 × 730h = $1,463/month
- Monthly savings: $1,445
- Trade-off: less memory per node (13.13 GB vs 26.36 GB). Verify the
  dataset fits at 60% of 13.13 GB (7.88 GB) per shard with headroom.
  If evictions spike, revert to 2xlarge.

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

Cluster with 3 shards × 2 nodes on `cache.m5.2xlarge` ($0.452/h):
- Current: 6 × $0.452 × 730h = $1,980/month
- Migrate to cache.r6g.2xlarge: 6 × $0.334 × 730h = $1,463/month
- Monthly savings: $517 (26%)
- Migration: create a new replication group on r6g, sync via DMS or
  application-level dual-write, cut over the endpoint. No code change.
- After migration, evaluate right-sizing (Step 4) on the new nodes.

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

A `cache.r6g.large` node ($0.167/h = $122/month) holding 3 GB of data,
EngineCPU avg=8%, overnight idle 8h/day. Effective utilisation ~25%.
- Provisioned: $122/month (billed 24/7 regardless of load)
- Serverless: 3 GB × $0.00383 × 730h = $8.39 data + compute ~$10 =
  $18.39/month
- Monthly savings: ~$104 (85%)
- Trade-off: Serverless has a slight cold-start latency on first access
  after idle; verify p99 tolerance.

### Step 7: Replication group topology

| Observation | Recommendation | Savings |
|---|---|---|
| ReplicasPerShard=2, read QPS < single-replica capacity | Reduce to 1 replica per shard | ~33% of replica nodes |
| 3 shards, dataset fits in 1 large node | Consolidate to 1 shard + 1 replica | 4 nodes eliminated |
| Non-cluster mode, dataset > single node memory | Enable cluster mode (shard) | None directly; prevents OOM |
| Cluster mode with 1 shard | Revert to non-cluster (simpler, same cost) | None (operational only) |

**Worked example — replica reduction:**

Replication group with 3 shards × 3 nodes (primary + 2 replicas) on
`cache.r6g.large` ($0.167/h). Read QPS avg=2,000, well within one
replica's capacity (~100,000 QPS for r6g.large).
- Current: 9 nodes × $0.167 × 730h = $1,097/month
- Reduce to 3 shards × 2 nodes (primary + 1 replica):
  6 nodes × $0.167 × 730h = $731/month
- Monthly savings: $366
- Trade-off: failover still works with 1 replica. Read capacity drops
  by 50%, but 2,000 QPS is 2% of one replica's ceiling. Confirm no
  analytics reader depends on the second replica.

### Step 8: Reserved Node evaluation

```bash
aws elasticache describe-reserved-cache-nodes-offerings \
  --cache-node-type cache.r6g.2xlarge \
  --product-description "redis" \
  --offering-type "No Upfront" --duration 31536000 --output json
```

| Pattern | Recommendation | Savings vs On-Demand |
|---|---|---|
| On-Demand, uptime > 6 months, steady load | 1-yr No Upfront RN | ~40% |
| On-Demand, uptime > 18 months, mission-critical | 3-yr No Upfront or Partial | ~60% |
| Burst-reader with spiky load | Keep On-Demand | None |
| Cluster scheduled for migration in < 6 months | No RN (commit outlasts cluster) | None |
| Existing RN on old node type (m5), migrating to r6g | Exchange via modify-reserved-cache-nodes-offering | Pro-rated exchange |

**Reserved node exchange:**

```bash
aws elasticache modify-reserved-cache-nodes-offering \
  --reserved-cache-node-id my-rn-1234 \
  --reserved-cache-nodes-offering-id <new-offering-id>
```

RN exchange is available within the same engine family. No penalty; the
new offering is pro-rated from the exchange date. Use this when
migrating from m5 to r6g and an m5 RN is still active.

### Step 9: Persistence cost optimisation

| Observation | Recommendation | Savings |
|---|---|---|
| AOF enabled on ephemeral cache (rebuildable) | Disable persistence | Node performance tax eliminated |
| AOF on high-write cache | Switch to RDB snapshots (daily) | Reduces write amplification |
| RDB snapshots with 7-day retention on small dataset | Reduce to 1-day or disable | $0.023/GB-month backup savings |
| AOF + RDB both enabled | Pick one; both is redundant | AOF performance tax |
| Persistence on, but never restored from backup in 12 months | Disable or reduce frequency | Full persistence overhead |

AOF persists every write; RDB takes periodic snapshots. For a cache
that is rebuilt from the primary database on restart (e.g., session
store with DB backing), disable persistence entirely — the cache does
not need its own durability.

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

Session store on 6 × `cache.r6g.2xlarge` (26.36 GB each, 158 GB total).
60% of keys are inactive sessions. Migrate to 3 × `cache.r7gd.4xlarge`
(105.42 GB tiered each, 316 GB total, ~2x density):
- Current: 6 × $0.664 × 730h = $2,908/month
- New: 3 × $1.336 × 730h = $2,926/month
- Node-hour cost is similar, BUT the dataset now has 2x headroom with
  fewer nodes — enabling future consolidation or right-sizing. If the
  dataset grows, tiered nodes absorb it without adding nodes.

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

```text
TARGET: sessions-cache-prod
VERDICT: ALREADY_OPTIMAL
REASON: All seven dimensions verified at cost-optimal config:
  cache.r7g.large nodes (latest Graviton), EngineCPU avg 35%,
  1 replica per shard for failover, RDB snapshots (1-day retention),
  1-yr RN on all nodes, no AOF, dataset at 40% of memory.
RECOMMENDATION:
  Current: All dimensions optimal
  Proposed: no change
  Confidence: HIGH — CE confirms 30-day spending stable; CloudWatch
    confirms EngineCPU in the healthy 20-50% band.
ESTIMATED_SAVINGS:
  Monthly (all dimensions): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Continue monthly CE review.
  - Re-evaluate at next dataset growth forecast — if memory exceeds
    60% of node capacity, evaluate data tiering (r7gd).
```

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

When handed an ElastiCache bill and asked "why is this so high?", run
this 60-second triage before deep-diving any single dimension:

1. **Pull CE ElastiCache USAGE_TYPE breakdown.** If nodes are on m5/r5
   generation, the Graviton migration (Step 5) is the first lever —
   flat ~20% cut.
2. **Pull cluster node types + shard count.** A cluster on r6g with
   EngineCPU < 20% = right-size opportunity (Step 4).
3. **Pull replica count per shard.** ReplicasPerShard > 1 with read
   QPS well under a single replica's capacity = topology waste
   (Step 7).
4. **Pull RN inventory.** Long-running clusters On-Demand with no RN =
   RN opportunity (Step 8).
5. **Pull persistence mode.** AOF on an ephemeral cache = persistence
   overhead (Step 9). RDB with long retention on a small dataset =
   backup cost.
6. **Pull Serverless vs provisioned split.** Provisioned clusters with
   overnight idle > 50% = Serverless candidate (Step 6).

If any of the six checks hits, deep-dive the corresponding step. If all
six pass, the cluster is likely ALREADY_OPTIMAL — verify with the full
ordered process.

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

- **ElastiCache Serverless (2024):** Auto-scaling, no node management.
  Per-GB-hour data + per-vCPU-hour compute billing. Break-even against
  provisioned at ~30% avg utilisation; cheaper for variable workloads.
- **Graviton-based nodes — cache.r7g generation (2024-2025):** Latest
  ARM-based nodes; ~8% cheaper than r6g, ~20-33% cheaper than m5/r5.
  Full Redis and Memcached engine support.
- **Data tiering — cache.r6gd / r7gd (2023-2024):** SSD-backed cold
  data offload for large datasets. Halves effective per-GB cost for
  workloads with a cold tail (e.g., session stores). Configurable
  tiering threshold.
- **ElastiCache for Redis 7.2+ (2024):** Native Redis functions,
  ACL improvements, and Sharded Pub/Sub. Verify RN product-description
  matches the new engine version before purchase.
- **Global Datastore cross-region (2024-2025):** Multi-region
  replication for Redis. Each secondary region bills full node cost;
  right-size DR-region clusters independently.
- **Reserved Node exchange via modify-reserved-cache-nodes-offering
  (2024+):** Exchange an active RN for a different offering within
  the same family — no penalty, pro-rated. Use when migrating between
  node generations with an active RN.

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
