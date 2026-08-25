# Elasticache Cost Optimizer — diagnostic & pre-flight commands (load on demand)

Diagnostic, pre-flight, and pricing CLI listings, moved verbatim from SKILL.md.

## pre-flight data-gathering CLI (Cost Explorer, ElastiCache topology, CloudWatch) (moved from SKILL.md lines 137-170)


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

## data-quality short-circuit table (moved from SKILL.md lines 174-182)

| Condition | Effect on optimisation |
|---|---|
| Cost Explorer access denied | NEED_MORE_INFO for cost quantification; topology still analysable. |
| Observation window < 14 days | NEED_MORE_INFO: workload may reflect atypical load. Min 14 days; 30 preferred. |
| Cluster in `creating` / `modifying` / `snapshotting` | Wait for `available` before emitting a change recommendation. |
| Global Datastore enabled | Cross-region replication adds full node cost in secondary region; analyse separately. |
| ElastiCache Serverless already in use | Skip the serverless-fit dimension; analyse per-GB-hour billing instead of node-hour. |
| Memcached with no replicas | Replica count dimension not applicable; focus on node size and Graviton. |


## Cost Explorer reconciliation CLI (Step 2) (moved from SKILL.md lines 266-277)


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

## Reserved Node offering query (Step 8) (moved from SKILL.md lines 418-424)


```bash
aws elasticache describe-reserved-cache-nodes-offerings \
  --cache-node-type cache.r6g.2xlarge \
  --product-description "redis" \
  --offering-type "No Upfront" --duration 31536000 --output json
```

## Reserved node exchange (Step 8) (moved from SKILL.md lines 436-445)

```bash
aws elasticache modify-reserved-cache-nodes-offering \
  --reserved-cache-node-id my-rn-1234 \
  --reserved-cache-nodes-offering-id <new-offering-id>
```

RN exchange is available within the same engine family. No penalty; the
new offering is pro-rated from the exchange date. Use this when
migrating from m5 to r6g and an m5 RN is still active.

