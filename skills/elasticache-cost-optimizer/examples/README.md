# Example usage: elasticache-cost-optimizer

A walkthrough showing the skill optimising an ElastiCache for Redis
cluster with multi-dimension waste (pre-Graviton nodes, over-provisioned
node size, AOF persistence on an ephemeral cache, no Reserved Node) —
surfacing four actionable opportunities, sizing each with pricing math,
and staging one-dimension-per-window remediation with snapshot rollback.

## Input (user prompt)

> Our orders-cache-rg ElastiCache bill is ~$4,000/month and I'm not sure
> where the waste is. Can you optimise it?

```text
Replication Group: orders-cache-rg
Engine: redis (7.0)
Region: us-east-1
NodeType: cache.m5.2xlarge (8 vCPU, 26.36 GB)
Shards: 3 (cluster mode enabled)
ReplicasPerShard: 1 (total 6 nodes)
Persistence: AOF (append-only file)
Pricing: On-Demand (no Reserved Node)
CloudWatch metrics (last 30 days):
  - CPUUtilization: avg=15%, max=25%
  - EngineCPUUtilization: avg=10%, max=18%
  - CurrConnections: avg=150, max=300
Dataset size: ~10 GB total (3.3 GB per shard)
```

## Skill output

```text
TARGET: orders-cache-rg
VERDICT: OPPORTUNITY_FOUND
REASON: Cluster runs cache.m5.2xlarge (pre-Graviton) with
  EngineCPUUtilization avg 10%, 3 shards x 2 nodes, AOF persistence
  on a cache that rebuilds from RDS, and no Reserved Node after
  12 months steady-state. Four dimensions have actionable opportunities.
RECOMMENDATION:
  Current:
    Nodes: 6 x cache.m5.2xlarge ($0.904/h each) = $3,960/month
    Topology: 3 shards x 2 nodes (primary + 1 replica)
    Persistence: AOF (append-only file)
    Pricing: On-Demand (no RN)
  Proposed:
    - Graviton migration: cache.m5.2xlarge -> cache.r6g.xlarge
      ($0.904/h -> $0.334/h, 63% cheaper, combines gen + right-size).
      EngineCPU avg 10% supports xlarge (4 vCPU).
    - Persistence: disable AOF (cache rebuilds from RDS on restart;
      AOF is redundant and adds write amplification).
    - RN: 1-yr No Upfront RN on cache.r6g.xlarge after migration settles.
  Confidence: HIGH — CloudWatch confirms EngineCPU headroom; CE confirms
    On-Demand spend with no RN discount applied.
ESTIMATED_SAVINGS:
  Monthly (Graviton + right-size): $2,497  (6 x ($0.904-$0.334) x 730)
  Monthly (persistence): $0  (no direct charge; performance tax removed)
  Monthly (reserved node): $732  (40% off 6 x $0.334 x 730)
  Annual total: $38,748
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
  3. Sync data via application dual-write or ElastiCache DMS.
  4. Cut over the application endpoint to the new replication group.
  5. Verify EngineCPUUtilization stays < 60% in 24h on the new nodes.
  6. After 7 days stable, purchase RN:
     aws elasticache purchase-reserved-cache-nodes-offering \
       --reserved-cache-nodes-offering-id <offering-id> \
       --reserved-cache-node-id orders-cache-rn-1yr \
       --cache-node-count 6
  7. Delete the old replication group after verification.
CONFIRM: Before each state-changing CLI, emit and await operator
  approval. Stage changes one dimension per window; never batch
  the Graviton migration + RN purchase.
```

## What the skill caught that a generic assistant misses

1. **EngineCPUUtilization vs CPUUtilization.** A generic assistant looks
   at CPUUtilization (avg 15%) and says "you can downsize." The skill
   checks EngineCPUUtilization (avg 10%) — the Redis engine's own CPU —
   and confirms the downsize is safe. CPUUtilization includes OS overhead
   that can mask Redis engine saturation; EngineCPUUtilization is the
   true constraint for single-threaded Redis.

2. **Graviton + right-size combined.** A generic assistant recommends
   "migrate to Graviton" as one step and "right-size" as another. The
   skill combines both: migrate from cache.m5.2xlarge directly to
   cache.r6g.xlarge (skipping r6g.2xlarge entirely), capturing both the
   ~20% Graviton discount and the 50% right-size in a single migration.

3. **AOF persistence on an ephemeral cache.** A generic assistant
   doesn't question the persistence mode. The skill identifies that AOF
   on a cache which rebuilds from RDS on restart is pure waste — the
   write amplification taxes every command with no durability benefit.
   Disabling AOF removes the performance overhead, potentially enabling
   further downsizing.

4. **RN timing — migrate first, then RN.** A generic assistant might
   recommend buying an RN immediately. The skill sequences the RN
   purchase AFTER the migration so the RN matches the new node type
   (cache.r6g.xlarge, not the old cache.m5.2xlarge). Buying an RN on
   the old type would lock in a discount on a node type you no longer
   run.

5. **Size-flexible RN awareness.** A generic assistant treats RNs as
   fixed. The skill notes that Redis OSS RNs are size-flexible within
   the r6g family — so a cache.r6g.xlarge RN can cover cache.r6g.large
   nodes too if the cluster is further rightsized later.

6. **Staged one-dimension-per-window remediation.** A generic assistant
   stacks all changes into one maintenance window. The skill sequences
   migration -> verification -> RN purchase, with monitoring between
   each, so any CPU spike or failover regression can be attributed to
   a specific change.

7. **Snapshot rollback path.** A generic assistant goes straight to
   create-replication-group with no rollback plan. The skill captures a
   snapshot before any change, providing a recovery path if the new node
   type can't handle the load.

## Slash-command invocation

```
/aws:optimize-elasticache-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "why is our ElastiCache bill so high?"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: elasticache-cost-optimizer]` and hands
off to this skill for the optimisation block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new pattern:

```bash
# Confirm the replication group is healthy post-changes
aws elasticache describe-replication-groups \
  --replication-group-id orders-cache-rg-v2 \
  --query 'ReplicationGroups[0].{Status:Status, Engine:Engine,
    CacheNodeType:CacheNodeType}' --output table

# Verify EngineCPU stays within bounds on the new nodes
aws cloudwatch get-metric-statistics \
  --namespace AWS/ElastiCache \
  --metric-name EngineCPUUtilization \
  --dimensions Name=CacheClusterId,Value=orders-cache-rg-v2-0001 \
  --start-time $(date -u -v-7d +%FT%TZ 2>/dev/null) \
  --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average Maximum --output json

# Verify the node-hour line item drops in CE
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -v-7d +%F 2>/dev/null),End=$(date -u +%F) \
  --filter '{"Dimensions":{"Key":"USAGE_TYPE","Values":["ElastiCache:NodeUsage"]}}' \
  --granularity DAILY --metrics "UsageQuantity" "BlendedCost" \
  --output json
```

If EngineCPU consistently exceeds 60% in the 7 days post-migration,
roll back to the prior node type and re-evaluate.

## Fleet-wide extension

For an Organizations fleet of N ElastiCache clusters:

1. Pull `describe-replication-groups` and CE ElastiCache USAGE_TYPE
   breakdowns across all accounts.
2. Group clusters by waste pattern (pre-Graviton, over-provisioned,
   no RN, over-replicated, AOF on ephemeral).
3. Sort by estimated savings (largest first).
4. Slice into batches of at most 3 clusters; emit per-cluster
   MIGRATION_STEPS and a single CONFIRM per batch.
5. Verify each batch before proceeding to the next.
6. After the per-cluster sweep, evaluate multi-cluster RN strategies
   (size-flexible Redis RNs across clusters where applicable).
