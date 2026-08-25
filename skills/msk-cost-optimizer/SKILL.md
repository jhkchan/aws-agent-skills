---
name: msk-cost-optimizer
description: Optimises Amazon MSK cost across seven dimensions — broker type right-sizing (CloudWatch BytesInPerSec, KafkaDataLogsDiskUsed, consumer lag MaxOffsetLag), broker count optimisation (minimum 3 for HA, reduce excess on low-throughput clusters), EBS storage optimisation (storage-auto-scaling vs fixed gp3, right-size to retention needs), MSK Serverless vs provisioned (break-even ~50 MB/s ingress), partition count impact (excessive partitions add broker overhead), data retention optimisation (log retention hours, compacted topics for changelog workloads), and Graviton broker migration (Kafka 3.x, kafka.m7g ~20% cheaper). Covers MSK Cluster Tier (Express) and MSK with KRaft. Emits OPTIMIZED, OPPORTUNITY_FOUND, or ALREADY_OPTIMAL per cluster with estimated monthly savings.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted cluster configuration, CloudWatch summaries, and billing line items. Live-account optimisation uses aws kafka describe-cluster, describe-cluster-v2, list-clusters-v2, aws kafka describe-configuration, aws cloudwatch get-metric-statistics for AWS/Kafka BytesInPerSec, BytesOutPerSec, KafkaDataLogsDiskUsed, ConsumerLagMetrics MaxOffsetLag, CpuUser, CpuSystem, aws ce...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | OPPORTUNITY_FOUND | ALREADY_OPTIMAL
  when_to_use: Reviewing Amazon MSK cluster spend, right-sizing Kafka broker types, evaluating Graviton brokers (kafka.m7g vs kafka.m5), deciding between MSK Serverless and provisioned (break-even ~50 MB/s), optimising broker count (minimum 3 for HA, reduce excess), auditing EBS storage allocation vs actual disk usage, tuning log retention hours or compacted topics for storage savings, or evaluating MSK Cluster Tier (Express) and MSK with KRaft for cost.
  when_not_to_use: Self-managed Kafka on EC2 cost optimisation (this skill covers the managed MSK service only), Kafka Connect or MSK Connect cost optimisation (use kafka-connect-troubleshooter or a Connect specialist), Kinesis Data Streams cost optimisation (different service), Kafka performance tuning or partition rebalancing as the primary goal (use a Kafka operations workflow; this skill uses metrics only to identify cost waste), or MSK security or TLS configuration (use a security audit workflow).
  activation_triggers: optimise MSK cost, right-size MSK broker, MSK Graviton migration, kafka.m7g vs kafka.m5, MSK Serverless vs provisioned, MSK broker count, MSK EBS storage optimisation, MSK log retention, MSK compacted topics, MSK partition count, MSK Cluster Tier Express, MSK KRaft, MSK consumer lag cost, KafkaDataLogsDiskUsed, reduce MSK bill
  invocation_schema: 'Input: either (a) an MSK cluster ARN or identifier + live-account context, (b) a cluster configuration document (broker type, broker count, EBS volume size, partition count, retention hours, Kafka version, pricing model, CloudWatch metrics), OR (c) a fleet description for batch optimisation. Output: a deterministic TARGET / VERDICT / REASON / RECOMMENDATION / ESTIMATED_SAVINGS / MIGRATION_STEPS block per cluster, where VERDICT ∈ {OPTIMIZED, OPPORTUNITY_FOUND, ALREADY_OPTIMAL}.'
  invocation_example: "# Minimal valid input (offline classification):\nCluster: events-prod-msk\nKafka Version: 3.5.1\nRegion: us-east-1\nBroker Type: kafka.m5.large (2 vCPU, 8 GB)\nBroker Count: 6\nEBS Volume: 1 TB gp3 per broker\nPartitions: 120 across 15 topics\nLog Retention: 168 hours (7 days)\nCompacted Topics: none\nPricing: On-Demand (no commit)\nCloudWatch metrics (last 30 days):\n  - BytesInPerSec per broker: avg=5, max=12\n  - KafkaDataLogsDiskUsed: avg=25%, max=35%\n  - MaxOffsetLag: avg=1,000 (low consumer lag)\nEmit the standard optimisation block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Amazon MSK, Amazon Managed Streaming for Apache Kafka, MSK Serverless, MSK Express, MSK Cluster Tier, MSK KRaft, Graviton brokers, kafka.m7g, broker right-sizing, EBS storage optimisation, log retention, compacted topics, partition count, consumer lag, KafkaDataLogsDiskUsed, data retention, FinOps, streaming cost
  tags: msk, kafka, analytics, cost-optimization, finops, right-sizing, serverless
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

Core quick-start heuristics (Graviton ~20% cheaper on Kafka 3.x, Serverless break-even ~50 MB/s, minimum 3 brokers, EBS and retention cost drivers): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
The decision tables in Steps 4-10 below encode the same thresholds.

## Mindset

Cost-structure fundamentals (how MSK cost differs from databases): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
The verdict thresholds below assume them.

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

The four data-gathering command blocks (Cost Explorer breakdown, cluster configuration, CloudWatch metrics, topic configuration): moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Run them before any optimisation decision, then apply the data-quality short-circuits below.

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

Non-obvious behaviours that change the recommendation (Graviton/Kafka-version coupling, broker-count immutability, EBS one-way scaling, Serverless billing model, partition overhead, compaction, Express tier, KRaft, retention): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load before emitting any recommendation; Steps 1-11 assume these constraints.

### Step 1: Validate input and data sufficiency

If Cost Explorer access is unavailable AND the caller has not pasted
billing line items, emit NEED_MORE_INFO:

Fallback data-gathering commands when Cost Explorer is unavailable: moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
If neither CE access nor pasted data exists, emit NEED_MORE_INFO.

### Step 2: Cost Explorer reconciliation

Cost Explorer reconciliation command block: moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
The USAGE_TYPE classification table stays below.

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

Worked example (m5.2xlarge right-sizing math): moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Apply the decision matrix above to reproduce it.

### Step 5: Graviton broker migration

This is the highest-leverage dimension when the cluster is on kafka.m5
and Kafka version is 3.x+.

| Current | Target | Savings | Notes |
|---|---|---|---|
| kafka.m5.large ($0.276/h) | kafka.m7g.large ($0.22/h) | ~20% | Same 2 vCPU / 8 GB |
| kafka.m5.2xlarge ($0.552/h) | kafka.m7g.2xlarge ($0.44/h) | ~20% | Same 8 vCPU / 32 GB |
| kafka.m5.4xlarge ($1.104/h) | kafka.m7g.4xlarge ($0.88/h) | ~20% | Same 16 vCPU / 64 GB |
| kafka.c5.large (legacy) | kafka.m7g.large | ~15% | c5 → m7g class change |

Worked example (Graviton migration savings math): moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Apply the migration matrix above to reproduce it.

### Step 6: MSK Serverless vs provisioned fit evaluation

Serverless eliminates broker management and bills per partition-hour +
per-GB data + per-PUT-hour. The break-even calculation compares total
provisioned cost against projected Serverless pricing.

**Break-even logic:**

Serverless break-even calculation block: moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Break-even heuristic: below ~50 MB/s sustained ingress Serverless is usually cheaper.

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

Worked example (Serverless vs provisioned math): moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Apply the fit table above to reproduce it.

### Step 7: Broker count optimisation

| Observation | Recommendation | Savings |
|---|---|---|
| Broker count=6, total ingress < 50 MB/s, partitions < 120 | Reduce to 3 brokers (blue/green migration) | ~50% of compute |
| Broker count=3, ingress > 50 MB/s, consumer lag growing | Add brokers (scale out) | None — capacity-bound |
| Broker count=3 (minimum for HA) | Keep; cannot reduce below 3 | None |
| Broker count > 3 with replication factor=3 | Evaluate reducing to 3 if throughput allows | Per excess broker |

Worked example (6-to-3 broker reduction math): moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Apply the observation table above to reproduce it.

### Step 8: EBS storage optimisation

| Observation | Recommendation | Savings |
|---|---|---|
| KafkaDataLogsDiskUsed avg < 30% on 1 TB+ volumes | Reduce volume on next blue/green | Per-GB-month saved |
| KafkaDataLogsDiskUsed growing > 10%/month | Enable MSK storage auto-expand | Prevents volume exhaustion |
| Fixed volume with predictable growth | Evaluate auto-expand vs manual right-size | Operational savings |
| Volume per broker > 2x the data need | Right-size to 1.3x actual usage | ~35% of EBS cost |

Worked example (EBS volume right-sizing math): moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Apply the observation table above to reproduce it.

### Step 9: Data retention and compaction optimisation

| Observation | Recommendation | Savings |
|---|---|---|
| Retention > 168h on high-throughput non-compacted topic | Reduce to 24-72h if replay not needed | Up to 7x storage |
| Compaction candidate (changelog, event-sourcing) with time retention | Switch to cleanup.policy=compact | 10x storage reduction |
| Mixed retention policy, some topics overly long | Audit topic-level configs; standardise | Variable |
| Retention = -1 (infinite) on any topic | Set finite retention immediately | Prevents unbounded growth |

Worked example (retention and compaction math): moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Apply the observation table above to reproduce it.

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

Full worked example for an ALREADY_OPTIMAL verdict: moved verbatim to [references/worked-examples.md](references/worked-examples.md).
The multi-dimension example above is the primary contract demonstration.

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

The 60-second triage (six checks to run when handed an MSK bill): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
If any check hits, deep-dive the corresponding Process step.

## Pre-flight safety checks (run before any remediation CLI)

Pre-flight safety checks (confirmation gate, state recording, one-dimension-per-window, post-change verification, blue/green migration, 3-cluster batch limit): moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
NEVER omit the CONFIRM gate — see FORBIDDEN output patterns above.

## Verdict semantics

| Verdict | When to emit | Position in workflow |
|---|---|---|
| `OPPORTUNITY_FOUND` | At least one dimension has a savings-bearing recommendation. | Primary — terminal for actionable findings. |
| `OPTIMIZED` | A change was applied and verified this session; CE line items confirm the new pattern. | Primary — only emitted post-remediation. |
| `ALREADY_OPTIMAL` | All seven dimensions at cost-optimal config AND broker count, retention, and Serverless fit evaluated. | Primary — terminal for healthy findings. |
| `NEED_MORE_INFO` | Data gate failed: CE access denied, CloudWatch window < 14 days, Kafka version unknown. | Pre-decision — emit per-dimension; other dimensions can still emit OPPORTUNITY_FOUND. |

## Recent AWS features (2024-2026)

Recent AWS features (2024-2026): moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Check before recommending Express tier, KRaft, or the newest broker types.

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

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Step 0 non-obvious behaviours, quick-start heuristics, cost-structure fundamentals, 60-second triage, recent AWS features (2024-2026).
- [references/diagnostic-commands.md](references/diagnostic-commands.md) — Required data-source commands, Step 1/Step 2 command blocks, pre-flight safety checks.
- [references/worked-examples.md](references/worked-examples.md) — Secondary worked examples (right-sizing, Graviton, Serverless break-even, broker count, EBS, retention, already-optimal).
- [references/msk-pricing-reference.md](references/msk-pricing-reference.md) — Broker-type pricing, Graviton savings matrix, Serverless pricing, EBS and retention cost projections.


