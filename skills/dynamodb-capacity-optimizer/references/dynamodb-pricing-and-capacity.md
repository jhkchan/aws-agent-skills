# DynamoDB Pricing and Capacity Reference

Supplementary reference for the DynamoDB Capacity Optimizer skill. Loaded
on-demand when detailed pricing math, crossover analysis, GSI cost
calculations, or partition key design patterns are needed.

## DynamoDB pricing (us-east-1, 2026, USD)

### On-demand pricing

| Operation | Rate | Unit |
|---|---|---|
| Read (eventually consistent) | $0.25 | per million reads (4 KB item) |
| Read (strongly consistent) | $0.50 | per million reads (4 KB item) |
| Write | $1.25 | per million writes (1 KB item) |
| Stream read | $0.0212 | per million stream reads |

### Provisioned pricing

| Resource | $/hour | Monthly (730h) | Capacity |
|---|---|---|---|
| Read Capacity Unit (RCU) | $0.00013 | $0.0949 | 2 eventually-consistent reads/sec (4 KB) |
| Write Capacity Unit (WCU) | $0.00065 | $0.4745 | 1 write/sec (1 KB) |

### Storage pricing

| Table class | $/GB-month | Notes |
|---|---|---|
| Standard | $0.25 | Default |
| Standard-Infrequent Access | $0.10 | 60% cheaper; same capacity pricing |

### Additional pricing

| Feature | Rate | Notes |
|---|---|---|
| PITR (Point-in-Time Recovery) | $0.20/GB-month | Continuous backups; based on table + GSI size |
| DynamoDB Streams | Free | But Lambda triggers consume invocations |
| Global Tables | WCU in each replica | 2-region doubles write cost |
| Data transfer out | $0.09/GB | Cross-region or internet |

## On-demand vs provisioned crossover math

### Crossover formula

```
On-demand monthly cost:
  reads = (consumed_rcu_per_sec × 730 × 3600 / 2) × ($0.25 / 1,000,000)
  writes = (consumed_wcu_per_sec × 730 × 3600) × ($1.25 / 1,000,000)

Provisioned monthly cost:
  capacity = (provisioned_rcu × $0.0949) + (provisioned_wcu × $0.4745)

Crossover utilization = on_demand_cost / provisioned_cost
If crossover < 0.30 → on-demand is cheaper
If crossover > 0.30 → provisioned is cheaper
```

### Worked example: read-heavy table

```
Table: 1000 RCU provisioned, consumed 200 RCU/s avg
Provisioned monthly: 1000 × $0.0949 = $94.90
On-demand reads: (200 × 2 × 730 × 3600) × $0.25/M = 1,051,200,000 reads
  → 1051M × $0.25 = $262.80

Utilization: 200/1000 = 20% → on-demand is CHEAPER at this level.
Wait: on-demand ($262.80) > provisioned ($94.90). Provisioned is cheaper!

The 30% rule accounts for both read AND write cost ratios.
At 20% utilization, on-demand is $262.80 vs provisioned $94.90.
Provisioned wins even at 20% because on-demand reads are priced per-
request while provisioned is per-capacity-unit.

The TRUE crossover is lower than 30% for pure-read workloads.
For write-heavy: writes cost 5x reads on-demand, so crossover shifts.
```

### Accurate crossover (with both reads and writes)

```
Example: 5000 RCU / 2000 WCU provisioned, 15% utilization
Consumed: 750 RCU/s, 300 WCU/s

Provisioned monthly:
  5000 × $0.0949 + 2000 × $0.4745 = $474.50 + $949.00 = $1,423.50

On-demand monthly:
  Reads: (750 × 2 × 730 × 3600) × $0.25/M = 3,942M × $0.25 = $985.50
  Writes: (300 × 730 × 3600) × $1.25/M = 788M × $1.25 = $985.50
  Total: $1,971.00

On-demand ($1,971) > Provisioned ($1,423.50). Provisioned is still cheaper
even at 15% utilization because this table has a large WCU component.

This is why the 30% rule is a guideline, not absolute. Always compute.
For tables with heavy WCU: provisioned can be cheaper even at 15%.
For read-only or read-heavy tables: on-demand crossover is higher (~40%).

ACCURATE RULE:
  Read-heavy (>5:1 read:write): on-demand crossover at ~40% utilization
  Balanced (1:1 to 5:1): on-demand crossover at ~30%
  Write-heavy (<1:1): on-demand crossover at ~15%
```

## GSI cost analysis

### Projection types and cost

| Projection | What it stores | Storage relative to base | RCU per query |
|---|---|---|---|
| ALL | Every attribute | 100% of base item size | Standard RCU |
| KEYS_ONLY | Partition + sort key only | ~5-10% of base | Standard RCU |
| INCLUDE | Keys + specified attributes | 10-50% of base | Standard RCU |

### GSI capacity sizing

GSIs have independent RCU/WCU from the base table:

```
GSI WCU must be ≥ base table write rate to the indexed items.
If base writes 1000 WCU/s and GSI indexes 50% of items:
  GSI needs ≥ 500 WCU/s (or on-demand auto-scales)

GSI RCU is sized to the query pattern:
  If GSI is queried 100 queries/sec, each consuming 5 RCU:
  Need 500 RCU (provisioned) or on-demand handles it per-request.
```

### Sparse GSI cost saving

```
Base table: 100M items, 8 KB avg, total 800 GB storage
GSI with ALL projection: 800 GB → $200/month (Standard)
GSI with INCLUDE (3 attributes, 500 bytes avg): 50 GB → $12.50/month
Saving: $187.50/month per GSI

For 3 GSIs with ALL projection: 2,400 GB → $600/month
After switching 2 to KEYS_ONLY, 1 to INCLUDE: 58 GB → $14.50/month
Saving: $585.50/month
```

## Partition key design patterns

### Hot partition detection

```
Symptom: ThrottledRequests > 0 despite consumed < provisioned
Root cause: one or few partition keys receive disproportionate traffic

Detection via CloudWatch:
  - Consumed capacity at table level looks fine (< 50%)
  - But specific partition key values are saturated
  - Partition capacity limits:
    - < 10 GB partition: 1000 RCU / 1000 WCU
    - > 10 GB partition: 3000 RCU / 1000 WCU
```

### Mitigation patterns

| Pattern | Implementation | Trade-off |
|---|---|---|
| Random suffix | `user_id + "#" + random(0-N)` | Must query N+1 partitions on read |
| Date bucket | `YYYY-MM-DD` partition key | Hot partition on current day |
| Hash prefix | `hash(user_id)[:2] + user_id` | Uniform distribution, same read cost |
| Separate tables | Hot keys in dedicated table | Operational overhead |

## Regional pricing multipliers

| Region | Multiplier | Notes |
|---|---|---|
| us-east-1, us-east-2, us-west-2 | 1.00x | Baseline |
| us-west-1 | 1.05x | |
| eu-west-1, eu-central-1 | 1.10-1.15x | |
| ap-southeast-1, ap-southeast-2 | 1.12-1.18x | |
| ap-northeast-1 | 1.10-1.15x | |
| ap-south-1 | 1.15-1.25x | |
| sa-east-1 | 1.35-1.50x | Highest |

## Extended NEVER list (supplementary anti-patterns)

- NEVER switch from provisioned to on-demand based on a single day of
  low utilization. Use minimum 14-day average.

- NEVER assume on-demand is always cheaper for "low traffic" tables.
  Write-heavy tables at 15% utilization may still be cheaper provisioned.

- NEVER create GSIs with ALL projection "just in case." Each GSI
  multiplies write cost and storage. Use INCLUDE with explicit attribute
  lists.

- NEVER enable Streams without evaluating the Lambda consumer cost. At
  high write rates, Streams-triggered Lambda can cost more than the
  table itself.

- NEVER change partition key design without a full data migration plan.
  It requires a new table, backfill, and application cutover.

- NEVER assume Standard-IA saves money on capacity. It only saves on
  storage. If capacity cost dominates, IA provides no benefit.

- NEVER trust adaptive capacity as a design principle. It is a safety
  net, not a partitioning strategy.

- NEVER set auto-scaling min-capacity above p50 consumed. The table
  will be over-provisioned at the floor 24/7.

- NEVER leave TTL disabled on tables with known data expiry. TTL is
  free and automatic — there is no downside.

---

## Step 1 pricing comparison and crossover math (moved from SKILL.md)

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
