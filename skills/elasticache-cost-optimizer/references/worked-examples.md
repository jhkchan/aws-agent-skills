# Elasticache Cost Optimizer — worked examples (load on demand)

Secondary worked examples, moved verbatim from SKILL.md.

## NEED_MORE_INFO output block (Step 1) (moved from SKILL.md lines 246-264)

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


## worked example — Redis right-sizing (Step 4) (moved from SKILL.md lines 322-332)


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

## worked example — Graviton migration (Step 5) (moved from SKILL.md lines 349-356)


Cluster with 3 shards × 2 nodes on `cache.m5.2xlarge` ($0.452/h):
- Current: 6 × $0.452 × 730h = $1,980/month
- Migrate to cache.r6g.2xlarge: 6 × $0.334 × 730h = $1,463/month
- Monthly savings: $517 (26%)
- Migration: create a new replication group on r6g, sync via DMS or
  application-level dual-write, cut over the endpoint. No code change.
- After migration, evaluate right-sizing (Step 4) on the new nodes.

## worked example — Serverless migration (Step 6) (moved from SKILL.md lines 385-393)


A `cache.r6g.large` node ($0.167/h = $122/month) holding 3 GB of data,
EngineCPU avg=8%, overnight idle 8h/day. Effective utilisation ~25%.
- Provisioned: $122/month (billed 24/7 regardless of load)
- Serverless: 3 GB × $0.00383 × 730h = $8.39 data + compute ~$10 =
  $18.39/month
- Monthly savings: ~$104 (85%)
- Trade-off: Serverless has a slight cold-start latency on first access
  after idle; verify p99 tolerance.

## worked example — replica reduction (Step 7) (moved from SKILL.md lines 405-415)


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

## worked example — data tiering (Step 10) (moved from SKILL.md lines 474-482)


Session store on 6 × `cache.r6g.2xlarge` (26.36 GB each, 158 GB total).
60% of keys are inactive sessions. Migrate to 3 × `cache.r7gd.4xlarge`
(105.42 GB tiered each, 316 GB total, ~2x density):
- Current: 6 × $0.664 × 730h = $2,908/month
- New: 3 × $1.336 × 730h = $2,926/month
- Node-hour cost is similar, BUT the dataset now has 2x headroom with
  fewer nodes — enabling future consolidation or right-sizing. If the
  dataset grows, tiered nodes absorb it without adding nodes.

## worked example — already optimal (moved from SKILL.md lines 565-585)


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
