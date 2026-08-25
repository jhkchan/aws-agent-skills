# Diagnostic and Pre-flight Commands — MSK Cost Optimizer

## Required data sources (pre-flight data-gathering commands)

```bash
# 1. MSK cost breakdown (last 30 days)
START=$(date -u -v-30d +%F 2>/dev/null || date -u -d '-30 days' +%F)
END=$(date -u +%F)
aws ce get-cost-and-usage \
  --time-period Start=$START,End=$END \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Managed Streaming for Kafka"]}}' \
  --granularity MONTHLY --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE --output json > msk-cost.json

# 2. Cluster configuration
aws kafka describe-cluster-v2 --cluster-arn $CLUSTER_ARN \
  --output json > msk-cluster.json
aws kafka describe-configuration \
  --arn $(jq -r '.ClusterInfo.Provisioned.BrokerNodeGroupInfo \
    .ConfigurationInfo.Arn' msk-cluster.json) \
  --output json > msk-config.json

# 3. CloudWatch metrics (per broker)
START_CW=$(date -u -v-30d +%FT%TZ 2>/dev/null || date -u -d '-30 days' +%FT%TZ)
END_CW=$(date -u +%FT%TZ)
for broker in $(seq 1 $(jq -r '.ClusterInfo.Provisioned \
  .CurrentBrokerSoftwareInfo.Version | length' msk-cluster.json)); do
  for metric in BytesInPerSec BytesOutPerSec KafkaDataLogsDiskUsed \
    CpuUser CpuSystem; do
    aws cloudwatch get-metric-statistics --namespace AWS/Kafka \
      --metric-name $metric \
      --dimensions Name=Cluster_Name,Value=$CLUSTER_NAME \
        Name=Broker_ID,Value=$broker \
      --start-time $START_CW --end-time $END_CW \
      --period 3600 --statistics Average Maximum --output json
  done
done > msk-cw.json

# 4. Topic-level configuration (partition count, retention)
aws kafka list-topics --cluster-arn $CLUSTER_ARN --output json > msk-topics.json
```

## Step 1 fallback commands (data sufficiency without Cost Explorer access)

```text
TARGET: <cluster-name>
VERDICT: NEED_MORE_INFO
REASON: Cost Explorer access is required to quantify per-dimension
  savings. Without USAGE_TYPE granularity (MSK:BrokerUsage,
  MSK:ServerlessUsage), the seven dimensions can be analysed
  qualitatively but the dollar savings cannot be computed.
RECOMMENDATION:
  1. Grant the auditor role `ce:GetCostAndUsage`.
  2. Or, paste the top 10 MSK USAGE_TYPE line items from the
     last 30 days of CUR.
ESTIMATED_SAVINGS: $0 (cannot quantify without CUR data)
MIGRATION_STEPS:
  - IAM policy addition:
    {"Effect":"Allow",
     "Action":["ce:GetCostAndUsage","ce:GetDimensionValues"],
     "Resource":"*"}
```

## Step 2 — Cost Explorer reconciliation commands

```bash
aws ce get-cost-and-usage \
  --time-period Start=$START,End=$END \
  --granularity MONTHLY \
  --metrics "BlendedCost" "UsageQuantity" \
  --group-by Type=DIMENSION,Key=USAGE_TYPE \
  --filter '{"Dimensions":{"Key":"SERVICE","Values":["Amazon Managed Streaming for Kafka"]}}' \
  --output json | \
  jq '.ResultsByTime[].Groups[] | {usage: .Keys[0],
    cost: (.Metrics.BlendedCost.Amount | tonumber)}'
```

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-cluster-v2`, `update-cluster-configuration`, `update-broker-
  storage`, `delete-cluster`, `kafka-configs --alter`), emit and await
  operator approval.
- **Record current state before any change.** Capture topic configs and
  consumer group offsets:
  ```bash
  aws kafka describe-cluster-v2 --cluster-arn $CLUSTER_ARN
  # Record partition count, replication factor, retention per topic
  # Record consumer group offsets for rollback
  ```
- **One dimension per migration window.** Broker type change, broker
  count change, and retention change each alter cluster behaviour;
  stacking them obscures which change produced any observed impact.
- **Verify throughput after broker change.** Watch BytesInPerSec and
  MaxOffsetLag for 7 days; if consumer lag grows, the new broker type
  is underpowered — roll back via the blue/green migration path.
- **Blue/green migration for broker count reduction.** Never remove
  brokers from a running cluster — create a new cluster with the
  target broker count, sync via MirrorMaker2 or Cluster Linking, cut
  over, verify, decommission.
- **Bulk-operation safety limit.** When optimising a fleet of clusters:
  sort by estimated savings (largest first); slice into batches of at
  most 3 clusters; emit per-cluster MIGRATION_STEPS with a single
  CONFIRM per batch; verify each cluster is ACTIVE before emitting the
  NEXT batch; abort the sweep if any cluster fails to stabilise within
  30 min. The skill MUST NOT emit remediation CLI for more than 3
  clusters in a single output block.

