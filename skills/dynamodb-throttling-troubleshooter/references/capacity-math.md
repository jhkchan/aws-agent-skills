# DynamoDB Capacity Math — Reference

Supplementary reference for the DynamoDB Throttling Troubleshooter skill.
The RCU/WCU consumption formulas, cost multipliers, and capacity planning
heuristics needed to diagnose throttling root cause.

## Read Capacity Units (RCU)

| Read type | RCU per 4 KB item read | Notes |
|---|---|---|
| Eventually consistent | 0.5 RCU | Default; `GetItem`, `Query`, `Scan` without `ConsistentRead` |
| Strongly consistent | 1.0 RCU | `ConsistentRead: true` on `GetItem` / `Query` |
| Transactional (`TransactGetItems`) | 2.0 RCU | 2x the strongly-consistent cost |

### RCU calculation

```
RCU consumed = ceil(item_size_kb / 4) × consistency_multiplier
```

Where:
- `item_size_kb` = size of the item in KB (rounded up to nearest 1 KB first)
- `consistency_multiplier` = 0.5 (eventual), 1.0 (strong), 2.0 (transactional)

### Worked examples

| Item size | Eventually consistent | Strongly consistent | Transactional |
|---|---|---|---|
| 1 KB | 0.5 RCU | 1 RCU | 2 RCU |
| 4 KB | 0.5 RCU | 1 RCU | 2 RCU |
| 5 KB | 1.0 RCU | 2 RCU | 4 RCU |
| 10 KB | 1.5 RCU | 3 RCU | 6 RCU |
| 40 KB | 5.0 RCU | 10 RCU | 20 RCU |
| 400 KB (max item) | 50 RCU | 100 RCU | 200 RCU |

### Scan RCU cost

A `Scan` reads every item in the table (or segment). The total RCU cost
for a full Scan is:

```
Scan RCUs = ceil(total_table_size_kb / 4) × 0.5  (eventually consistent)
```

For a 100 GB table: 100 × 1024 × 1024 / 4 × 0.5 = ~13.1 million RCUs.

A `FilterExpression` does NOT reduce RCU cost — the filter is applied
AFTER all items are read. A Scan that filters out 99% of items still
consumes the full Scan RCU cost.

## Write Capacity Units (WCU)

| Write type | WCU per 1 KB written | Notes |
|---|---|---|
| Standard (`PutItem`, `UpdateItem`, `DeleteItem`) | 1.0 WCU | Per 1 KB of item size |
| Transactional (`TransactWriteItems`) | 2.0 WCU | 2x the standard cost |

### WCU calculation

```
WCU consumed = ceil(item_size_kb / 1) × consistency_multiplier
```

Where:
- `item_size_kb` = size of the larger of (old item, new item) for updates,
  rounded up to nearest 1 KB
- `consistency_multiplier` = 1.0 (standard), 2.0 (transactional)

### Worked examples

| Item size | Standard write | Transactional write |
|---|---|---|
| 1 KB | 1 WCU | 2 WCU |
| 500 bytes | 1 WCU | 2 WCU |
| 2.5 KB | 3 WCU | 6 WCU |
| 10 KB | 10 WCU | 20 WCU |
| 400 KB (max item) | 400 WCU | 800 WCU |

## GSI Write Cost Multiplier

Each GSI on the table replicates writes. The total WCU cost per item
write is:

```
Total WCU = base_write_wcu × (1 + number_of_GSIs_that_replicate_the_change)
```

A GSI only replicates the write if the item attributes in the GSI's key
schema or projection change. If the update does not touch GSI-projected
attributes, the GSI does not replicate.

### Worked examples

| Table config | 1 KB write cost | Notes |
|---|---|---|
| No GSIs | 1 WCU | Base table only |
| 1 GSI (all attributes projected) | 2 WCU | 1 (base) + 1 (GSI replica) |
| 3 GSIs (all attributes projected) | 4 WCU | 1 (base) + 3 (GSI replicas) |
| 5 GSIs (all attributes projected) | 6 WCU | 1 (base) + 5 (GSI replicas) |
| 3 GSIs (only key attributes projected) | 1-4 WCU | Depends on which attributes changed |

**Planning rule:** each GSI roughly doubles the write cost of the base
table for full-projection GSIs. Before adding a GSI, audit whether the
query pattern justifies the 2x write multiplier.

## Partition Key Distribution

DynamoDB partitions data by partition key hash. Each partition receives
an equal share of the table's provisioned capacity. A hot partition
(one key value receiving disproportionate traffic) exhausts its share
faster than the table's aggregate capacity.

### Partition capacity allocation

```
Per-partition capacity ≈ table_capacity / number_of_partitions
```

A table with 10 partitions and 10,000 WCU provisioned gives each
partition ~1,000 WCU. If one partition receives 5,000 WCU of traffic,
it throttles even though the table aggregate (5,000) is below provisioned
(10,000).

### Hot partition thresholds

| Partition key cardinality | Risk | Notes |
|---|---|---|
| < 100 distinct values | HIGH | Almost certainly hot |
| 100 - 1,000 distinct values | MEDIUM | Risky if distribution is skewed |
| 1,000 - 10,000 distinct values | LOW | Generally safe if evenly distributed |
| > 10,000 distinct values | MINIMAL | Safe unless power-law distribution |

### Skew detection

Use Contributor Insights to identify the top partition key values by
traffic volume. A key where the top value exceeds 10% of total traffic
is a hot partition candidate. The top value exceeding 50% is a confirmed
hot partition.

```bash
aws dynamodb describe-contributor-insights --table-name <table>
```

## Burst Capacity

DynamoDB retains up to 5 minutes (300 seconds) of unused provisioned
capacity as burst. When traffic exceeds provisioned, the burst absorbs
the excess — until it runs out.

### Burst budget calculation

```
Burst budget = unused_capacity_per_second × 300 seconds
```

A table provisioned at 10,000 WCU with sustained traffic of 5,000 WCU
accumulates: (10,000 - 5,000) × 300 = 1,500,000 WCU of burst budget.

A spike of 50,000 WCU for 30 seconds consumes 50,000 × 30 = 1,500,000
WCU — exactly exhausting the burst. Further spikes throttle.

### Burst is per-partition

The burst budget is per-partition, not per-table. A hot partition only
accumulates burst from its own unused capacity. A table with 10 partitions
and even traffic accumulates 10 × per-partition-burst. A table with a
hot partition accumulates only 1 × per-partition-burst for the hot
partition.

This is why hot partitions exhaust burst faster than even distributions,
even at the same aggregate traffic rate.

## Adaptive Capacity

When a partition becomes hot, DynamoDB's adaptive capacity redirects
traffic to other partitions with spare capacity. The redirect introduces
a lag (seconds to minutes).

### Adaptive capacity behavior

1. Partition A becomes hot (exceeds its share of provisioned capacity).
2. DynamoDB detects the hot partition (within seconds).
3. DynamoDB redirects excess traffic to partitions with spare capacity.
4. The redirect takes effect after a lag (seconds to minutes).

During the lag, throttling persists even if the table has aggregate
capacity headroom. This is the "throttling after scale-up" pattern.

### Adaptive capacity limits

Adaptive capacity redistributes WITHIN the table's provisioned capacity.
It does not increase the table's aggregate capacity. A table provisioned
at 10,000 WCU with a hot partition at 15,000 WCU cannot be fixed by
adaptive capacity — the aggregate (15,000) exceeds provisioned (10,000).

The fix for adaptive capacity lag is either:
- Redesign the partition key to distribute traffic evenly (permanent fix).
- Switch to on-demand mode (on-demand scales per-partition without lag).
- Raise provisioned capacity above the hot partition's peak rate
  (expensive, temporary).

## On-Demand Mode Burst Limit

On-demand mode bills per request without provisioned capacity. However,
it has a per-partition burst limit: 2x the previous 30-minute peak,
ramped over time.

### On-demand throttle scenario

A table in on-demand mode with steady traffic of 1,000 writes/sec per
partition can handle a spike to 2,000 writes/sec on that partition. A
spike to 3,000 writes/sec (3x the previous peak) throttles on that
partition, even though on-mode mode has no table-level provisioned limit.

The fix is the same as provisioned-mode hot partition: redistribute the
key.

## Capacity Planning Heuristics

### Provisioned mode sizing

```
ProvisionedReadCapacityUnits = max(sustained_rcu_rate, p99_rcu_rate / 2)
ProvisionedWriteCapacityUnits = max(sustained_wcu_rate, p99_wcu_rate)
```

For spiky workloads, set provisioned to the 99th percentile to keep burst
in reserve. For steady workloads, set provisioned to the average (burst
is not needed).

### On-demand vs provisioned cost crossover

On-demand costs ~3x provisioned at sustained load. The crossover point
where on-demand becomes cheaper than provisioned is approximately:

```
On-demand cheaper when: p99_rate > 3 × average_rate
```

For workloads where the peak is > 3x the average (spiky), on-demand is
cheaper and simpler. For workloads where peak ≈ average (steady),
provisioned is cheaper.

### GSI capacity planning

In provisioned mode, each GSI has its own `ProvisionedReadCapacityUnits`
and `ProvisionedWriteCapacityUnits`. The GSI's write capacity must cover
the GSI replica cost from base-table writes. The GSI's read capacity must
cover the query load on the GSI.

```
GSI_ProvisionedWriteCapacityUnits ≥ base_write_rate × fraction_of_writes_that_touch_GSI_attributes
GSI_ProvisionedReadCapacityUnits ≥ GSI_query_rate × rcu_per_query
```

Underprovisioning the GSI causes GSI throttling, which propagates to the
base table write path in provisioned mode.
