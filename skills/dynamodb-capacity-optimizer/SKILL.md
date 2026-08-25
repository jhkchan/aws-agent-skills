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

Four-principle mindset (provisioned pays for idle, hot partitions throttle first, GSIs multiply cost, TTL eliminates storage cost invisibly) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when explaining why capacity mode is the #1 lever.

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

Configuration dependency graph (consumed-capacity inputs through the capacity-mode / sizing / partition-key gates to the verdict block) and the never-switch-mode-before-Step-4 dependency rule moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when sequencing a multi-dimension optimization.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

All twelve non-obvious behaviours (per-request on-demand billing, provisioned idle charge, 30% crossover nuance, autoscaling cooldown lag, adaptive capacity, GSI capacity independence, projection types, Standard-IA storage-only pricing, free TTL deletes, Streams read billing, Global Tables WCU multiplier, instant mode switch) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when an operational gotcha could reroute the recommendation.

### Step 1: On-demand vs provisioned capacity mode crossover

This is the primary cost lever. The crossover point determines whether
on-demand (pay per request) or provisioned (pay for capacity) is
cheaper for the observed usage pattern.

us-east-1 2026 pricing comparison and the 1000-RCU crossover math (provisioned 13.8x cheaper at 100%, on-demand wins below ~7%) moved verbatim to [references/dynamodb-pricing-and-capacity.md](references/dynamodb-pricing-and-capacity.md).
Load on demand when computing the capacity-mode crossover.

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

RCU/WCU sizing formula (max consumed / 0.7, round up to 100) and the right-sizing decision matrix moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when right-sizing a provisioned table.

Right-sizing CLI (register-scalable-target + TargetTrackingScaling put-scaling-policy) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before applying any capacity change.

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

Hot-partition detection math (any partition key consuming > 1000 RCU sustained) and the four mitigation strategies moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when ThrottledRequests > 0 with consumed < provisioned.

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

Sparse GSI strategy (5%-attribute example, 95% saving) and projection optimization math ($112.50/month per GSI) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when auditing GSI projection size.

### Step 6: Table class selection

Table class comparison, the Standard-IA decision gate (avg RCU < 50/s AND storage > 50 GB, $120/month example), and the storage-only-savings warning moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when evaluating Standard vs Standard-Infrequent Access.

### Step 7: TTL and DynamoDB Streams cost impact

TTL CLI, TTL savings estimation formula, and the Streams/Lambda cost math (~$460/month at 1,000 writes/sec) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when evaluating TTL or Streams cost.

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

Simple per-table output block moved verbatim to [references/worked-examples.md](references/worked-examples.md); the STRICT output contract below remains authoritative.
Load on demand when emitting a non-strict summary block.

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

OPTIMIZED post-apply verification example moved verbatim to [references/worked-examples.md](references/worked-examples.md); the FURTHER_OPTIMIZATION_AVAILABLE example above is the primary inline example.
Load on demand when emitting the post-apply OPTIMIZED verdict.

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

Pre-remediation safety checks (CONFIRM gate, GSI blue/green swap, Streams consumer check, TTL 48-hour lag, mode-switch rollback path, gradual capacity lowering, Global Table coordination, 5-table batches) moved verbatim to [references/diagnostic-commands.md](references/diagnostic-commands.md).
Load on demand before executing any remediation CLI.

## Recent AWS features (2024-2026)

Recent AWS features 2024-2026 (Standard-IA class, adaptive capacity improvements, on-demand maturation, KDS alternative, Global Tables writer optimizations, IaC support, OpenSearch zero-ETL) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when a 2024-2026 feature affects the recommendation.

## References

- `references/dynamodb-pricing-and-capacity.md` — pricing tables,
  capacity-mode crossover math, GSI projection cost analysis, partition
  key design patterns, auto-scaling configuration, extended NEVER list,
  regional pricing multipliers.
- `references/worked-examples.md` — full worked examples (capacity mode
  crossover, auto-scaling tuning, GSI optimization, hot partition, already-
  optimal, NEED_MORE_INFO, end-to-end walkthrough).

## References (load on demand)

- [`references/advanced-patterns.md`](references/advanced-patterns.md) — Mindset principles, configuration dependency graph, Step 0 gotchas, Steps 2/4/5/6/7 detail, and recent AWS features (2024-2026) moved from SKILL.md
- [`references/diagnostic-commands.md`](references/diagnostic-commands.md) — pre-remediation safety checks and the right-sizing CLI moved from SKILL.md
- [`references/dynamodb-pricing-and-capacity.md`](references/dynamodb-pricing-and-capacity.md) — capacity-mode pricing comparison and crossover math moved from SKILL.md, plus the pre-existing pricing tables, partition-key patterns, and extended NEVER list
- [`references/worked-examples.md`](references/worked-examples.md) — the simple output block and the OPTIMIZED post-apply example moved from SKILL.md, plus the pre-existing worked examples

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
