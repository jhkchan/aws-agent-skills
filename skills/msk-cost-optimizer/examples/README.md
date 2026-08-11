# Example usage: msk-cost-optimizer

A walkthrough showing the skill optimising an Amazon MSK cluster with
multi-dimension waste (pre-Graviton brokers, over-provisioned broker
count, oversized EBS volumes, excessive retention, no Serverless
evaluation) — surfacing five actionable opportunities, sizing each with
pricing math, and staging a blue/green migration with MirrorMaker2 sync.

## Input (user prompt)

> Our events-prod-msk cluster bill is ~$1,700/month and I'm not sure
> where the waste is. Can you optimise it?

```text
Cluster: events-prod-msk
Kafka Version: 3.5.1
Region: us-east-1
Broker Type: kafka.m5.large (2 vCPU, 8 GB)
Broker Count: 6
EBS Volume: 1 TB gp3 per broker
Partitions: 120 across 15 topics
Log Retention: 168 hours (7 days)
Compacted Topics: none
Pricing: On-Demand
CloudWatch metrics (last 30 days):
  - BytesInPerSec per broker: avg=2.5, max=5
  - Total BytesInPerSec: avg=15 MB/s
  - KafkaDataLogsDiskUsed: avg=25%, max=35%
  - CpuUser: avg=10%, max=20%
  - MaxOffsetLag: avg=200 (low consumer lag)
Partition-to-broker ratio: 20/broker
```

## Skill output

```text
TARGET: events-prod-msk
VERDICT: OPPORTUNITY_FOUND
REASON: Cluster runs kafka.m5.large (pre-Graviton) with 6 brokers,
  1 TB EBS per broker at 25% disk used, 168h retention on a topic
  that only needs 24h, total ingress 15 MB/s (well under the 50 MB/s
  Serverless candidate range), and Kafka 3.5.1 (Graviton-ready).
  Five dimensions have actionable opportunities.
RECOMMENDATION:
  Current:
    Brokers: 6 x kafka.m5.large ($0.276/h) = $1,209/month
    EBS: 6 x 1 TB gp3 = $480/month
    Retention: 168h (7 days) on events topic
    Partitions: 120 across 15 topics
    Pricing: On-Demand (no commit)
  Proposed:
    - Graviton migration: kafka.m5.large -> kafka.m7g.large ($0.22/h,
      20% cheaper). Kafka 3.5.1 supports Graviton.
    - Broker count: reduce 6 -> 3 brokers (blue/green migration).
      Total ingress 15 MB/s is 5 MB/s/broker on 3 brokers — well within
      capacity. Partition ratio 40/broker (under 400 ceiling).
    - EBS: reduce 1 TB -> 500 GB per broker on new cluster (disk used
      is 25% = 250 GB; 500 GB gives 2x headroom). Enable auto-expand.
    - Retention: reduce events topic from 168h -> 24h (data-replay
      requirement is 24h).
    - Combined: migrate to kafka.m7g.large x 3 brokers with 500 GB EBS
      and 24h retention in a single blue/green migration.
  Confidence: HIGH — CloudWatch confirms low disk utilisation; CE
    confirms On-Demand spend with no discount; Kafka version supports
    Graviton.
ESTIMATED_SAVINGS:
  Monthly (Graviton migration): $122  (3 x ($0.276-$0.22) x 730)
  Monthly (broker count 6->3): $604   (3 x $0.276 x 730)
  Monthly (EBS 1TB->500GB): $120      (3 x 500GB x $0.08)
  Monthly (retention 168h->24h): $411 (storage delta on events topic)
  Annual total: $15,084
  Assumptions: us-east-1 pricing, 730h/month, all changes applied via
    blue/green migration to a new cluster.
MIGRATION_STEPS:
  1. Snapshot current topic configurations and consumer group offsets:
     aws kafka describe-cluster-v2 --cluster-arn $CLUSTER_ARN
     # Record partition count, replication factor, retention per topic
  2. Create the new MSK cluster with optimised config:
     aws kafka create-cluster-v2 \
       --cluster-name events-prod-msk-v2 \
       --provisioned '{"BrokerNodeGroupInfo":{\
         "InstanceType":"kafka.m7g.large",\
         "BrokerCount":3,\
         "StorageInfo":{"VolumeSize":500}},\
         "KafkaVersion":"3.5.1"}'
  3. Set retention to 24h on the events topic in the new cluster:
     kafka-configs --bootstrap-server $NEW_BROKERS \
       --alter --topic events \
       --add-config retention.ms=86400000
  4. Sync data via MirrorMaker2 or MSK Cluster Linking:
     # Start MirrorMaker2 to replicate topics from old -> new cluster
  5. Cut over producers and consumers to the new cluster.
  6. Verify BytesInPerSec, KafkaDataLogsDiskUsed, and MaxOffsetLag
     are stable for 7 days on the new cluster.
  7. Decommission the old cluster:
     aws kafka delete-cluster --cluster-arn $OLD_CLUSTER_ARN
CONFIRM: Before each state-changing CLI, emit and await operator
  approval. Stage the blue/green migration with monitoring between
  each step; never batch the cut-over + decommission.
```

## What the skill caught that a generic assistant misses

1. **Graviton requires Kafka 3.x+.** A generic assistant says "migrate to
   Graviton" without checking the Kafka version prerequisite. The skill
   confirms Kafka 3.5.1 supports Graviton (m7g) before recommending the
   migration. On Kafka 2.8, the skill would flag the version upgrade as
   a prerequisite step.

2. **Broker count reduction requires blue/green, not in-place.** A
   generic assistant says "remove 3 brokers." The skill recognises that
   MSK broker count cannot be reduced in-place — partition leadership is
   distributed across all 6 brokers. The recommendation is a full blue/
   green migration: new 3-broker cluster, MirrorMaker2/Cluster Linking
   sync, cut-over, verify, decommission.

3. **EBS cannot be decreased in-place.** A generic assistant says "shrink
   the EBS volumes." The skill flags that MSK supports online EBS
   increases but NOT decreases — the EBS right-size must happen on the
   new cluster during the blue/green migration, with auto-expand enabled
   to prevent future over-allocation.

4. **Retention is the hidden EBS cost driver.** A generic assistant looks
   at EBS volume size and recommends shrinking. The skill traces the root
   cause: 168h retention on a 15 MB/s topic generates ~2.7 TB of stored
   data. Reducing retention to 24h cuts storage to ~390 GB, directly
   reducing the EBS requirement by 85%.

5. **Serverless break-even awareness.** A generic assistant might
   recommend Serverless for any low-throughput workload. The skill
   computes the ~50 MB/s break-even threshold and confirms that 15 MB/s
   total ingress is a strong Serverless candidate — but also notes that
   if the workload grows above 50 MB/s steady, provisioned with Graviton
   becomes cheaper. The recommendation is condition-aware, not absolute.

6. **Partition-to-broker ratio check.** A generic assistant ignores
   partition count. The skill checks that reducing from 6 to 3 brokers
   keeps the partition-per-broker ratio at 40 (under the 400 ceiling),
   confirming the broker reduction won't create partition overhead
   problems.

7. **Combined blue/green migration.** A generic assistant treats each
   dimension as a separate change. The skill combines all four
   dimensions (Graviton + broker count + EBS + retention) into a single
   blue/green migration, minimising operational disruption while
   capturing all savings.

## Slash-command invocation

```
/aws:optimize-msk-cost
```

Or via the orchestrator:

```
/aws:pipeline
You: "why is our MSK bill so high?"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: msk-cost-optimizer]` and hands
off to this skill for the optimisation block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new pattern:

```bash
# Confirm the new cluster is healthy
aws kafka describe-cluster-v2 \
  --cluster-arn $NEW_CLUSTER_ARN \
  --query 'ClusterInfo.{State:State, BrokerType:.Provisioned.BrokerNodeGroupInfo.InstanceType,
    BrokerCount:.Provisioned.BrokerNodeGroupInfo.BrokerCount}' \
  --output table

# Verify throughput and disk stay within bounds
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka \
  --metric-name KafkaDataLogsDiskUsed \
  --dimensions Name=Cluster_Name,Value=events-prod-msk-v2 \
  --start-time $(date -u -v-7d +%FT%TZ 2>/dev/null) \
  --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average Maximum --output json

# Verify the broker-hour line item drops in CE
aws ce get-cost-and-usage \
  --time-period Start=$(date -u -v-7d +%F 2>/dev/null),End=$(date -u +%F) \
  --filter '{"Dimensions":{"Key":"USAGE_TYPE","Values":["MSK:BrokerUsage"]}}' \
  --granularity DAILY --metrics "UsageQuantity" "BlendedCost" \
  --output json
```

If KafkaDataLogsDiskUsed consistently exceeds 80% in the 7 days post-
migration, increase EBS volume size or reduce retention further.

## Fleet-wide extension

For an Organizations fleet of N MSK clusters:

1. Pull `list-clusters-v2` and CE MSK USAGE_TYPE breakdowns across all
   accounts.
2. Group clusters by waste pattern (pre-Graviton, over-provisioned
   broker count, oversized EBS, long retention, Serverless candidate).
3. Sort by estimated savings (largest first).
4. Slice into batches of at most 3 clusters; emit per-cluster
   MIGRATION_STEPS and a single CONFIRM per batch.
5. Verify each batch before proceeding to the next.
6. After the per-cluster sweep, evaluate multi-cluster strategies
   (consolidating dev/test clusters into a single Serverless cluster).
