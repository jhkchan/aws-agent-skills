---
name: dynamodb-capacity-optimizer
description: 'Optimises DynamoDB table cost across seven dimensions: on-demand vs provisioned capacity mode crossover analysis (30% utilization break-even), RCU/WCU sizing from CloudWatch ConsumedReadCapacityUnits and ConsumedWriteCapacityUnits, auto-scaling target utilization tuning (70% default vs 50-60% for headroom), partition key design for even distribution (hot partition detection via CloudWatch), GSI projection size optimization (sparse index strategy), table class selection (Standard vs Standard-Infrequent Access for low-traffic tables), and TTL for data lifecycle cost reduction. DynamoDB Streams cost impact evaluated. Emits FURTHER_OPTIMIZATION_AVAILABLE with capacity mode recommendation and dollar savings, OPTIMIZED, or ALREADY_OPTIMAL.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline classification works from pasted CloudWatch metrics and table configuration. Live-account optimization uses aws dynamodb describe-table, aws dynamodb describe-continuous-backups, aws application-autoscaling describe-scaling-policies, aws cloudwatch get-metric-statistics (ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits, ThrottledRequests, SystemErrors), aws ce get-cost-and-usage, and aws dynamodb...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Databases
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising DynamoDB table cost, evaluating on-demand vs provisioned capacity mode, sizing RCU/WCU from CloudWatch consumed capacity metrics, tuning auto-scaling target utilization, diagnosing hot partitions via partition skew, optimising GSI projection size, selecting table class (Standard vs Standard-IA), deploying TTL for data lifecycle, or running a database FinOps review.
  when_not_to_use: DynamoDB table security or IAM auditing (use dynamodb-table-auditor), DynamoDB troubleshooting (throttling diagnosis without cost context — use the DynamoDB troubleshooter), or DynamoDB schema design from scratch (use a data modeling specialist). This skill focuses on cost-driven capacity optimization for existing tables, not greenfield schema design.
  activation_triggers: optimise DynamoDB cost, DynamoDB on-demand vs provisioned, DynamoDB RCU WCU sizing, DynamoDB auto-scaling target, DynamoDB hot partition, DynamoDB partition skew, DynamoDB GSI cost, DynamoDB sparse index, DynamoDB table class, DynamoDB Standard-Infrequent Access, DynamoDB TTL cost, DynamoDB Streams cost, DynamoDB adaptive capacity, DynamoDB FinOps review, reduce DynamoDB bill, DynamoDB capacity review
  invocation_schema: 'Input: either (a) a table identifier + live-account context, (b) a CloudWatch consumed-capacity metrics export with table configuration, OR (c) table metadata (BillingMode, ProvisionedThroughput, GSIs, AutoScaling policies, TTL status). Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_SAVINGS/MIGRATION_STEPS block per table, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE, ALREADY_OPTIMAL.'
  invocation_example: "# Minimal valid input (offline classification):\nTableName: user-events-prod\nRegion: us-east-1\nBillingMode: PROVISIONED\nProvisionedThroughput:\n  ReadCapacityUnits: 5000\n  WriteCapacityUnits: 2000\nAutoScaling:\n  Read: target=70, min=1000, max=10000\n  Write: target=70, min=500, max=5000\nGSIs: 2 (total projected size: 120 GB)\nTTL: not enabled\nTable Class: STANDARD\nStreams: NEW_AND_OLD_IMAGES\nMetrics (last 30 days):\n  - ConsumedReadCapacityUnits: avg 850/s, max 1200/s\n  - ConsumedWriteCapacityUnits: avg 400/s, max 600/s\n  - ThrottledRequests: 12,000 (on Read)\n  - SystemErrors: 0\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: DynamoDB, capacity optimization, on-demand vs provisioned, RCU, WCU, auto-scaling, target utilization, partition key, hot partition, GSI, sparse index, adaptive capacity, table class, Standard-Infrequent Access, TTL, DynamoDB Streams, cost optimization, FinOps, consumed capacity, partition skew
  tags: dynamodb, databases, cost-optimization, finops, capacity, autoscaling, gsi
---

# DynamoDB Capacity Optimizer

## What this skill does

Translates a DynamoDB table's capacity configuration and consumed-
capacity profile into a concrete cost-optimization recommendation with
a dollar-denominated savings estimate. The verdict is the highest-
leverage action across seven dimensions — capacity mode (on-demand vs
provisioned), RCU/WCU sizing, auto-scaling target tuning, partition key
design, GSI projection optimization, table class selection, and TTL for
data lifecycle — applied in priority order. Always pairs the
recommendation with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the cost formula | First read |
| Mindset | Why capacity mode is the #1 lever | Understanding the approach |
| Quick reference — verdict thresholds | Decision matrix at a glance | Classifying a table |
| Pre-flight data gate | CloudWatch consumed capacity, CE breakdown | Before any recommendation |
| Step 0 non-obvious behaviours | Crossover math, partition math, GSI billing | Edge cases |
| Step 1 Capacity mode | On-demand vs provisioned crossover at 30% | The headline savings dimension |
| Step 2 RCU/WCU sizing | Consumed-capacity-driven right-sizing | Provisioned tables |
| Step 3 Auto-scaling tuning | Target utilization, min/max bounds | Scaling tables |
| Step 4 Partition key design | Hot partition detection and mitigation | Throttling or skew |
| Step 5 GSI optimization | Projection size, sparse index strategy | Index cost reduction |
| Step 6 Table class | Standard vs Standard-Infrequent Access | Low-traffic tables |
| Step 7 TTL and Streams | Data lifecycle and stream cost | Churn-heavy tables |
| Step 8 Impact estimation | Per-RCU/WCU cost formula and worked math | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, blue/green GSI swap | Before any apply CLI |

## Quick start

- **Capacity mode is the #1 lever.** DynamoDB charges per read/write
  unit. On-demand charges 1.8x-2x the provisioned per-unit rate but
  has zero idle cost. The crossover is at ~30% utilization: if your
  provisioned capacity is used <30% of the time, on-demand is cheaper.
- **Cost formula (memorise this):**
  `provisioned_monthly = (RCU × $0.00013 + WCU × $0.00065) × 730`
  `on_demand_monthly = (read_requests_million × $0.25) + (write_requests_million × $1.25)`
  Crossover: if consumed < 30% of provisioned, on-demand wins.
- **GSIs cost as much as the base table.** A GSI with the same RCU/WCU
  as the base table doubles your bill. Sparse GSIs (small projected
  size) with independent capacity autoscaling are the fix.
- **Table class for low-traffic tables.** Standard-Infrequent Access
  table class costs 60% less per GB than Standard. Use for tables
  < 1 read/sec average (audit logs, cold session stores).

## Mindset

DynamoDB cost optimization is a capacity-mode and access-pattern
decision, not a throughput maximization exercise. The goal is the
billing mode, capacity setting, and index design that minimize dollar
cost while preserving latency and throttling SLOs.

Four principles guide every recommendation:

- **Provisioned pays for idle.** Whether you use the RCU/WCU or not,
  provisioned mode charges for the configured amount 24/7. On-demand
  charges only for what you use. The 30% utilization crossover is the
  single most important calculation.
- **Hot partitions throttle before the table does.** DynamoDB distributes
  data across partitions. A hot partition key (all writes to one key)
  exhausts a single partition's 3000 RCU / 1000 WCU capacity long
  before the table's provisioned capacity is exhausted. Adaptive
  Capacity mitigates this but is reactive, not preventive.
- **GSIs multiply cost.** Every GSI has its own RCU/WCU and storage.
  A table with 3 GSIs configured at the same capacity as the base
  table pays 4x. GSI projection size (which attributes are projected)
  directly affects storage cost and RCUs consumed per query.
- **TTL eliminates storage cost invisibly.** TTL deletes expired items
  automatically at no charge. A table with 90% data churn (logs,
  sessions) that doesn't use TTL pays for data that is never read
  again.

## Quick reference — verdict thresholds

| Observation (14-30 day CloudWatch window) | Verdict | Recommendation |
|---|---|---|
| Provisioned mode AND consumed RCU/WCU sustained < 30% of provisioned | **FURTHER_OPTIMIZATION_AVAILABLE** (capacity mode) | Step 1 — switch to on-demand |
| On-demand mode AND consumed RCU/WCU sustained > 50% of equivalent provisioned | **FURTHER_OPTIMIZATION_AVAILABLE** (capacity mode) | Step 1 — switch to provisioned with auto-scaling |
| Provisioned AND auto-scaling target > 80% AND ThrottledRequests > 0 | **FURTHER_OPTIMIZATION_AVAILABLE** (auto-scaling) | Step 3 — lower target to 60-70%, raise max |
| Provisioned AND ThrottledRequests on specific partition key values | **FURTHER_OPTIMIZATION_AVAILABLE** (partition skew) | Step 4 — redistribute hot keys or add randomization suffix |
| GSI with ALL projection AND projected item size > 2x the key-only size | **FURTHER_OPTIMIZATION_AVAILABLE** (GSI bloat) | Step 5 — reduce to KEYS_ONLY or INCLUDE sparse projection |
| Table in Standard class AND avg consumed RCU < 50/s AND no latency SLA | **FURTHER_OPTIMIZATION_AVAILABLE** (table class) | Step 6 — switch to Standard-Infrequent Access |
| Table has high data churn (>50% items expire) AND no TTL | **FURTHER_OPTIMIZATION_AVAILABLE** (TTL) | Step 7 — enable TTL on the expiry attribute |
| On-demand or provisioned correctly sized AND GSIs optimized AND no skew AND TTL active | **ALREADY_OPTIMAL** | None — continue monitoring |
| CloudWatch consumed-capacity data absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day data, re-evaluate |
| All dimensions verified AND change applied and confirmed this session | **OPTIMIZED** | Emit post-state verification |

## Pre-flight: data gate (run before any optimization decision)

Capacity decisions require consumed-capacity metrics over a
representative window. Pull these before any recommendation. Full CLI
sequences are in `references/dynamodb-pricing-and-capacity.md`.

**Required data sources** (summarized — see reference for full CLI):
1. Table configuration: `aws dynamodb describe-table`
2. Billing mode and provisioned throughput
3. Auto-scaling policies: `aws application-autoscaling describe-scaling-policies`
4. Consumed capacity (14-30 day window): `aws cloudwatch get-metric-statistics`
5. Throttled requests: `aws cloudwatch get-metric-statistics --metric-name ThrottledRequests`
6. TTL status: `aws dynamodb describe-time-to-live`
7. Streams status: `aws dynamodb describe-kinesis-streaming-destination` or `describe-continuous-backups`
8. Cost Explorer DynamoDB breakdown: `aws ce get-cost-and-usage`

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `ConsumedReadCapacityUnits` absent (table never accessed) | **ALREADY_OPTIMAL** with note "dormant table." |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred for seasonal patterns. |
| `ThrottledRequests` > 0 but consumed < provisioned | Hot partition detected. Proceed to Step 4 (partition skew). |
| Auto-scaling policies absent on a PROVISIONED table | No autoscaling — provisioned capacity is static. Flag as finding. |
| `describe-table` returns `ResourceNotFoundException` | Table does not exist in this region. Skip entirely. |
| GSI count > 5 | High index count; flag GSI cost audit (Step 5). |
| PITR enabled | Continuous backups add $0.20/GB-month storage. Factor into total cost. |
| Global Table (replica) detected | Replicated writes consume WCU in each replica region. Factor separately. |

When CloudWatch and Cost Explorer disagree, CloudWatch wins for
consumed-capacity utilization; CE wins for dollar amounts.

## Configuration dependency graph

```
                    ┌────────────────────────────────┐
                    │  CloudWatch Consumed Capacity   │
                    │  Cost Explorer DynamoDB Spend   │
                    │  Table Configuration            │
                    └───────────────┬────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
    ┌──────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │ Capacity Mode    │  │ RCU/WCU Sizing  │  │ Partition Key   │
    │ Crossover (S1)   │  │ + AutoScaling   │  │ Design (S4)     │
    │                  │  │ Tuning (S2/S3)  │  │                 │
    └────────┬─────────┘  └────────┬────────┘  └────────┬────────┘
             │                     │                    │
             ▼                     ▼                    ▼
    ┌─────────────────────────────────────────────────────────┐
    │           GSI Optimization Gate (Step 5)                │
    │  Verify GSI capacity and projection are not excessive   │
    └─────────────────────────┬───────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────┐
    │     Table Class + TTL + Streams Gate (Step 6/7)         │
    │  Verify table class, TTL, and Streams cost are optimal  │
    └─────────────────────────┬───────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────┐
    │           Impact Estimation (Step 8)                    │
    │           Verdict + savings block                        │
    └─────────────────────────────────────────────────────────┘
```

**Dependency rule:** Never recommend a capacity-mode switch without
first verifying the partition key design (Step 4 gate). A hot-partition
problem is a capacity problem, not a billing-mode problem — switching
to on-demand to avoid throttling is a valid mitigation but the root
cause (skew) should be surfaced.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **On-demand charges per request, not per capacity.** A 300 KB item
  read consumes 5 RCU. Item size directly affects on-demand cost.
- **Provisioned mode charges for configured capacity, not consumed.** A
  table provisioned for 10,000 RCU that uses 1,000 RCU pays for 10,000.
  This is the #1 DynamoDB cost waste.
- **The 30% crossover is a rule of thumb, not a cliff.** Writes are 5x
  more expensive than reads ($1.25/M vs $0.25/M on-demand). A write-
  heavy workload hits the crossover at a different utilization than
  read-heavy.
- **Auto-scaling is not instantaneous.** Cooldown period (default 60s)
  and scaling increments mean sudden spikes can throttle before scaling.
- **Adaptive Capacity is automatic and free** (since 2024). It
  temporarily redirects unused capacity from cold partitions to hot ones.
  It does NOT eliminate the need for good partition key design.
- **GSI RCUs and WCUs are independent from the base table.** When the
  base table writes exceed the GSI's WCU, the GSI falls behind.
- **GSI projection ALL stores every attribute.** KEYS_ONLY stores just
  partition+sort key. INCLUDE projects specified attributes — the sweet
  spot for cost-sensitive GSIs.
- **Table class Standard-IA does NOT change capacity pricing.** Only
  storage is 60% cheaper. RCU/WCU pricing stays the same.
- **TTL deletes are free and automatic.** Items past the TTL timestamp
  are deleted within 48 hours. No WCU charged. Cheapest data lifecycle.
- **DynamoDB Streams are billed per read.** Every write generates a
  stream record. Lambda triggers consume RCU-equivalent reads.
- **Global Tables replicate writes to all regions.** Each replica
  region consumes WCU for replicated writes — a 2-region table doubles
  write cost.
- **Switching provisioned→on-demand is instant** (`update-table --
  billing-mode PAY_PER_REQUEST`). Switching back requires re-specifying
  RCU/WCU and auto-scaling.

### Step 1: On-demand vs provisioned capacity mode crossover

This is the primary cost lever. The crossover point determines whether
on-demand (pay per request) or provisioned (pay for capacity) is
cheaper for the observed usage pattern.

**Pricing comparison (us-east-1, 2026):**
```
On-demand:
  Read: $0.25 per million eventually-consistent reads (4 KB item)
  Write: $1.25 per million writes (up to 1 KB item)

Provisioned:
  Read: $0.00013 per RCU-hour
  Write: $0.00065 per WCU-hour

Monthly (730 hours):
  1 RCU for a month: $0.00013 × 730 = $0.0949
  1 WCU for a month: $0.00065 × 730 = $0.4745
```

**Crossover math (read-heavy, 1000 RCU provisioned table):**
```
Provisioned monthly: 1000 × $0.0949 = $94.90
Capacity: 1000 RCU × 2 reads/sec = 2000 reads/sec → 5.256B reads/month at 100%

At 100% utilization: on-demand would cost 5256M × $0.25 = $1,314 → provisioned 13.8x cheaper
At 30% utilization: on-demand = $394.20; provisioned = $94.90 → provisioned 4.2x cheaper
At 10% utilization: on-demand = $131.25; provisioned = $94.90 → barely cheaper
Below ~7% utilization: on-demand wins.

Rule of thumb: consumed > 30% of provisioned → keep provisioned.
Consumed < 15% → on-demand likely wins. Between 15-30% → calculate.
```

**Decision gate:**
```
Is the table in PROVISIONED mode?
├── YES → consumed_capacity / provisioned_capacity over 14-30 days:
│   ├── > 30% → Provisioned is cost-justified. Proceed to Step 2.
│   └── < 30% → Switch to on-demand. Use the formula above.
└── NO (PAY_PER_REQUEST) → estimate equivalent provisioned cost:
    ├── If provisioned cost < on-demand cost → Switch to provisioned.
    └── If provisioned cost ≥ on-demand cost → On-demand is optimal.
```

### Step 2: RCU/WCU sizing from consumed capacity

For provisioned tables that are correctly in provisioned mode, right-
size the RCU/WCU configuration.

**Sizing formula:**
```
required_rcu = max(consumed_rcu_avg) / 0.7  (with 70% target headroom)
required_wcu = max(consumed_wcu_avg) / 0.7

round up to the nearest multiple of 100 for auto-scaling minimum.
```

**Right-sizing decision matrix:**

| Consumed vs Provisioned | Utilization | Verdict | Action |
|---|---|---|---|
| Consumed < 30% of provisioned | Under-utilized | Switch to on-demand (Step 1) | |
| Consumed 30-60% of provisioned | Well-utilized | Reduce provisioned to ~140% of consumed | |
| Consumed 60-85% of provisioned | Optimal | No change needed | |
| Consumed > 85% of provisioned | Near-ceiling | Increase provisioned or fix partition skew | |

**CLI for right-sizing (with auto-scaling):**
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace dynamodb --resource-id table/my-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --min-capacity <new_min> --max-capacity <new_max>

aws application-autoscaling put-scaling-policy \
  --policy-name my-table-read-scaling \
  --service-namespace dynamodb --resource-id table/my-table \
  --scalable-dimension dynamodb:table:ReadCapacityUnits \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{"TargetValue":70.0,"PredefinedMetricSpecification":{"PredefinedMetricType":"DynamoDBReadCapacityUtilization"},"ScaleOutCooldown":60,"ScaleInCooldown":60}'
```

### Step 3: Auto-scaling target utilization tuning

The default auto-scaling target is 70%. This means DynamoDB scales up
when consumed capacity reaches 70% of provisioned.

**When to lower the target (to 50-60%):** ThrottledRequests > 0
during scale-ups, sudden traffic spikes (CV > 1.0), or latency-
sensitive workloads (p99 < 10 ms).

**When to raise the target (to 80%):** Traffic is steady (CV < 0.3),
ThrottledRequests = 0 over 30 days, or frequent scale-in events
(capacity oscillates and a stable target is fine).

**Min/max capacity bounds:**
`min_capacity` ≈ p30 of consumed; `max_capacity` ≈ p99 × 1.2. If min
exceeds p50 consumed, the table is over-provisioned at the floor.

### Step 4: Partition key design and hot-partition detection

DynamoDB partitions data by partition key hash. A hot partition key
(all traffic to one key) exhausts that partition's capacity before the
table-level capacity is reached.

**Hot partition detection via CloudWatch:**
```
Table consumed = 800 RCU/sec of 1000 provisioned → expect no throttle.
But ThrottledRequests > 0. Why?
→ One partition key receives 80% of traffic → 640 RCU on one partition.
→ Partition < 10 GB has 1000 RCU limit; combined hot keys can exceed it.
→ Detection: any partition key consuming > 1000 RCU sustained = hot.
```

**Mitigation strategies:**

| Strategy | When to use | Implementation |
|---|---|---|
| Add randomization suffix to partition key | Write-heavy, uniform reads | `user_id + "#" + random(0-9)` |
| Use sort key for time-series data | Time-series patterns | Partition by date bucket, sort by timestamp |
| Separate hot keys to different tables | Few known hot keys | Dedicated table for high-traffic entities |
| Switch to on-demand | Unknown patterns | Bursting per-request avoids throttle |

**Hot partition is NOT a billing-mode problem.** Switching to on-demand
avoids throttling but does not fix the access pattern. Always surface
the root cause.

### Step 5: GSI optimization

GSIs have independent RCU/WCU and storage. An over-projected GSI with
high capacity is a common cost sink.

**GSI cost audit checklist:**

| Question | If YES → Action |
|---|---|
| Projection type = ALL? | Downgrade to INCLUDE with only queried attributes |
| GSI item size > 50% of base item? | Reduce projected attributes to cut storage + RCU |
| GSI has independent RCU/WCU autoscaling? | Verify min/max bounds are right-sized |
| GSI queried < 100x/day? | Evaluate dropping; use Scan with Filter instead |
| Multiple GSIs on same partition key? | Consolidate or use sparse GSIs |

**Sparse GSI strategy:**
A sparse GSI only includes items with the indexed attribute. If the
attribute exists on < 10% of items, the GSI is 90% smaller — reducing
both storage and RCU cost dramatically.

```
Example: 500M items in base table.
  Non-sparse GSI: 500M items, 200 GB → $50/mo storage + RCU
  Sparse GSI (5% have attribute): 25M items, 10 GB → $2.50/mo (95% saving)
```

**Projection optimization math:**
```
GSI with ALL projection: 500 GB → $125/mo storage
GSI with INCLUDE (3 attributes): 50 GB → $12.50/mo
Savings: $112.50/month per GSI
```

### Step 6: Table class selection

DynamoDB offers two table classes:

| Class | Storage $/GB-month | Use case |
|---|---|---|
| Standard | $0.25 | Active tables (default) |
| Standard-Infrequent Access | $0.10 | Low-traffic, data-heavy tables (60% storage savings) |

**Standard-IA decision gate:**
```
avg_consumed_rcu_per_second < 50 AND table_storage > 50 GB
→ Standard-IA saves 60% on storage, same capacity pricing

Example:
  Table: audit-log-archive
  Storage: 800 GB
  Avg consumed: 8 RCU/sec (occasional compliance queries)

  Standard: 800 × $0.25 = $200/month storage
  Standard-IA: 800 × $0.10 = $80/month storage
  Saving: $120/month (60%)
```

**WARNING:** Standard-IA has no change to capacity pricing. If the
table is in provisioned mode, the RCU/WCU cost is identical. The
savings are storage-only.

### Step 7: TTL and DynamoDB Streams cost impact

**TTL configuration:**
```bash
aws dynamodb update-time-to-live \
  --table-name my-table \
  --time-to-live-specification '{"Enabled": true, "AttributeName": "expires_at"}'
```

TTL items are automatically deleted within 48 hours of the TTL
timestamp. No WCU charged. This is the cheapest data lifecycle
mechanism.

**TTL savings estimation:**
```
churn_storage = table_storage_GB × churn_rate_per_month
Monthly saving = churn_storage × $0.25/GB (Standard) or $0.10/GB (Standard-IA)
Without TTL, churned data accumulates indefinitely.
```

**DynamoDB Streams cost:**
```
Streams enabled with NEW_AND_OLD_IMAGES at 1,000 writes/sec:
  Monthly records: 1,000 × 730 × 3600 = 2.628B records
  Lambda trigger at batch size 100: 26.28M invocations/month
  Lambda cost (512 MB, 200ms): ~$460/month

If the consumer is optional (audit log), consider disabling to save.
```

### Step 8: Impact estimation

Compute the monthly savings for each recommendation:

```
current_monthly_cost =
  (provisioned_rcu × $0.0949) + (provisioned_wcu × $0.4745) +
  (storage_GB × $0.25) + (gsi_rcu × $0.0949) + (gsi_wcu × $0.4745) +
  (gsi_storage_GB × $0.25) + (pitr_storage_GB × $0.20)

projected_monthly_cost =
  (projected_rcu × $0.0949) + (projected_wcu × $0.4745) +
  (projected_storage_GB × class_rate) + ... (all dimensions)

monthly_saving = current_monthly_cost - projected_monthly_cost
```

For on-mode tables:
```
current_monthly_cost =
  (read_requests_M × $0.25) + (write_requests_M × $1.25) +
  (storage_GB × $0.25) + gsi_costs + pitr_costs
```

Always state assumptions: consumed capacity, provisioned capacity,
storage size, GSI count and size, table class, pricing region.

### Step 9: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions pass (correct capacity mode, right-sized, no skew, GSIs
  optimized, correct table class, TTL active where applicable) →
  **ALREADY_OPTIMAL**.
- Change applied and verified this session → **OPTIMIZED**.
- Data insufficient (consumed-capacity absent, window < 14 days) →
  **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO`/`BLOCKED` gate.

## Output format

```text
TARGET: <table-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <billing mode>, <RCU/WCU>, <GSIs>, <table class>, <TTL>, <Streams>
  Proposed: <billing mode>, <RCU/WCU>, <GSIs>, <table class>, <TTL>, <Streams>
  Dimensions changed: <capacity-mode | rcu-wcu-sizing | autoscaling | partition-key | gsi | table-class | ttl-streams>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Monthly: $<amount>
  Annual: $<amount>
  Assumptions: <list (consumed capacity, pricing region, GSI count, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <table-name> in <region>.
  Proceed? (yes/no)"
```

Full worked examples are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block against these rules
before returning the response.

### Decision tree (determines VERDICT)

Walk this tree top-to-bottom. The FIRST matching leaf sets the VERDICT.
Cite the evidence (CloudWatch consumed vs provisioned, GSI projection
size, TTL status) in the REASON field.

```text
Is there >= 14 days of CloudWatch ConsumedReadCapacityUnits / ConsumedWriteCapacityUnits data?
├── NO  → VERDICT: NEED_MORE_INFO             (data gate failed; emit no savings)
└── YES → Hard blocker present (Global Table replication conflict, IAM denies DescribeTable)?
          ├── YES → VERDICT: BLOCKED
          └── NO  → Walk the 7 optimization dimensions in priority order:
                    D1 Capacity mode crossover (provisioned consumed < 30% of provisioned)?
                    ├── YES → leaf: capacity-mode    → FURTHER_OPTIMIZATION_AVAILABLE
                    └── NO  → D2 RCU/WCU sizing (consumed 30-60% AND provisioned > 1.4 × consumed)?
                              ├── YES → leaf: rcu-wcu-sizing  → FURTHER_OPTIMIZATION_AVAILABLE
                              └── NO  → D3 Auto-scaling (target > 80% AND ThrottledRequests > 0)?
                                        ├── YES → leaf: autoscaling       → FURTHER_OPTIMIZATION_AVAILABLE
                                        └── NO  → D4 Partition skew (ThrottledRequests > 0 with consumed < provisioned)?
                                                  ├── YES → leaf: partition-key    → FURTHER_OPTIMIZATION_AVAILABLE
                                                  └── NO  → D5 GSI bloat (ALL projection AND item > 2× KEYS_ONLY size)?
                                                            ├── YES → leaf: gsi             → FURTHER_OPTIMIZATION_AVAILABLE
                                                            └── NO  → D6 Table class (Standard AND avg RCU < 50/s AND storage > 50 GB)?
                                                                      ├── YES → leaf: table-class    → FURTHER_OPTIMIZATION_AVAILABLE
                                                                      └── NO  → D7 TTL/Streams (churn > 50% AND no TTL, OR Streams unused)?
                                                                                ├── YES → leaf: ttl-streams    → FURTHER_OPTIMIZATION_AVAILABLE
                                                                                └── NO  → Was a change applied AND verified THIS session?
                                                                                          ├── YES → VERDICT: OPTIMIZED
                                                                                          └── NO  → VERDICT: ALREADY_OPTIMAL
```

**Zero-savings rule:** if every dimension nets $0.00, the verdict MUST
be `ALREADY_OPTIMAL` — never `FURTHER_OPTIMIZATION_AVAILABLE`.

### Required output structure

Every response MUST be a single block using these literal labels, in
this order. Do NOT substitute markdown headings, camelCase, or bold
variants.

```text
TARGET: <table-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE | ALREADY_OPTIMAL
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <billing mode>, <RCU/WCU>, <GSIs>, <table class>, <TTL>, <Streams>
  Proposed: <billing mode>, <RCU/WCU>, <GSIs>, <table class>, <TTL>, <Streams>
  Dimensions changed: <capacity-mode | rcu-wcu-sizing | autoscaling | partition-key | gsi | table-class | ttl-streams>
  Dimensions checked: <list ALL seven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_SAVINGS:
  Current monthly: $<amount>    ← MUST show capacity + storage + GSI subtotals
  Projected monthly: $<amount>
  Monthly saving: $<amount>     ← MUST equal Current − Projected, 2 decimals
  Annual saving: $<amount>      ← MUST equal Monthly × 12
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: <confirmation prompt text>
```

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Monthly saving: $0.00`.** If every dimension nets zero cost delta,
   the verdict MUST be `ALREADY_OPTIMAL`.

2. **NEVER show savings math that does not balance.**
   `Current monthly − Projected monthly` MUST equal `Monthly saving`,
   rounded to 2 decimal places.

3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.

4. **NEVER recommend switching from provisioned to on-demand without
   citing consumed-capacity utilization from CloudWatch.** The REASON
   MUST name the evidence (consumed vs provisioned over the observation
   window).

5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all seven dimensions, each marked
   ✓ (no finding) or → (finding).

6. **NEVER recommend dropping a GSI without confirming no application
   queries depend on it.** GSI removal breaks queries that use the GSI
   as the backing index.

7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE

Every field below is internally consistent. Copy this shape exactly.
Note: on-demand was evaluated but the write-heavy ratio (5:1 cost) means
provisioned at reduced capacity wins. The skill catches this.

```text
TARGET: user-events-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Provisioned table at 5000 RCU / 2000 WCU consumed at only 17%
  read and 20% write utilization (CloudWatch 30-day). On-demand evaluated
  but write-heavy ratio makes on-demand 38% MORE expensive. Instead,
  reduce provisioned to 1200 RCU / 600 WCU with autoscaling. GSI with ALL
  projection (120 GB) → INCLUDE (30 GB) saves GSI storage 75%. TTL not
  enabled despite 60% churn; Streams Lambda consuming $238/month.
RECOMMENDATION:
  Current: PROVISIONED 5000 RCU / 2000 WCU, 2 GSIs (ALL, 120 GB), no TTL, Streams on
  Proposed: PROVISIONED 1200 RCU / 600 WCU (autoscaled), 2 GSIs (INCLUDE, 30 GB), TTL on, Streams off
  Dimensions changed: capacity-mode → rcu-wcu-sizing → gsi → ttl-streams
  Dimensions checked: capacity-mode ✓ (provisioned confirmed)  rcu-wcu-sizing → (reduce)
    autoscaling → (retune)  partition-key ✓ (no skew)  gsi → (reduce projection)
    table-class ✓ (Standard, high traffic)  ttl-streams → (enable TTL, disable Streams)
  Confidence: HIGH — 30-day CloudWatch confirms 17% utilization; on-demand
    crossover verified (writes 5x cost make provisioned optimal at this ratio).
ESTIMATED_SAVINGS:
  Current monthly: $2,137.80
    capacity: 5000 RCU × $0.0949 + 2000 WCU × $0.4745 = $1,423.50
    storage: 200 GB × $0.25 = $50.00
    GSI capacity+storage: $332.15 + $30.00 = $362.15
    PITR: 320 GB × $0.20 = $64.00; Streams Lambda: $238.15
  Projected monthly: $571.45
    capacity: 1200 RCU × $0.0949 + 600 WCU × $0.4745 = $398.58
    storage (TTL reduces 60%): 80 GB × $0.25 = $20.00
    GSI capacity+storage (INCLUDE): $123.37 + $7.50 = $130.87
    PITR: 110 GB × $0.20 = $22.00; Streams: $0
  Monthly saving: $1,566.35 ($2,137.80 − $571.45 ✓)
  Annual saving: $18,796.20
MIGRATION_STEPS:
  1. Reduce autoscaling min capacity:
     aws application-autoscaling register-scalable-target \
       --service-namespace dynamodb --resource-id table/user-events-prod \
       --scalable-dimension dynamodb:table:ReadCapacityUnits \
       --min-capacity 1200 --max-capacity 3000
  2. Recreate GSI with INCLUDE projection (swap: create new, verify, delete old):
     aws dynamodb update-table --table-name user-events-prod \
       --global-secondary-index-updates '[{"Create":{"IndexName":"by-type-v2",...}}]'
  3. Enable TTL: aws dynamodb update-time-to-live --table-name user-events-prod \
       --time-to-live-specification '{"Enabled":true,"AttributeName":"expires_at"}'
  4. Disable Streams after confirming no Lambda consumers depend on it.
  5. Monitor ThrottledRequests and ConsumedCapacity for 7 days.
CONFIRM: About to reduce capacity (5000→1200 RCU, 2000→600 WCU), swap GSI,
  enable TTL, disable Streams on user-events-prod. Saving $1,566.35/mo (73.3%).
  Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current monthly − Projected monthly == Monthly saving` (2 decimals)?
- [ ] `Monthly saving × 12 == Annual saving`?
- [ ] All seven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] On-demand vs provisioned crossover math verified before recommending switch?
- [ ] No scratch/recompute text in the block?

### Perfect example output — OPTIMIZED (post-apply verification)

This is the shape emitted AFTER the operator approves and the change is
applied. VERDICT is `OPTIMIZED` (not FURTHER_OPTIMIZATION_AVAILABLE).
The "before → after" capacity numbers and dollar savings are preserved
so downstream FinOps can close the loop.

```text
TARGET: user-events-prod
VERDICT: OPTIMIZED
REASON: Capacity reduced from 5000/2000 to 1200/600 RCU/WCU with
  autoscaling; GSI recreated with INCLUDE projection (120 GB → 30 GB);
  TTL enabled on expires_at; Streams disabled. CloudWatch confirms zero
  ThrottledRequests over the 7-day post-apply window.
RECOMMENDATION:
  Current: PROVISIONED 1200 RCU / 600 WCU (autoscaled, target 70%), 2 GSIs (INCLUDE, 30 GB), TTL on (expires_at), Streams off
  Proposed: same as Current — no further action
  Dimensions changed: capacity-mode ✓  rcu-wcu-sizing ✓ (applied)  autoscaling ✓ (applied)
    partition-key ✓ (no skew)  gsi ✓ (applied)  table-class ✓ (Standard, high traffic)  ttl-streams ✓ (applied)
  Confidence: HIGH — 7-day post-apply CloudWatch shows ConsumedReadCapacityUnits avg 820/s, max 1190/s; zero ThrottledRequests.
ESTIMATED_SAVINGS:
  Pre-apply monthly: $2,137.80
  Post-apply monthly: $571.45
  Monthly saving: $1,566.35 ($2,137.80 − $571.45 ✓)
  Annual saving: $18,796.20
MIGRATION_STEPS:
  1. Completed: autoscaling min reduced (5000→1200 RCU, 2000→600 WCU) on 2026-08-04.
  2. Completed: GSI recreated with INCLUDE projection (by-type-v2 live, by-type-v1 deleted).
  3. Completed: TTL enabled on expires_at; first deletes observed within 38 hours.
  4. Completed: Streams disabled after confirming no Lambda consumers.
  5. Monitor ThrottledRequests and ConsumedCapacity for 7 more days.
CONFIRM: Change applied and verified. No further approval needed.
```

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, savings-bearing recommendation. |
| `OPTIMIZED` | A change was applied and verified this session; CloudWatch confirms no throttling. |
| `ALREADY_OPTIMAL` | All dimensions pass (correct capacity mode, right-sized, no skew, GSIs optimized, TTL active). |
| `NEED_MORE_INFO` | Data gate failed: consumed-capacity metrics absent, window < 14 days. |
| `BLOCKED` | Hard precondition prevents evaluation: table in a Global Table with replication conflicts, IAM denies dynamodb:DescribeTable. |

**Zero-savings rule:** If MONTHLY_SAVING == $0.00 for every dimension,
verdict MUST be `ALREADY_OPTIMAL`, never `FURTHER_OPTIMIZATION_AVAILABLE`.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend switching to on-demand without verifying the
   consumed-to-provisioned ratio over at least 14 days.** A single-day
   spike can make provisioned look necessary; a single-day lull can
   make on-demand look cheaper. Use 14-30 day data.

2. **NEVER recommend dropping a GSI without confirming which application
   queries use it.** Dropping a GSI that backs a critical query path
   causes application errors. Always verify GSI usage via CloudTrail
   or application code audit before removal.

3. **NEVER recommend a partition key change without a migration plan.**
   Changing the partition key requires creating a new table, backfilling
   data (via Data Pipeline or BatchWriteItem), and cutting over the
   application. This is NOT a one-CLI-command change.

4. **NEVER enable TTL on the wrong attribute.** TTL deletes items
   permanently when the attribute value (Unix epoch timestamp) is in
   the past. Setting TTL on a non-timestamp attribute causes mass data
   deletion. Always verify the attribute contains epoch seconds.

5. **NEVER assume adaptive capacity eliminates hot partitions.**
   Adaptive Capacity is a safety net, not a design principle. It
   delays throttling but does not prevent it under sustained skew.
   Fix the access pattern.

Extended anti-patterns in `references/dynamodb-pricing-and-capacity.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Test GSI changes on a new index, not the existing one.** Create a
  new GSI with the desired projection; verify queries work; then delete
  the old GSI. Never modify an in-use GSI directly (GSIs cannot be
  modified — only created or deleted).
- **Verify no consumers depend on Streams before disabling.** Lambda
  triggers on DynamoDB Streams will silently stop processing. Check
  event source mappings before disabling.
- **TTL takes up to 48 hours for the first deletes.** Do not expect
  immediate storage reduction. Monitor table size over 7 days.
- **Capacity mode switch from provisioned to on-demand is instant**
  but switching back requires specifying RCU/WCU. Ensure the rollback
  path is documented.
- **Auto-scaling changes can cause brief throttling.** Lowering
  min-capacity below the current consumed rate will cause throttling
  during the transition. Lower gradually.
- **Global Table replica changes require multi-region coordination.**
  Do not change capacity on a Global Table member without verifying
  replication health first.
- **Bulk-operation limit:** Process at most 5 tables per batch. Sort
  by estimated savings, verify each batch before proceeding. Abort if
  any table shows increased throttling or errors post-change.

## Recent AWS features (2024-2026)

- **Standard-Infrequent Access table class (2024):** 60% storage cost
  reduction for low-traffic tables. No capacity pricing change.
- **Adaptive capacity improvements (2024-2025):** Absorbs hot-partition
  spikes faster (seconds). Still reactive, not preventive.
- **On-demand mode maturation (2024-2025):** Instant mode switching.
  The 30% crossover rule remains the guideline.
- **Streams to Kinesis Data Streams (2024):** KDS alternative offers
  longer retention but higher cost. Flag if detected.
- **Global Tables writer improvements (2025):** Replicated write
  consumption optimized by 15%. Still doubles write cost for 2-region.
- **IaC support (2024-2025):** CloudFormation/CDK now support table
  class, TTL, and auto-scaling in one resource definition.
- **Zero-ETL integration with OpenSearch (2025-2026):** Eliminates
  custom search pipelines. Flag if detected.

## References

- `references/dynamodb-pricing-and-capacity.md` — pricing tables,
  capacity-mode crossover math, GSI projection cost analysis, partition
  key design patterns, auto-scaling configuration, extended NEVER list,
  regional pricing multipliers.
- `references/worked-examples.md` — full worked examples (capacity mode
  crossover, auto-scaling tuning, GSI optimization, hot partition, already-
  optimal, NEED_MORE_INFO, end-to-end walkthrough).

## Domain

AWS CloudOps / DynamoDB Capacity Cost Optimization & FinOps.

## AWS documentation

- **Amazon DynamoDB Developer Guide** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Welcome.html
- **Amazon DynamoDB pricing** — https://aws.amazon.com/dynamodb/pricing/
- **DynamoDB capacity modes** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html
- **DynamoDB auto-scaling** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/AutoScaling.html
- **DynamoDB partition key design** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html
- **DynamoDB GSI best practices** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-indexes.html
- **DynamoDB TTL** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html
- **DynamoDB table classes** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/table-class.html
- **DynamoDB Streams** — https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Streams.html
- **AWS Well-Architected Framework — Cost Optimization** — https://docs.aws.amazon.com/wellarchitected/latest/cost-optimization-pillar/welcome.html
