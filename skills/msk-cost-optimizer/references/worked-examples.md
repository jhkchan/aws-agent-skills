# Worked Examples — MSK Cost Optimizer

## Worked example — broker right-sizing

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

## Worked example — Graviton migration

**Worked example — Graviton migration:**

Cluster with 3 brokers on `kafka.m5.large` ($0.276/h):
- Current: 3 × $0.276 × 730h = $604/month
- Migrate to kafka.m7g.large: 3 × $0.22 × 730h = $482/month
- Monthly savings: $122 (20%)
- Prerequisite: Kafka version must be 3.x or later. If on Kafka 2.8,
  upgrade first (rolling, non-disruptive), then migrate broker type.
- Migration: create a new MSK cluster on kafka.m7g, use MirrorMaker2
  or Cluster Linking to sync topics, cut over consumers/producers.

## Serverless break-even math

```
provisioned_monthly = broker_count × broker_hourly × 730 +
                      ebs_total_GB × $0.08

serverless_monthly  = (partition_count × $0.005 × 730) +
                      (data_stored_GB × $0.10) +
                      (put_requests_millions × $0.10)
```

## Worked example — Serverless migration

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

## Worked example — broker count reduction

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

## Worked example — EBS right-sizing

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

## Worked example — retention optimisation

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

## Worked example — already optimal

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

