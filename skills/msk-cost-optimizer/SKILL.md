---
name: msk-cost-optimizer
description: Optimises Amazon MSK cost across seven dimensions — broker type right-sizing (CloudWatch BytesInPerSec, KafkaDataLogsDiskUsed, consumer lag MaxOffsetLag), broker count optimisation (minimum 3 for HA, reduce excess on low-throughput clusters), EBS storage optimisation (storage-auto-scaling vs fixed gp3, right-size to retention needs), MSK Serverless vs provisioned (break-even ~50 MB/s ingress), partition count impact (excessive partitions add broker overhead), data retention optimisation (log retention hours, compacted topics for changelog workloads), and Graviton broker migration (Kafka 3.x, kafka.m7g ~20% cheaper). Covers MSK Cluster Tier (Express) and MSK with KRaft. Emits OPTIMIZED, OPPORTUNITY_FOUND, or ALREADY_OPTIMAL per cluster with estimated monthly savings.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted cluster configuration, CloudWatch summaries, and billing line items. Live-account optimisation uses aws kafka describe-cluster, describe-cluster-v2, list-clusters-v2, aws kafka describe-configuration, aws cloudwatch get-metric-statistics for AWS/Kafka BytesInPerSec, BytesOutPerSec, KafkaDataLogsDiskUsed, ConsumerLagMetrics MaxOffsetLag, CpuUser, CpuSystem, aws ce get-cost-and-usage filtered to Amazon MSK USAGE_TYPEs (MSK:BrokerUsage, MSK:ServerlessUsage), and aws kafka update-broker-storage / update-cluster-configuration for remediation (AWS CLI v2, SSO or key-based credentials). Pricing is us-east-1 published rates as of 2026; re-state regional rates before producing dollar estimates for other regions.
keywords:
- Amazon MSK
- Amazon Managed Streaming for Apache Kafka
- MSK Serverless
- MSK Express
- MSK Cluster Tier
- MSK KRaft
- Graviton brokers
- kafka.m7g
- broker right-sizing
- EBS storage optimisation
- log retention
- compacted topics
- partition count
- consumer lag
- KafkaDataLogsDiskUsed
- data retention
- FinOps
- streaming cost
tags:
- msk
- kafka
- analytics
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
  family: Analytics
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Reviewing Amazon MSK cluster spend, right-sizing Kafka broker types, evaluating Graviton brokers (kafka.m7g vs kafka.m5), deciding between MSK Serverless and provisioned (break-even ~50 MB/s), optimising broker count (minimum 3 for HA, reduce excess), auditing EBS storage allocation vs actual disk usage, tuning log retention hours or compacted topics for storage savings, or evaluating MSK Cluster Tier (Express) and MSK with KRaft for cost.
  when_not_to_use: Self-managed Kafka on EC2 cost optimisation (this skill covers the managed MSK service only), Kafka Connect or MSK Connect cost optimisation (use kafka-connect-troubleshooter or a Connect specialist), Kinesis Data Streams cost optimisation (different service), Kafka performance tuning or partition rebalancing as the primary goal (use a Kafka operations workflow; this skill uses metrics only to identify cost waste), or MSK security or TLS configuration (use a security audit workflow).
  activation_triggers:
  - optimise MSK cost
  - right-size MSK broker
  - MSK Graviton migration
  - kafka.m7g vs kafka.m5
  - MSK Serverless vs provisioned
  - MSK broker count
  - MSK EBS storage optimisation
  - MSK log retention
  - MSK compacted topics
  - MSK partition count
  - MSK Cluster Tier Express
  - MSK KRaft
  - MSK consumer lag cost
  - KafkaDataLogsDiskUsed
  - reduce MSK bill
  invocation_schema: 'Input: either (a) an MSK cluster ARN or identifier + live-account context, (b) a cluster configuration document (broker type, broker count, EBS volume size, partition count, retention hours, Kafka version, pricing model, CloudWatch metrics), OR (c) a fleet description for batch optimisation. Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block per cluster, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL}.'
  invocation_example: "# Minimal valid input (offline classification):\nCluster: events-prod-msk\nKafka Version: 3.5.1\nRegion: us-east-1\nBroker Type: kafka.m5.large (2 vCPU, 8 GB)\nBroker Count: 6\nEBS Volume: 1 TB gp3 per broker\nPartitions: 120 across 15 topics\nLog Retention: 168 hours (7 days)\nCompacted Topics: none\nPricing: On-Demand (no commit)\nCloudWatch metrics (last 30 days):\n  - BytesInPerSec per broker: avg=5, max=12\n  - KafkaDataLogsDiskUsed: avg=25%, max=35%\n  - MaxOffsetLag: avg=1,000 (low consumer lag)\nEmit the standard optimisation block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
---

# MSK Cost Optimizer

## What this skill does

Optimises Amazon MSK cost across seven dimensions: broker type right-
sizing, Graviton broker migration, broker count optimisation, EBS storage
optimisation, MSK Serverless vs provisioned fit, partition count impact,
and data retention optimisation. Emits a deterministic verdict per cluster
with estimated monthly savings and a one-dimension-per-window migration
plan.

## STRICT output contract

Every invocation MUST emit exactly one optimisation block per cluster
in this shape — no prose before, no commentary after:

```text
TARGET: <cluster-name or cluster-arn>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <broker-type, broker-count, EBS-volume, partitions,
            retention, pricing model, Kafka version, tier>
  Proposed: <per-dimension list of changes>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly (broker right-sizing): $<amount>
  Monthly (Graviton migration): $<amount>
  Monthly (broker count reduction): $<amount>
  Monthly (EBS storage): $<amount>
  Monthly (serverless fit): $<amount>
  Monthly (retention / compaction): $<amount>
  Monthly (partition right-sizing): $0  (operational, no direct cost)
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

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: OPPORTUNITY_FOUND` with `Annual total: $0`.**
   If all seven dimensions net zero savings, the verdict MUST be
   `ALREADY_OPTIMAL`. A cost-neutral operational improvement (e.g.,
   partition right-sizing) is surfaced in REASON, not as a dollar
   saving.

2. **NEVER show savings math that does not balance.** The sum of all
   `Monthly (...)` lines MUST equal the Monthly total, and
   `Monthly total × 12` MUST equal `Annual total`, rounded to 2 decimal
   places. Re-verify before emitting.

3. **NEVER recommend Graviton brokers (`kafka.m7g`) without confirming
   Kafka version 3.x or later.** Kafka 2.x does NOT support Graviton
   broker types. Recommending Graviton on a Kafka 2.x cluster without
   first planning the version upgrade will fail at cluster creation.

4. **NEVER recommend reducing MSK broker count below 3.** Kafka requires
   a minimum of 3 brokers for replication factor=3 and quorum-based
   fault tolerance. A 2-broker cluster cannot survive a single broker
   failure without data loss.

5. **NEVER recommend decreasing EBS volume size in-place.** MSK supports
   online EBS volume increases via `update-broker-storage`, but NOT
   decreases. EBS reduction requires blue/green cluster migration. Flag
   it for the next migration window, never as an immediate action.

6. **NEVER recommend MSK Serverless for a workload exceeding 50 MB/s
   sustained ingress without computing the full 30-day break-even
   cost.** Serverless per-partition-hour + per-GB data pricing exceeds
   provisioned broker cost at high sustained throughput.

7. **NEVER omit the `CONFIRM:` gate before any state-changing CLI
   command.** Every `create-cluster-v2`, `update-cluster-configuration`,
   `update-broker-storage`, `delete-cluster`, and `kafka-configs --alter`
   MUST be preceded by a CONFIRM line and operator approval.

8. **NEVER emit scratch or recompute text** ("WAIT", "let me redo",
   "corrected:") in the output block. Finalize all math before emitting
   the block.

## Quick start

- **Graviton brokers (kafka.m7g) on Kafka 3.x are ~20% cheaper than the
  equivalent kafka.m5 generation.** Same vCPU and memory, full Kafka 3.x
  support. A cluster on `kafka.m5.large` ($0.276/h) migrates to
  `kafka.m7g.large` ($0.22/h) for ~20% off. Requires Kafka 3.x or later;
  Kafka 2.x does not support Graviton brokers.

- **MSK Serverless vs provisioned break-even is ~50 MB/s of ingress
  throughput.** Below 50 MB/s sustained, Serverless per-partition-hour +
  per-GB data pricing is usually cheaper. Above 50 MB/s steady, provisioned
  brokers are cheaper. Workloads with bursty traffic that idles for hours
  are prime Serverless candidates regardless of peak throughput.

- **Minimum 3 brokers for HA; more brokers are only justified by
  throughput or partition count.** A 6-broker cluster doing 10 MB/s total
  ingress is over-provisioned — 3 brokers can handle it with headroom.
  Kafka partitions must be distributed across brokers; the partition-to-
  broker ratio (aim < 400 partitions per broker) is the constraint.

- **EBS storage is the second-largest MSK cost after broker compute.**
  Each broker has an attached EBS volume. KafkaDataLogsDiskUsed below 30%
  means the volume is over-allocated. Storage auto-scaling (MSK storage
  auto-expand) or a manual right-size eliminates wasted EBS cost.

- **Log retention is the primary EBS cost driver over time.** A 7-day
  retention on a high-throughput topic consumes 7x the disk of a 1-day
  retention. Compacted topics (retention by key, not time) can reduce
  storage 10x for changelog or event-sourcing workloads.

## Mindset

MSK cost structure differs from databases in three ways: the cost is
dominated by broker compute + EBS storage (not per-request), partition
count adds broker overhead (metadata, leader election, rebalancing), and
data retention directly drives storage cost over time. The levers are
broker generation, broker count, EBS volume size, retention policy, and
Serverless fit. Most MSK waste comes from (a) legacy kafka.m5 brokers
that should be Graviton, (b) over-provisioned broker count for low-
throughput workloads, (c) oversized EBS volumes, or (d) long retention
on high-throughput topics that don't need it.

## Quick reference — verdict thresholds

| Observation | Verdict | Dimension |
|---|---|---|
| Cluster on kafka.m5 (pre-Graviton), Kafka 3.x+ | **OPPORTUNITY_FOUND** | Graviton migration |
| BytesInPerSec per broker avg < 10 MB/s on kafka.m5.2xlarge+ | **OPPORTUNITY_FOUND** | Broker right-sizing |
| Broker count > 3, total ingress < 50 MB/s, partitions < 400/broker | **OPPORTUNITY_FOUND** | Broker count reduction |
| KafkaDataLogsDiskUsed avg < 30% on 1 TB+ EBS volumes | **OPPORTUNITY_FOUND** | EBS storage |
| Total ingress < 50 MB/s with idle periods, provisioned | **OPPORTUNITY_FOUND** | Serverless fit |
| Log retention > 168h on high-throughput, non-compacted topic | **OPPORTUNITY_FOUND** | Retention |
| Partition count > 1000 total with low throughput per partition | **OPPORTUNITY_FOUND** | Partition right-sizing |
| All seven dimensions at cost-optimal config | **ALREADY_OPTIMAL** | (continue monitoring) |

## Pre-flight: data gate (run before any optimisation decision)

MSK optimisation requires four data sources: Cost Explorer for billing
line items, cluster configuration (broker type, count, EBS, partitions,
retention), CloudWatch metrics for utilisation, and topic-level
configuration.

### Required data sources

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

### Data-quality short-circuits

| Condition | Effect on optimisation |
|---|---|
| Cost Explorer access denied | NEED_MORE_INFO for cost quantification; topology still analysable. |
| Observation window < 14 days | NEED_MORE_INFO: workload may reflect atypical load. Min 14 days; 30 preferred. |
| Cluster in `CREATING` / `UPDATING` / `MAINTENANCE` | Wait for `ACTIVE` before emitting a change recommendation. |
| MSK Serverless cluster (no broker type) | Skip broker right-size + count dimensions; analyse per-partition pricing. |
| Kafka version < 3.0 | Graviton brokers not available; note version upgrade prerequisite. |
| Multi-VPC or cross-region replication active | Each region's cluster bills independently; analyse separately. |

## Process — Optimisation logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

- **Graviton brokers require Kafka 3.x or later.** Kafka 2.x does not
  support Graviton (m7g/m6g) brokers. If the cluster is on Kafka 2.8 or
  earlier, the Graviton migration is gated on a Kafka version upgrade
  first. The upgrade itself is non-disruptive (rolling) but must be
  staged before the broker type change.

- **MSK broker count cannot be reduced without cluster recreation.**
  Kafka partition leadership is distributed across brokers; removing a
  broker requires reassigning its partitions first. MSK supports
  broker count changes via update-cluster but reducing below the
  original count requires creating a new cluster and migrating. Plan
  broker-count reduction as a blue/green migration, not an in-place
  change.

- **EBS storage can be increased online but not decreased.** MSK
  supports `update-broker-storage` to increase EBS volume size per
  broker (online, no downtime). Decreasing EBS size requires cluster
  recreation. If KafkaDataLogsDiskUsed < 30%, flag for the next
  blue/green migration rather than immediate reduction. Storage auto-
  scaling (MSK storage auto-expand) prevents over-allocation on new
  clusters.

- **MSK Serverless bills per partition-hour + per-GB data stored + per-
  PUT-hour.** There is no broker cost. A Serverless cluster with 10
  partitions, low throughput, and 5 GB data costs pennies per hour.
  The same workload on provisioned kafka.m5.large x 3 brokers costs
  $600+/month. The break-even is ~50 MB/s sustained ingress or ~1000
  partitions.

- **Partition count directly adds broker overhead.** Each partition has
  a leader, followers, and metadata that consumes broker CPU and memory.
  Kafka recommends < 4000 partitions per broker. Excessive partitions
  (e.g., 1000 partitions on a 3-broker cluster doing 1 MB/s) waste
  broker resources — the metadata overhead exceeds the data processing.
  Reducing partition count is an operational change (no direct cost)
  that can enable broker downsize.

- **Compacted topics reduce storage 10x for key-based workloads.** A
  compacted topic retains only the latest value per key, not all
  history. For changelog, event-sourcing, or state-store workloads,
  compaction can reduce disk usage from 500 GB to 50 GB, directly
  reducing EBS cost. Switch via topic-level `cleanup.policy=compact`.

- **MSK Express tier (2025+) provides high-throughput burstable brokers
  with credit-based performance.** Express brokers have a baseline
  throughput and burst credits for spikes. Cost is comparable to
  Standard provisioned but with better burst handling. Evaluate Express
  for workloads with variable throughput that don't justify more
  brokers full-time.

- **MSK with KRaft (2025+) eliminates ZooKeeper, reducing broker
  overhead.** KRaft mode uses an in-protocol consensus instead of
  separate ZooKeeper ensembles. This frees the broker CPU that was
  spent on ZooKeeper health checks and metadata sync, potentially
  enabling a broker downsize. KRaft is available on Kafka 3.5+ on MSK.

- **Log retention is the single biggest EBS cost driver.** A topic
  ingesting 10 MB/s with 7-day retention stores ~6 TB. With 1-day
  retention, it stores ~860 GB. The EBS cost difference at $0.08/GB-
  month is $400+/month for one topic. Always evaluate retention
  duration against the actual data-replay requirements.

### Step 1: Validate input and data sufficiency

If Cost Explorer access is unavailable AND the caller has not pasted
billing line items, emit NEED_MORE_INFO:

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

### Step 2: Cost Explorer reconciliation

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

| USAGE_TYPE | Dimension | What it represents |
|---|---|---|
| `MSK:BrokerUsage` | Compute (provisioned) | Per-broker-hour by type |
| `MSK:ServerlessUsage` | Compute (Serverless) | Per-partition-hour + per-GB data |
| `MSK:EBSUsage` | EBS storage | Per-GB-month of broker-attached volume |

If `MSK:BrokerUsage` dominates with kafka.m5 brokers, the Graviton
migration is the first lever. If `MSK:EBSUsage` is > 30% of total, the
retention/storage dimension has high leverage.

### Step 3: Cost classification

| Cost profile | Indicators | Emphasis |
|---|---|---|
| Pre-Graviton | kafka.m5 brokers, Kafka 3.x+ | Graviton migration (Step 5) |
| Over-provisioned brokers | BytesInPerSec/broker < 10 MB/s on large type | Broker right-sizing (Step 4) |
| Excess broker count | > 3 brokers, total ingress < 50 MB/s | Broker count (Step 7) |
| EBS over-allocated | KafkaDataLogsDiskUsed avg < 30% | EBS storage (Step 8) |
| Serverless candidate | Ingress < 50 MB/s, idle periods | Serverless fit (Step 6) |
| Retention-driven storage | EBSUsage high, retention > 168h | Retention (Step 9) |
| Partition-heavy | > 400 partitions/broker, low throughput | Partition right-sizing (Step 10) |
| Mixed (no single dimension dominant) | Even distribution | Apply all in parallel |

### Step 4: Broker type right-sizing

**Decision matrix:**

| Throughput profile (30-day) | Recommendation | Savings estimate |
|---|---|---|
| BytesInPerSec/broker avg < 5 MB/s on kafka.m5.2xlarge | Downsize to kafka.m5.large or kafka.m7g.large | ~50% of compute |
| BytesInPerSec/broker avg 5-20 MB/s | Keep current broker type | None |
| BytesInPerSec/broker avg > 30 MB/s frequently | Upsize or add brokers | None — already constrained |
| CpuUser + CpuSystem avg > 60% | CPU-bound; don't downsize | None |
| Consumer lag (MaxOffsetLag) growing | Throughput-bound; don't downsize | None |

**Worked example — broker right-sizing:**

Cluster with 3 brokers on `kafka.m5.2xlarge` ($0.552/h each in us-east-1).
BytesInPerSec/broker avg=4 MB/s, max=8 MB/s. CpuUser avg=15%.
Downsize to `kafka.m5.large` ($0.276/h):
- Current: 3 × $0.276 × 730h = $604/month (Note: m5.2xlarge is $0.552)
  3 × $0.552 × 730h = $1,209/month
- New: 3 × $0.276 × 730h = $604/month
- Monthly savings: $605
- Trade-off: less CPU headroom. Verify MaxOffsetLag doesn't grow and
  CpuUser stays < 50% after the downsize.

### Step 5: Graviton broker migration

This is the highest-leverage dimension when the cluster is on kafka.m5
and Kafka version is 3.x+.

| Current | Target | Savings | Notes |
|---|---|---|---|
| kafka.m5.large ($0.276/h) | kafka.m7g.large ($0.22/h) | ~20% | Same 2 vCPU / 8 GB |
| kafka.m5.2xlarge ($0.552/h) | kafka.m7g.2xlarge ($0.44/h) | ~20% | Same 8 vCPU / 32 GB |
| kafka.m5.4xlarge ($1.104/h) | kafka.m7g.4xlarge ($0.88/h) | ~20% | Same 16 vCPU / 64 GB |
| kafka.c5.large (legacy) | kafka.m7g.large | ~15% | c5 → m7g class change |

**Worked example — Graviton migration:**

Cluster with 3 brokers on `kafka.m5.large` ($0.276/h):
- Current: 3 × $0.276 × 730h = $604/month
- Migrate to kafka.m7g.large: 3 × $0.22 × 730h = $482/month
- Monthly savings: $122 (20%)
- Prerequisite: Kafka version must be 3.x or later. If on Kafka 2.8,
  upgrade first (rolling, non-disruptive), then migrate broker type.
- Migration: create a new MSK cluster on kafka.m7g, use MirrorMaker2
  or Cluster Linking to sync topics, cut over consumers/producers.

### Step 6: MSK Serverless vs provisioned fit evaluation

Serverless eliminates broker management and bills per partition-hour +
per-GB data + per-PUT-hour. The break-even calculation compares total
provisioned cost against projected Serverless pricing.

**Break-even logic:**

```
provisioned_monthly = broker_count × broker_hourly × 730 +
                      ebs_total_GB × $0.08

serverless_monthly  = (partition_count × $0.005 × 730) +
                      (data_stored_GB × $0.10) +
                      (put_requests_millions × $0.10)
```

A rough heuristic: if the provisioned cluster's total sustained ingress
is below ~50 MB/s, or if the cluster idles for extended periods,
Serverless is likely cheaper. Above 50 MB/s steady, provisioned with
Graviton brokers is cheaper.

| Provisioned profile | Recommendation | Rationale |
|---|---|---|
| Ingress < 50 MB/s, variable load | Migrate to Serverless | Pay only for partitions + data |
| Ingress < 50 MB/s, steady, few partitions | Evaluate Serverless | Break-even zone; compute 30-day cost |
| Ingress > 50 MB/s steady | Keep provisioned + Graviton | Provisioned cheaper at scale |
| > 1000 partitions | Keep provisioned | Serverless per-partition-hour adds up |
| Dev/test, idle nights/weekends | Migrate to Serverless | Near-zero cost when idle |

**Worked example — Serverless migration:**

A 3-broker `kafka.m5.large` cluster ($0.276/h each = $604/month
compute) + 1 TB EBS ($80/month) = $684/month total. Total ingress
avg=10 MB/s, 20 partitions, 5 GB data stored.
- Provisioned: $684/month (billed 24/7 regardless of load)
- Serverless: 20 partitions × $0.005 × 730h = $73 data + 5 GB × $0.10 =
  $0.50 + PUT requests ~$5 = $78.50/month
- Monthly savings: ~$606 (88%)
- Trade-off: Serverless has a partition-per-cluster limit and a slight
  per-request latency overhead. Verify consumer throughput requirements.

### Step 7: Broker count optimisation

| Observation | Recommendation | Savings |
|---|---|---|
| Broker count=6, total ingress < 50 MB/s, partitions < 120 | Reduce to 3 brokers (blue/green migration) | ~50% of compute |
| Broker count=3, ingress > 50 MB/s, consumer lag growing | Add brokers (scale out) | None — capacity-bound |
| Broker count=3 (minimum for HA) | Keep; cannot reduce below 3 | None |
| Broker count > 3 with replication factor=3 | Evaluate reducing to 3 if throughput allows | Per excess broker |

**Worked example — broker count reduction:**

Cluster with 6 brokers on `kafka.m5.large` ($0.276/h each). Total
ingress avg=15 MB/s (2.5 MB/s per broker). Partitions: 60 total (10
per broker, well under the 400/broker ceiling).
- Current: 6 × $0.276 × 730h = $1,209/month
- Reduce to 3 brokers: 3 × $0.276 × 730h = $604/month
- Monthly savings: $605
- Migration: create a 3-broker MSK cluster, use MirrorMaker2 or Cluster
  Linking to replicate topics, cut over producers/consumers, decommission
  the 6-broker cluster.
- Trade-off: 3 brokers is the minimum for Kafka replication factor=3.
  Confirm the reduced partition-per-broker ratio (20/broker) is within
  the < 400 guideline.

### Step 8: EBS storage optimisation

| Observation | Recommendation | Savings |
|---|---|---|
| KafkaDataLogsDiskUsed avg < 30% on 1 TB+ volumes | Reduce volume on next blue/green | Per-GB-month saved |
| KafkaDataLogsDiskUsed growing > 10%/month | Enable MSK storage auto-expand | Prevents volume exhaustion |
| Fixed volume with predictable growth | Evaluate auto-expand vs manual right-size | Operational savings |
| Volume per broker > 2x the data need | Right-size to 1.3x actual usage | ~35% of EBS cost |

**Worked example — EBS right-sizing:**

Cluster with 3 brokers, each with 1 TB gp3 EBS ($0.08/GB-month =
$80/broker/month = $240/month total). KafkaDataLogsDiskUsed avg=25%
(250 GB used per broker).
- Current: 3 × 1,000 GB × $0.08 = $240/month
- Right-size to 500 GB on next blue/green migration:
  3 × 500 GB × $0.08 = $120/month
- Monthly savings: $120
- Note: EBS volume cannot be decreased in-place. Schedule for the next
  blue/green migration alongside broker type or count changes. Enable
  MSK storage auto-expand on the new cluster to auto-scale if data grows.

### Step 9: Data retention and compaction optimisation

| Observation | Recommendation | Savings |
|---|---|---|
| Retention > 168h on high-throughput non-compacted topic | Reduce to 24-72h if replay not needed | Up to 7x storage |
| Compaction candidate (changelog, event-sourcing) with time retention | Switch to cleanup.policy=compact | 10x storage reduction |
| Mixed retention policy, some topics overly long | Audit topic-level configs; standardise | Variable |
| Retention = -1 (infinite) on any topic | Set finite retention immediately | Prevents unbounded growth |

**Worked example — retention optimisation:**

Topic ingesting 10 MB/s with 7-day retention (168h). Stores ~6 TB
across the cluster. Data-replay requirement is only 24 hours.
- Current storage: ~6 TB → EBS cost contribution ~$480/month
- Reduce to 24h retention: stores ~860 GB → EBS cost ~$69/month
- Monthly savings: ~$411
- Change: `kafka-configs --alter --topic <topic> \
  --add-config retention.ms=86400000`
- Trade-off: consumers can only replay the last 24h. Verify no batch
  consumer depends on the full 7-day window.

### Step 10: Partition count right-sizing

| Observation | Recommendation | Savings |
|---|---|---|
| > 400 partitions/broker with low throughput/partition | Consolidate partitions (operational) | Enables broker downsize |
| 1000 partitions for a 1 MB/s workload | Reduce to 12-24 partitions | Frees broker CPU |
| Uneven partition distribution | Reassign partitions (kafka-reassign-partitions) | Performance, not cost |
| Consumer group reading from few partitions | Reduce partition count to match consumer parallelism | Enables downsize |

Partition right-sizing has no direct cost savings, but reducing
excessive partitions frees broker CPU and memory, which can then enable
a broker type downsize. This is a force-multiplier for Step 4.

### Step 11: Final verdict

The verdict is the worst-case (most-actionable) finding across all
seven dimensions:

- If ANY dimension has a concrete recommendation with quantified
  savings, verdict is **OPPORTUNITY_FOUND**.
- If a change was applied and verified this session, verdict is
  **OPTIMIZED**.
- If all dimensions are at cost-optimal config AND broker count,
  retention, and Serverless fit have been evaluated, verdict is
  **ALREADY_OPTIMAL**.

## Output format

### Worked example — multi-dimension opportunity

```text
TARGET: events-prod-msk
VERDICT: OPPORTUNITY_FOUND
REASON: Cluster runs kafka.m5.large (pre-Graviton) with 6 brokers,
  1 TB EBS per broker at 25% disk used, 168h retention on a
  high-throughput topic that only needs 24h, total ingress 15 MB/s
  (well under the 50 MB/s Serverless break-even candidate range),
  and Kafka 3.5.1 (Graviton-ready). Five dimensions have actionable
  opportunities.
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

### Worked example — already optimal

```text
TARGET: analytics-msk-prod
VERDICT: ALREADY_OPTIMAL
REASON: All seven dimensions verified at cost-optimal config:
  kafka.m7g.large brokers (Graviton, Kafka 3.5.1 with KRaft),
  3 brokers (minimum HA), BytesInPerSec/broker avg 18 MB/s (healthy
  utilisation), KafkaDataLogsDiskUsed avg 55%, compacted topics for
  changelog workloads, 72h retention on event topics, partition count
  90 total (30/broker).
RECOMMENDATION:
  Current: All dimensions optimal
  Proposed: no change
  Confidence: HIGH — CE confirms 30-day spending stable; CloudWatch
    confirms healthy throughput and disk utilisation.
ESTIMATED_SAVINGS:
  Monthly (all dimensions): $0
  Annual total: $0
MIGRATION_STEPS:
  - None required. Continue monthly CE review.
  - Re-evaluate if total ingress exceeds 50 MB/s sustained — may need
    to add a 4th broker or evaluate MSK Express tier for burst.
```

## Anti-Patterns — NEVER do these things

- **NEVER recommend reducing MSK broker count below 3.** Kafka requires
  a minimum of 3 brokers for replication factor=3 and quorum-based
  fault tolerance. A 2-broker cluster cannot survive a single broker
  failure without data loss. Always retain at least 3 brokers for HA.

- **NEVER recommend Graviton brokers without confirming Kafka version
  3.x+.** Kafka 2.x does not support Graviton (m7g/m6g) broker types.
  Recommending Graviton on a Kafka 2.x cluster without first planning
  the version upgrade will fail at cluster creation.

- **NEVER recommend decreasing EBS volume size in-place.** MSK supports
  online EBS volume increases via update-broker-storage, but NOT
  decreases. Decreasing EBS requires cluster recreation via blue/green
  migration. Always flag EBS reduction for the next migration, not as
  an immediate action.

- **NEVER recommend MSK Serverless for a workload exceeding 50 MB/s
  sustained ingress without computing the full break-even.** Serverless
  per-partition-hour + per-GB data pricing exceeds provisioned broker
  cost at high sustained throughput. Always compute the 30-day projected
  Serverless cost and compare against provisioned + Graviton cost.

- **NEVER recommend reducing log retention without confirming the
  data-replay requirement.** Consumers may depend on historical data
  for batch processing, backfill, or audit. Always confirm the required
  replay window before shortening retention. For audit requirements,
  consider exporting to S3 before reducing Kafka-side retention.

- NEVER recommend switching a topic to cleanup.policy=compact without
  confirming the topic is key-based. Compaction on a topic with null
  keys or append-only events will delete data unpredictably.
- NEVER recommend adding partitions to solve a throughput problem
  without checking the consumer parallelism first. More partitions add
  broker overhead; if consumers can't parallelise, the partitions are
  wasted cost.
- NEVER batch a blue/green migration's cut-over and decommission in
  one step. Always cut over, verify for 7 days, then decommission the
  old cluster.
- NEVER purchase a 3-year commitment on a cluster with active migration
  plans. The commitment outlasts the cluster. Match commit term to
  expected cluster lifetime.
- NEVER recommend MSK Express tier for a steady-state workload. Express
  burst credits deplete under sustained load; Express is for variable-
  throughput workloads that burst occasionally.

## Quick navigation

| You want to... | Jump to |
|---|---|
| Evaluate Graviton migration (m5 -> m7g) | Step 5 — Graviton migration |
| Right-size broker type | Step 4 — Broker right-sizing |
| Reduce broker count (6 -> 3) | Step 7 — Broker count optimisation |
| Evaluate MSK Serverless vs provisioned | Step 6 — Serverless fit |
| Optimise EBS storage | Step 8 — EBS storage optimisation |
| Reduce log retention / enable compaction | Step 9 — Retention and compaction |
| Reduce excessive partitions | Step 10 — Partition right-sizing |
| Handle missing data | Step 1 — Validate input |
| Look up pricing / broker types | references/msk-pricing-reference.md |

## Expert heuristic — the 60-second triage

When handed an MSK bill and asked "why is this so high?", run this
60-second triage before deep-diving any single dimension:

1. **Pull CE MSK USAGE_TYPE breakdown.** If brokers are on kafka.m5
   generation, the Graviton migration (Step 5) is the first lever —
   flat ~20% cut (requires Kafka 3.x+).
2. **Pull broker count + total ingress.** Broker count > 3 with total
   ingress < 50 MB/s = broker-count reduction opportunity (Step 7).
3. **Pull KafkaDataLogsDiskUsed.** Disk used < 30% on 1 TB+ volumes =
   EBS over-allocation (Step 8). Enable auto-expand on new clusters.
4. **Pull retention per topic.** Retention > 168h on high-throughput
   non-compacted topics = retention-driven storage waste (Step 9).
5. **Pull partition count.** > 400 partitions/broker with low throughput
   = excessive partitions enabling broker downsize (Step 10).
6. **Pull Serverless vs provisioned split.** Provisioned clusters with
   ingress < 50 MB/s and idle periods = Serverless candidate (Step 6).

If any of the six checks hits, deep-dive the corresponding step. If all
six pass, the cluster is likely ALREADY_OPTIMAL — verify with the full
ordered process.

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

## Verdict semantics

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension has a savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; CE line items confirm the new pattern. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All seven dimensions at cost-optimal config AND broker count, retention, and Serverless fit evaluated. | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed: CE access denied, CloudWatch window < 14 days, Kafka version unknown. | Pre-decision — emit per-dimension; other dimensions can still emit OPPORTUNITY_FOUND. |

## Recent AWS features (2024-2026)

- **MSK Cluster Tier — Express (2025+):** High-throughput burstable
  broker tier with credit-based performance. Express brokers have a
  baseline throughput and burst credits for spikes. Evaluate for
  variable-throughput workloads that don't justify additional brokers
  full-time.
- **MSK with KRaft (2025+):** Eliminates ZooKeeper, using an in-protocol
  consensus (KRaft). Reduces broker overhead spent on ZooKeeper health
  checks and metadata sync, potentially enabling a broker downsize.
  Available on Kafka 3.5+ on MSK.
- **Graviton brokers — kafka.m7g (2024-2025):** ARM-based brokers ~20%
  cheaper than kafka.m5. Requires Kafka 3.x or later. Full Kafka feature
  parity including KRaft mode.
- **MSK Serverless (2022-2024 enhancements):** Auto-scaling partitions,
  no broker management. Per-partition-hour + per-GB data + per-PUT-hour
  pricing. Break-even against provisioned at ~50 MB/s sustained ingress.
- **MSK Cluster Linking (2024-2025):** Cross-cluster topic replication
  with offset preservation. Enables blue/green migrations for broker
  type and count changes without MirrorMaker2 overhead.
- **MSK storage auto-expand (2024):** Automatic EBS volume expansion
  when KafkaDataLogsDiskUsed exceeds threshold. Prevents volume
  exhaustion and enables starting with smaller volumes (right-sized
  from day one).

## AWS documentation

Domain: AWS CloudOps / Analytics — Amazon MSK cost optimisation.

- **Amazon MSK pricing** — https://aws.amazon.com/msk/pricing/
- **MSK Serverless** — https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html
- **MSK broker types** — https://docs.aws.amazon.com/msk/latest/developerguide/msk-create-cluster.html
- **MSK Cluster Tier (Express)** — https://docs.aws.amazon.com/msk/latest/developerguide/supported-broker-types.html
- **MSK with KRaft** — https://docs.aws.amazon.com/msk/latest/developerguide/kraft.html
- **MSK storage** — https://docs.aws.amazon.com/msk/latest/developerguide/msk-storage.html
- **MSK Cluster Linking** — https://docs.aws.amazon.com/msk/latest/developerguide/msk-cluster-linking.html
- **AWS Cost Explorer** — https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
- **Well-Architected — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
