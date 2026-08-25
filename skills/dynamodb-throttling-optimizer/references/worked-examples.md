# Worked Examples

Full worked examples for the DynamoDB Throttling Optimizer skill. Each
example demonstrates a distinct optimization pattern with verified
throughput math, CLI commands, and rationale.

## Example 1: Write sharding for hot partition

```text
TARGET: user-events-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: PROVISIONED table with 45,000 ThrottledRequests on Write over
  30 days. Partition key (user_id) has severe write skew -- top 1% of
  user_ids generate 80% of writes (confirmed via CloudTrail). Write
  sharding with 10 random suffixes will spread writes across 10
  partitions, eliminating hot-partition throttling.
RECOMMENDATION:
  Current: PROVISIONED, 3000 WCU, pk=user_id (80/20 skew), 1 GSI, PutItem
  Proposed: PROVISIONED, 3000 WCU, pk=user_id#NN (10 shards), 1 GSI, BatchWriteItem
  Dimensions changed: partition_key (Step 1) + batch_write (Step 6)
  Dimensions checked: partition_key → (shard)  burst ✓  adaptive ✓
    gsi → (redesign if needed)  capacity_mode ✓  batch_write → (migrate)
    backoff ✓ (SDK default active)
  Confidence: HIGH -- CloudTrail confirms 80/20 write skew on user_id.
ESTIMATED_THROUGHPUT_IMPACT:
  Current throttled requests/day: 1,500
  Projected throttled requests/day: 0
  Throughput improvement: 10x write capacity on hot keys (1 partition → 10)
  Root cause: hot partition (write skew on user_id)
MIGRATION_STEPS:
  1. Add sharding suffix to partition key on write:
     pk = f"{user_id}#{random.randint(1,10).zfill(2)}"
  2. Update reads to fan out across 10 shards in parallel:
     Query all 10 suffixes, merge results.
  3. Migrate high-volume PutItem calls to BatchWriteItem (16 items/batch):
     with table.batch_writer() as batch: ...
  4. Backfill existing items with sharded keys (one-time migration).
  5. Monitor ThrottledRequests for 7 days post-migration.
CONFIRM: About to apply write sharding (10 suffixes) to user-events-prod
  partition key. Read queries will need parallel fan-out. Proceed? (yes/no)
```

## Example 2: GSI backpressure redesign

```text
TARGET: order-management-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: GSI partition key (status) has only 3 values with severe skew
  (80% of writes go to COMPLETED). GSI throttling (22,000 events)
  back-pressures the base table (28,000 total). Redesign GSI partition
  key to composite key (status#YYYY-MM-DD) distributes writes across
  daily partitions.
RECOMMENDATION:
  Current: PROVISIONED, 5000 WCU, pk=order_id, GSI pk=status (3 values), no batch
  Proposed: PROVISIONED, 5000 WCU, pk=order_id, GSI pk=status#date, BatchWriteItem
  Dimensions changed: gsi (Step 4) + batch_write (Step 6)
  Dimensions checked: partition_key ✓ (UUID, even)  burst ✓  adaptive ✓
    gsi → (redesign)  capacity_mode ✓  batch_write → (migrate)  backoff ✓
  Confidence: HIGH -- GSI throttling dominates (78% of total).
ESTIMATED_THROUGHPUT_IMPACT:
  Current throttled requests/day: 933 (78% from GSI)
  Projected throttled requests/day: 0
  Throughput improvement: GSI partition writes spread across 365 daily
    partitions instead of 3 status values.
  Root cause: GSI hot partition (low-cardinality status key)
MIGRATION_STEPS:
  1. Delete the status-index GSI (or create new composite-key GSI):
     aws dynamodb update-table --table-name order-management-prod
       --delete GlobalSecondaryIndexUpdates '[{Delete:{IndexName:status-index}}]'
  2. Create new GSI with composite partition key:
     aws dynamodb update-table --table-name order-management-prod
       --attribute-definitions '[{AttributeName:status_date,AttributeType:S}]'
       --global-secondary-index-updates '[{Create:{IndexName:status-date-index,
         KeySchema:[{AttributeName:status_date,KeyType:HASH}],
         Projection:{ProjectionType:ALL}}}]'
  3. Update application code to write status_date = "COMPLETED#2026-08-11".
  4. Update GSI queries to use composite key.
  5. Monitor ThrottledRequests for 7 days.
CONFIRM: About to redesign GSI partition key on order-management-prod
  (delete old GSI, create new composite-key GSI). GSI backfill will
  take several minutes. Proceed? (yes/no)
```

## Example 3: Capacity mode switch to on-demand

```text
TARGET: session-tracking-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: PROVISIONED table with 15,000 ThrottledRequests caused by
  unpredictable traffic spikes (3-5x normal, 10-15 min duration).
  Auto-scaling reacts too slowly (minutes). Partition key (UUID) is
  well-distributed -- issue is capacity, not distribution. On-demand
  mode eliminates capacity-based throttling for bursty workloads.
RECOMMENDATION:
  Current: PROVISIONED, 1000 WCU, pk=session_id (UUID), auto-scaling
  Proposed: ON_DEMAND, pk=session_id (UUID)
  Dimensions changed: capacity_mode (Step 5)
  Dimensions checked: partition_key ✓ (UUID, even)  burst → (exhausted)
    adaptive ✓  gsi ✓ (none)  capacity_mode → (switch)  batch_write ✓
    backoff ✓ (SDK default)
  Confidence: HIGH -- partition key is well-distributed; throttling is
    capacity-driven, not distribution-driven.
ESTIMATED_THROUGHPUT_IMPACT:
  Current throttled requests/day: 500
  Projected throttled requests/day: 0
  Throughput improvement: on-demand instantly allocates for any sustained
    throughput up to 2x previous peak.
  Root cause: capacity exhaustion during unpredictable spikes
MIGRATION_STEPS:
  1. Switch to on-demand:
     aws dynamodb update-table --table-name session-tracking-prod
       --billing-mode PAY_PER_REQUEST
  2. Verify mode switch:
     aws dynamodb describe-table --table-name session-tracking-prod
       --query 'Table.BillingModeSummary'
  3. Monitor ThrottledRequests for 7 days (expect 0).
  4. Note: on-demand cost premium applies (~3-5x per-request cost vs
     provisioned for steady workloads). Evaluate cost after 30 days.
CONFIRM: About to switch session-tracking-prod to on-demand capacity
  mode. This eliminates throttling but increases per-request cost.
  Proceed? (yes/no)
```

## Example 4: Already-optimized table

```text
TARGET: iot-telemetry-prod
VERDICT: OPTIMIZED
REASON: PROVISIONED table with zero ThrottledRequests in 30-day window.
  Partition key (device_id UUID) is well-distributed. GSI partition key
  (device_type, 500+ values) is evenly distributed. BatchWriteItem used
  for all writes. Exponential backoff with jitter configured. Burst
  capacity at 85% remaining. No remaining throttling-prevention levers.
RECOMMENDATION:
  Current: PROVISIONED, 4000 WCU, pk=device_id (UUID), 1 GSI (500+ values), batch writes
  Proposed: (no changes -- all dimensions pass)
  Dimensions checked: partition_key ✓  burst ✓ (85%)  adaptive ✓
    gsi ✓  capacity_mode ✓  batch_write ✓  backoff ✓
  Confidence: HIGH -- all eight dimensions verified.
ESTIMATED_THROUGHPUT_IMPACT:
  Current throttled requests/day: 0
  Projected throttled requests/day: 0
  Throughput improvement: n/a (no changes)
  Root cause: n/a
MIGRATION_STEPS:
  (none -- continue monitoring)
CONFIRM: (n/a)
```

## Example 5: Batch write migration

```text
TARGET: event-logging-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: On-demand table with sporadic throttling (3,200 events/month)
  caused by 1,200 individual PutItem calls/second at peak. Connection
  pool exhaustion observed. Partition key (event_id UUID) is well-
  distributed -- issue is request rate, not partition distribution.
  Migrating to BatchWriteItem reduces request count by 16x and
  eliminates connection pool pressure.
RECOMMENDATION:
  Current: ON_DEMAND, pk=event_id (UUID), PutItem (1200/s peak)
  Proposed: ON_DEMAND, pk=event_id (UUID), BatchWriteItem (75 batches/s)
  Dimensions changed: batch_write (Step 6) + backoff (Step 7)
  Dimensions checked: partition_key ✓  burst ✓  adaptive ✓
    gsi ✓ (none)  capacity_mode ✓  batch_write → (migrate)
    backoff → (add custom)
  Confidence: HIGH -- partition key is UUID; issue is client request rate.
ESTIMATED_THROUGHPUT_IMPACT:
  Current throttled requests/day: 107
  Projected throttled requests/day: 0
  Throughput improvement: Request count drops from 1200/s to ~75/s
    (16x reduction). Connection pool pressure eliminated.
  Root cause: client-side request rate pressure (not partition-level)
MIGRATION_STEPS:
  1. Migrate PutItem calls to BatchWriteItem:
     with table.batch_writer() as batch:
         for item in items:
             batch.put_item(Item=item)
  2. Add custom exponential backoff with jitter (max 10 retries):
     Use full-jitter pattern for ProvisionedThroughputExceededException.
  3. Buffer items client-side before batch write (micro-batching):
     Collect 16 items, flush as one BatchWriteItem.
  4. Monitor ThrottledRequests and SDK connection errors for 7 days.
CONFIRM: About to migrate event-logging-prod to BatchWriteItem (code
  change required). Request count drops 16x. Proceed? (yes/no)
```

## Example 6: NEED_MORE_INFO

```text
TARGET: mystery-table-prod
VERDICT: NEED_MORE_INFO
REASON: CloudWatch metrics absent -- ThrottledRequests and
  ConsumedWriteCapacityUnits not available. Observation window is
  3 days (below 14-day minimum). Cannot assess throttling posture.
RECOMMENDATION:
  Current: insufficient data
  Dimensions checked: (cannot evaluate -- data gate failed)
  Confidence: LOW -- no telemetry.
ESTIMATED_THROUGHPUT_IMPACT:
  Current throttled requests/day: unknown
  Projected throttled requests/day: unknown
MIGRATION_STEPS:
  1. Enable CloudWatch detailed metrics for the table.
  2. Collect 14-30 days of ThrottledRequests and ConsumedWriteCapacityUnits.
  3. Re-run throttling optimization analysis.
CONFIRM: (n/a -- read-only recommendation)
```


---

## Step 1: Write sharding (random suffix strategy) (moved from SKILL.md)

**Write sharding (random suffix strategy):**
```python
import random

SHARD_COUNT = 10  # Number of suffixes

def get_sharded_key(base_key):
    """Add random suffix to spread writes across partitions."""
    suffix = str(random.randint(1, SHARD_COUNT)).zfill(2)
    return f"{base_key}#{suffix}"

# Write: pk = "user123#07"
# Read: Query all 10 suffixes in parallel, then merge
```

---

## Step 1: Write sharding trade-offs (moved from SKILL.md)

**Write sharding trade-offs:**

| Factor | Unsharded | Sharded (10 suffixes) |
|---|---|---|
| Write throughput on hot key | 1,000 WCU/partition | 10,000 WCU (10 partitions) |
| Read (single key) | 1 Query | 10 parallel Queries |
| Read (scan by key prefix) | 1 Query | 10 parallel Queries + merge |
| Complexity | Low | Medium (parallel reads) |

---

## Step 2: Burst capacity math (moved from SKILL.md)

**Burst capacity math:**
```
burst_bucket_max = 300 seconds × provisioned_wcu
burst_available = min(burst_bucket_max, accumulated_unused_wcu)

Example: 1000 WCU provisioned
  burst_bucket_max = 300 × 1000 = 300,000 WCUs
  A spike of 2000 WCU for 60 seconds uses 60 × (2000-1000) = 60,000 WCUs
  Remaining burst: 300,000 - 60,000 = 240,000 WCUs (sustained for 240 more seconds)
```

---

## Step 5: Switching capacity mode (moved from SKILL.md)

**Switching capacity mode:**
```bash
aws dynamodb update-table --table-name <table> \
  --billing-mode PAY_PER_REQUEST  # or PROVISIONED
```

---

## Step 6: BatchWriteItem example (moved from SKILL.md)

**BatchWriteItem example:**
```python
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('<table>')

# Process 16 items per batch
with table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)
    # batch_writer handles chunking, retries, and UnprocessedItems
```

---

## Step 6: Batch vs individual write comparison (moved from SKILL.md)

**Batch vs individual write comparison:**

| Metric | 16x PutItem | 1x BatchWriteItem |
|---|---|---|
| Network round trips | 16 | 1 |
| Consumed WCU | Same | Same (per-item WCU) |
| Client-side latency | 16x RTT | 1x RTT |
| Request count | 16 | 1 |
| Connection pool pressure | High | Low |

---

## Step 8: Conditional writes for idempotency (moved from SKILL.md)

**Conditional writes for idempotency:**
```python
# Prevent duplicate writes
table.put_item(
    Item=item,
    ConditionExpression='attribute_not_exists(pk)'
)
# If item exists, ConditionalCheckFailedException -- write rejected
# This prevents duplicates without consuming downstream resources
```

---

## Step 8: TTL for data lifecycle (moved from SKILL.md)

**TTL for data lifecycle:**
```bash
# Enable TTL on an attribute
aws dynamodb update-time-to-live \
  --table-name <table> \
  --time-to-live-specification Enabled=true,AttributeName=ttl

# Set ttl attribute on write: item['ttl'] = int(time.time()) + 86400  # 24h
```
