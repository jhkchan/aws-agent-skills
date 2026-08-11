---
description: Optimises Amazon ElastiCache cost through node-type right-sizing (CloudWatch EngineCPUUtilization, CPUUtilization, CurrConnections), Graviton-based node migration (cache.r6g/r7g ~20% cheaper than cache.m5/r5), replication group topology (fewer larger nodes vs many small, replica count, shard count cost impact), ElastiCache Serverless evaluation (per-GB-hour break-even vs provisioned), Reserved Node vs On-Demand (1yr/3yr with modify-reserved-cache-nodes-offering exchange), persistence cost (AOF vs RDB vs none), and data tiering (r6gd/r7gd SSD-backed). Emits a deterministic VERDICT, recommendation, and estimated monthly savings per cluster.
nl_triggers:
  - "optimise ElastiCache cost"
  - "right-size ElastiCache node"
  - "ElastiCache Graviton migration"
  - "cache.r6g vs cache.m5"
  - "ElastiCache Reserved Node"
  - "ElastiCache Serverless"
  - "replication group topology cost"
  - "ElastiCache cluster mode cost"
  - "AOF persistence cost"
  - "ElastiCache data tiering"
  - "cache node right-sizing"
  - "ElastiCache FinOps review"
  - "reduce ElastiCache bill"
  - "Memcached vs Redis cost"
  - "EngineCPUUtilization right-size"
routes_to: elasticache-cost-optimizer
---

# /aws:optimize-elasticache-cost

Activate the `elasticache-cost-optimizer` skill and right-size Amazon
ElastiCache clusters for cost optimisation using the seven-dimension
analysis framework.

## What it does

Reads a cluster's configuration (node type, engine, shard count, replicas
per shard, persistence mode, pricing model) plus 14-30 day CloudWatch
metrics (CPUUtilization, EngineCPUUtilization, CurrConnections,
NetworkBandwidthIn/Out, FreeableMemory), then applies the ordered
optimisation logic:

1. **Pre-flight** — data sufficiency gate. If CloudWatch data is
   insufficient or observation window < 14 days, emit NEED_MORE_INFO.
2. **Cost Explorer reconciliation** — ElastiCache:NodeUsage breakdown to
   identify the dominant cost driver (compute vs backup vs serverless).
3. **Graviton migration** — cache.m5/r5/c4 (pre-Graviton) → cache.r6g/r7g
   for ~20-33% flat cost reduction. No application change.
4. **Node-type right-sizing** — EngineCPUUtilization (Redis) or
   CPUUtilization (Memcached) < 20% → downsize one step; verify dataset
   fits in new node memory.
5. **ElastiCache Serverless fit** — variable load with overnight idle >
   50% → evaluate Serverless per-GB-hour vs provisioned node-hour break-
   even. Steady > 60% utilisation → keep provisioned + RN.
6. **Replication group topology** — ReplicasPerShard > 1 with read QPS
   well under single-replica capacity → reduce to 1 replica per shard.
   Shards where dataset fits in one large node → consolidate.
7. **Reserved Node** — On-Demand steady > 6 months → 1-yr/3-yr No Upfront
   RN. Redis OSS RNs are size-flexible within a family; Memcached RNs
   are fixed. Exchange via modify-reserved-cache-nodes-offering.
8. **Persistence** — AOF on ephemeral cache → disable. AOF + RDB both
   enabled → pick one. RDB with long retention on small dataset → reduce.
9. **Data tiering** — dataset > 60% of node memory with > 50% inactive
   keys → migrate to r6gd/r7gd (SSD-backed, ~45% per-GB savings).
10. **Verdict** — OPPORTUNITY_FOUND (any dimension has a recommendation),
    OPTIMIZED (applied and verified), or ALREADY_OPTIMAL (no change
    needed).

Emits a deterministic optimisation block per cluster:

```text
TARGET: <replication-group-id or cache-cluster-id>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <engine> <node-type> <shards>x<replicas> <persistence> at <pricing-model>
  Proposed: <engine> <node-type> <shards>x<replicas> <persistence> at <pricing-model>
  Dimensions: <list of applicable dimensions>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly (Graviton migration): $<amount>
  Monthly (right-sizing): $<amount>
  Monthly (reserved node): $<amount>
  Monthly (topology): $<amount>
  Monthly (serverless fit): $<amount>
  Monthly (persistence): $<amount>
  Annual total: $<amount>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a cluster configuration and ask any of:

- "right-size this ElastiCache node"
- "should I migrate to Graviton cache nodes?"
- "is this ElastiCache cluster oversized?"
- "should I buy a Reserved Node for this cache?"
- "is ElastiCache Serverless cheaper for this workload?"
- "do I need AOF persistence on this cache?"
- "can I reduce replica count on this Redis cluster?"

A bare replication group ID + any optimise verb ("optimise this cache",
"reduce ElastiCache cost") also routes here via the orchestrator.

## Inputs

- Cluster metadata: replication group ID, engine (redis/memcached), node
  type, shard count, replicas per shard, persistence mode, pricing model.
- CloudWatch metrics (last 14-30 days):
  - `CPUUtilization` (always available)
  - `EngineCPUUtilization` (required for Redis right-size)
  - `CurrConnections` (idle-cluster detection)
  - `NetworkBandwidthIn/Out` (throughput assessment)
  - `FreeableMemory` (memory headroom for downsize)
- Cost Explorer (optional but HIGH confidence requires it):
  - ElastiCache:NodeUsage breakdown by node type
- Workload context: production vs dev/test, steady vs variable, read-
  heavy vs write-heavy, dataset rebuild source.

## Outputs

- One optimisation block per cluster.
- Confidence level with rationale (HIGH requires CloudWatch data + CE
  breakdown + clear thresholds).
- Estimated monthly and annual savings, broken down by dimension
  (Graviton, right-size, RN, topology, serverless, persistence, tiering).
- Specific migration steps with CLI commands (create-replication-group
  for migration, modify-replication-group for right-size, purchase-
  reserved-cache-nodes-offering for RN).
- Rollback path (pre-change snapshot) for production migrations.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for ElastiCache cost).
- `/aws:optimize-rds-cost` for the database cost-optimisation sibling —
  ElastiCache and RDS are typically compared for caching vs database
  workloads.
- `/aws:audit-elasticache-cache` for the security and configuration audit
  of an ElastiCache cluster (complements this cost-focused optimisation).
