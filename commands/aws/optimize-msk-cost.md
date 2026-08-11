---
description: Optimises Amazon MSK cost through broker type right-sizing (CloudWatch BytesInPerSec, KafkaDataLogsDiskUsed, consumer lag via MaxOffsetLag, CpuUser), broker count optimisation (minimum 3 for HA, reduce excess on low-throughput clusters), EBS storage optimisation (right-size per-broker volume to actual disk usage, storage-auto-scaling), MSK Serverless vs provisioned evaluation (break-even ~50 MB/s ingress), partition count impact (excessive partitions add broker overhead), data retention optimisation (log retention hours, compacted topics), and Graviton broker migration (Kafka 3.x, kafka.m7g ~20% cheaper than kafka.m5). Covers latest MSK Cluster Tier (Express) and MSK with KRaft. Emits a deterministic VERDICT, recommendation, and estimated monthly savings per cluster.
nl_triggers:
  - "optimise MSK cost"
  - "right-size MSK broker"
  - "MSK Graviton migration"
  - "kafka.m7g vs kafka.m5"
  - "MSK Serverless vs provisioned"
  - "MSK broker count"
  - "MSK EBS storage optimisation"
  - "MSK log retention"
  - "MSK compacted topics"
  - "MSK partition count"
  - "MSK Cluster Tier Express"
  - "MSK KRaft"
  - "MSK consumer lag cost"
  - "KafkaDataLogsDiskUsed"
  - "reduce MSK bill"
routes_to: msk-cost-optimizer
---

# /aws:optimize-msk-cost

Activate the `msk-cost-optimizer` skill and right-size Amazon MSK
clusters for cost optimisation using the seven-dimension analysis
framework.

## What it does

Reads a cluster's configuration (broker type, broker count, EBS volume
size, partition count, retention, Kafka version, pricing model) plus
14-30 day CloudWatch metrics (BytesInPerSec, BytesOutPerSec,
KafkaDataLogsDiskUsed, CpuUser, MaxOffsetLag), then applies the ordered
optimisation logic:

1. **Pre-flight** — data sufficiency gate. If CloudWatch data is
   insufficient or observation window < 14 days, emit NEED_MORE_INFO.
2. **Cost Explorer reconciliation** — MSK:BrokerUsage + MSK:EBSUsage +
   MSK:ServerlessUsage breakdown to identify the dominant cost driver.
3. **Graviton migration** — kafka.m5 (pre-Graviton) with Kafka 3.x+ ->
   kafka.m7g for ~20% flat cost reduction. Requires Kafka 3.x or later;
   flag version upgrade prerequisite if on Kafka 2.x.
4. **Broker type right-sizing** — BytesInPerSec/broker < 10 MB/s +
   CpuUser < 40% -> downsize one step. Check MaxOffsetLag is not growing
   (throughput-bound clusters should not downsize).
5. **Broker count optimisation** — broker count > 3 with total ingress <
   50 MB/s and partition-to-broker ratio < 400 -> reduce to 3 brokers
   (blue/green migration). Minimum 3 brokers for HA.
6. **MSK Serverless fit** — total ingress < 50 MB/s with idle periods ->
   evaluate Serverless per-partition-hour vs provisioned broker-hour
   break-even. Steady > 50 MB/s -> keep provisioned + Graviton.
7. **EBS storage optimisation** — KafkaDataLogsDiskUsed < 30% on 1 TB+
   volumes -> reduce volume on next blue/green. EBS can be increased
   online but NOT decreased. Enable MSK storage auto-expand on new
   clusters.
8. **Data retention / compaction** — retention > 168h on high-throughput
   non-compacted topic -> reduce to 24-72h if replay not needed.
   Compaction candidate (changelog, event-sourcing) -> switch to
   cleanup.policy=compact for 10x storage reduction.
9. **Partition right-sizing** — > 400 partitions/broker with low
   throughput -> consolidate partitions (operational, enables broker
   downsize).
10. **Verdict** — OPPORTUNITY_FOUND (any dimension has a recommendation),
    OPTIMIZED (applied and verified), or ALREADY_OPTIMAL (no change
    needed).

Emits a deterministic optimisation block per cluster:

```text
TARGET: <cluster-name>
VERDICT: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <broker-type> <broker-count> <ebs-volume> <retention> at <pricing-model>
  Proposed: <broker-type> <broker-count> <ebs-volume> <retention> at <pricing-model>
  Dimensions: <list of applicable dimensions>
  Confidence: <HIGH/MEDIUM/LOW> — <rationale>
ESTIMATED_SAVINGS:
  Monthly (broker right-sizing): $<amount>
  Monthly (Graviton migration): $<amount>
  Monthly (broker count): $<amount>
  Monthly (EBS storage): $<amount>
  Monthly (retention / compaction): $<amount>
  Annual total: $<amount>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a cluster configuration and ask any of:

- "right-size this MSK cluster"
- "should I migrate to Graviton brokers?"
- "do I need 6 brokers or can I use 3?"
- "is MSK Serverless cheaper for this Kafka workload?"
- "is my EBS volume too large?"
- "should I reduce log retention?"
- "can I compact this Kafka topic?"

A bare cluster name + any optimise verb ("optimise this MSK cluster",
"reduce MSK cost") also routes here via the orchestrator.

## Inputs

- Cluster metadata: cluster name/ARN, broker type, broker count, EBS
  volume size per broker, partition count, retention, Kafka version,
  pricing model, MSK tier (Standard/Express/Serverless).
- CloudWatch metrics (last 14-30 days):
  - `BytesInPerSec` per broker (throughput assessment)
  - `BytesOutPerSec` per broker (consumer throughput)
  - `KafkaDataLogsDiskUsed` (disk utilisation for EBS right-size)
  - `CpuUser` + `CpuSystem` (CPU headroom for broker downsize)
  - `MaxOffsetLag` (consumer lag — growing lag means throughput-bound)
- Cost Explorer (optional but HIGH confidence requires it):
  - MSK:BrokerUsage + MSK:EBSUsage breakdown
- Workload context: production vs dev/test, steady vs variable, data-
  replay retention requirement.

## Outputs

- One optimisation block per cluster.
- Confidence level with rationale (HIGH requires CloudWatch data + CE
  breakdown + clear thresholds).
- Estimated monthly and annual savings, broken down by dimension
  (Graviton, broker right-size, broker count, EBS, retention, Serverless).
- Specific migration steps with CLI commands (create-cluster-v2 for
  blue/green migration, kafka-configs for retention changes, update-
  broker-storage for EBS increases).
- Blue/green migration plan with MirrorMaker2 or MSK Cluster Linking
  for broker count and type changes.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for MSK cost).
- `/aws:optimize-elasticache-cost` for the caching cost-optimisation
  sibling — MSK and ElastiCache are both commonly over-provisioned
  data services.
- `/aws:audit-msk-cluster` for the security and configuration audit of
  an MSK cluster (complements this cost-focused optimisation).
