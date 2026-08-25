# Advanced Patterns (load on demand) — DynamoDB Capacity Optimizer

Mindset principles, the configuration dependency graph, Step 0 non-obvious behaviours, per-step detail, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Mindset (moved from SKILL.md)

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

---

## Configuration dependency graph (moved from SKILL.md)

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

---

## Step 0: Non-obvious behaviours that change the recommendation (moved from SKILL.md)

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

---

## Step 2: RCU/WCU sizing from consumed capacity (moved from SKILL.md)

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

---

## Step 4: Partition key design and hot-partition detection (moved from SKILL.md)

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

---

## Step 5: Sparse GSI strategy and projection math (moved from SKILL.md)

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

---

## Step 6: Table class selection (moved from SKILL.md)

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

---

## Step 7: TTL and DynamoDB Streams cost impact (moved from SKILL.md)

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

---

## Recent AWS features (2024-2026) (moved from SKILL.md)

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
