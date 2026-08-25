# Diagnostic Commands — Aurora Cost Optimizer

Load-on-demand pre-flight and diagnostic CLI moved verbatim from SKILL.md.

## Pre-flight — required data sources

```bash
# 1. Aurora cost breakdown (last 30 days)
START=$(date -u -v-30d +%F 2>/dev/null || date -u -d '-30 days' +%F)
END=$(date -u +%F)
aws ce get-cost-and-usage \
  --time-period Start=$START,End=$END \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Aurora"]}}' \
  --granularity MONTHLY --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE --output json > aurora-cost.json

# 2. Cluster + instance + global + RI topology
aws rds describe-db-clusters --output json > aurora-clusters.json
aws rds describe-db-instances \
  --filters Name=engine,Values=aurora-mysql,aurora-postgresql \
  --output json > aurora-instances.json
aws rds describe-global-clusters --output json > aurora-global.json
aws rds describe-reserved-db-instances --output json > aurora-ris.json

# 3. Backtrack inventory (clusters with backtrack enabled)
for cluster in $(jq -r '.DBClusters[].DBClusterIdentifier' aurora-clusters.json); do
  aws rds describe-db-cluster-backtracks --db-cluster-identifier $cluster --output json
done > aurora-backtracks.json

# 4. CloudWatch CPU + Performance Insights top-SQL (per instance)
START_CW=$(date -u -v-30d +%FT%TZ 2>/dev/null || date -u -d '-30 days' +%FT%TZ)
END_CW=$(date -u +%FT%TZ)
for inst in $(jq -r '.DBInstances[].DBInstanceIdentifier' aurora-instances.json); do
  aws cloudwatch get-metric-statistics --namespace AWS/RDS \
    --metric-name CPUUtilization \
    --dimensions Name=DBInstanceIdentifier,Value=$inst \
    --start-time $START_CW --end-time $END_CW \
    --period 3600 --statistics Average Maximum --output json
  aws pi describe-dimension-keys --service-type RDS --identifier $inst \
    --start-time $START_CW --end-time $END_CW \
    --metric db.load.avg --group-by Group=db.sql --output json
done > aurora-cpu-pi.json
```

## Step 2 — Cost Explorer reconciliation

```bash
aws ce get-cost-and-usage \
  --time-period Start=$START,End=$END \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Aurora"]}}' \
  --output json | \
  jq '.ResultsByTime[].Groups[] | {usage: .Keys[0],
    cost: (.Metrics.BlendedCost.Amount | tonumber)}'
```

| USAGE_TYPE | Dimension | What it represents |
|---|---|---|
| `Aurora:InstanceUsage` | Compute (provisioned) | Per-instance-hour by class |
| `Aurora:ServerlessUsage` | Compute (Serverless v2) | Per-ACU-hour |
| `Aurora:StorageUsage` | Storage | Per-GB-month |
| `Aurora:IOUsage` | I/O (Standard tier) | Per-million I/O requests |
| `Aurora:BackupUsage` | Backtrack / snapshots | Per-GB-month |
| `Aurora:ReplicaUsage` | Cross-region replicas | Per-replica-instance-hour |

If `Aurora:IOUsage` is > 30% of total Aurora bill AND the cluster is on
Standard tier, I/O-Optimized is a prime candidate. If
`Aurora:ServerlessUsage` dominates with low CPU, ACU floor is too high.

## Step 11 — Reserved Instance offering lookup

```bash
aws rds describe-reserved-db-instances-offerings \
  --db-instance-class db.r6g.2xlarge \
  --product-description "aurora postgresql" \
  --offering-type "No Upfront" --duration 31536000 --output json
```
