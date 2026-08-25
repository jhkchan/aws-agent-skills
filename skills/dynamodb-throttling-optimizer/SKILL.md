---
name: dynamodb-throttling-optimizer
description: 'Optimises DynamoDB throttling prevention across eight dimensions: partition key design (hot partition detection via CloudWatch ThrottledRequests), burst capacity utilization (300-second burst bucket understanding), adaptive capacity (automatic redistribution, not a design substitute), GSI partition key distribution (hot GSI backpressure), write capacity mode (provisioned vs on-demand for bursty writes), batch write API (BatchWriteItem for 16x throughput), exponential backoff with jitter (ProvisionedThroughputExceededException handling), and write sharding (random suffix for high-cardinality hot keys). Covers conditional writes for idempotency, TTL for data lifecycle, partition splitting, and throttling root cause analysis via CloudTrail.'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted CloudWatch metrics and table configuration. Live-account optimization uses aws dynamodb describe-table, aws dynamodb describe-limits, aws cloudwatch get-metric-statistics (ThrottledRequests, ConsumedReadCapacityUnits, ConsumedWriteCapacityUnits, ReturnedItemCount), aws cloudtrail lookup-events, and aws application-autoscaling describe-scaling-policies (AWS...
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
  when_to_use: Preventing DynamoDB throttling, diagnosing hot partitions via CloudWatch ThrottledRequests, designing write-sharding strategies for high-cardinality keys, evaluating burst capacity utilization, understanding adaptive capacity limits, distributing GSI partition keys, choosing provisioned vs on-demand for bursty writes, implementing BatchWriteItem for throughput, configuring exponential backoff with jitter, or running throttling root cause analysis via CloudTrail.
  when_not_to_use: DynamoDB cost optimization without a throttling focus (use dynamodb-capacity-optimizer), DynamoDB table security or IAM auditing (use dynamodb-table-auditor), or DynamoDB schema design from scratch (use a data modeling specialist). This skill targets throttling prevention and partition-key distribution, not dollar cost or greenfield schema design.
  activation_triggers: prevent DynamoDB throttling, DynamoDB hot partition, DynamoDB ThrottledRequests, DynamoDB write sharding, DynamoDB burst capacity, DynamoDB adaptive capacity, DynamoDB GSI throttling, DynamoDB BatchWriteItem, DynamoDB exponential backoff, DynamoDB ProvisionedThroughputExceededException, DynamoDB partition key design, DynamoDB partition splitting, DynamoDB on-demand vs provisioned, DynamoDB throttling root cause, DynamoDB CloudTrail analysis, DynamoDB conditional writes, DynamoDB idempotency, DynamoDB TTL throttling
  invocation_schema: 'Input: either (a) a table identifier + live-account context, (b) a CloudWatch metrics export (ThrottledRequests, ConsumedWriteCapacityUnits, ConsumedReadCapacityUnits), OR (c) table metadata (TableName, BillingMode, ProvisionedThroughput, GSIs, partition key attribute, TTL status) with observed throttling events. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_THROUGHPUT_IMPACT/MIGRATION_STEPS block per table, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline classification):\nTableName: user-events-prod\nRegion: us-east-1\nBillingMode: PROVISIONED\nProvisionedThroughput:\n  ReadCapacityUnits: 5000\n  WriteCapacityUnits: 3000\nPartitionKey: user_id (String)\nGSI: event-type-index (partition key: event_type)\nTTL: not enabled\nMetrics (last 30 days):\n  - ThrottledRequests: 45,000 (on Write)\n  - ConsumedWriteCapacityUnits: avg 2800/s, max 3500/s\n  - ConsumedReadCapacityUnits: avg 1200/s, max 1800/s\n  - ReturnedItemCount: avg 50/scan\nThrottling pattern: spikes at top-of-hour batch writes (same user_id\n  values concentrated in few partitions)\nEmit the standard optimization block (TARGET, VERDICT, REASON,\nRECOMMENDATION, ESTIMATED_THROUGHPUT_IMPACT, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: DynamoDB, throttling, hot partition, partition key, write sharding, burst capacity, adaptive capacity, GSI, batch write, BatchWriteItem, exponential backoff, jitter, provisioned vs on-demand, ProvisionedThroughputExceededException, ThrottledRequests, ConsumedWriteCapacityUnits, conditional writes, idempotency, TTL, partition splitting, CloudTrail, root cause analysis
  tags: dynamodb, databases, performance, throttling, partition-design, capacity, write-sharding
---

# DynamoDB Throttling Optimizer

## What this skill does

Translates a DynamoDB table's throttling posture into a concrete
prevention recommendation with a throughput-denominated estimated impact.
The verdict is the highest-leverage action across eight dimensions --
partition key design, burst capacity, adaptive capacity, GSI distribution,
write capacity mode, batch write API, exponential backoff, and write
sharding -- applied in priority order. Always pairs the recommendation
with exact CLI commands.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Four headline rules and the throttling formula | First read |
| Mindset | Why partition key design is the #1 lever | Understanding the approach |
| Quick reference -- verdict thresholds | Decision matrix at a glance | Classifying a table |
| Pre-flight data gate | CloudWatch metrics, CloudTrail | Before any recommendation |
| Step 0 non-obvious behaviours | Burst capacity, adaptive capacity, GSI backpressure | Edge cases |
| Step 1 Partition key design | Hot partition detection, write sharding | The headline dimension |
| Step 2 Burst capacity | 300-second burst bucket utilization | Intermittent spikes |
| Step 3 Adaptive capacity | Automatic redistribution limits | Hot partition mitigation |
| Step 4 GSI distribution | Hot GSI partition key backpressure | GSI throttling |
| Step 5 Write capacity mode | Provisioned vs on-demand for bursty writes | Capacity mode decision |
| Step 6 Batch write API | BatchWriteItem for 16x throughput | High-volume writes |
| Step 7 Exponential backoff | ProvisionedThroughputExceededException handling | Client-side retry |
| Step 8 Impact estimation | Throughput math and worked examples | Every recommendation |
| Output format | VERDICT block + worked examples | Emitting the result |
| Anti-Patterns -- NEVER | Common misclassifications | Self-check before emit |
| Pre-flight safety checks | CONFIRM gate, GSI backfill | Before any apply CLI |

## Quick start

- **Partition key design is the #1 lever.** DynamoDB distributes data
  across partitions by partition key. A hot partition key (few distinct
  values, uneven write distribution) causes throttling even when total
  consumed capacity is below provisioned. Write sharding (random suffix)
  spreads writes across partitions.
- **Burst capacity gives a 5-minute window.** DynamoDB accumulates
  unused capacity (up to 300 seconds of provisioned throughput) and
  releases it as burst capacity. Intermittent spikes that fit within
  the burst window do NOT throttle. Sustained spikes beyond burst DO
  throttle.
- **Adaptive capacity is a safety net, not a design substitute.** When
  a hot partition exceeds its share of throughput, DynamoDB temporarily
  redirects unused capacity from cold partitions. This prevents
  immediate throttling but does not fix the underlying distribution
  problem. Rely on write sharding, not adaptive capacity.
- **BatchWriteItem is 16x more efficient than PutItem.** A single
  BatchWriteItem request writes up to 16 items (up to 16 MB) in one
  round trip. This reduces request count, network overhead, and
  consumed capacity per item. For high-volume writes, always use batch.

## Mindset

Throttling optimization is a distribution problem, not a capacity
problem. The goal is the partition-key distribution and write pattern
that minimizes throttling events while preserving the cost envelope --
not simply increasing provisioned throughput to brute-force past the
issue.

Five principles guide every recommendation:

- **Throttling is per-partition, not per-table.** DynamoDB allocates
  throughput proportionally across partitions. A hot partition can
  throttle even when table-level consumed capacity is below provisioned.
  CloudWatch `ThrottledRequests` with a `TableName` dimension shows
  table-level throttling; partition-level diagnosis requires CloudTrail
  or the table's partition key distribution analysis.
- **Burst capacity absorbs intermittent spikes.** DynamoDB accumulates
  up to 300 seconds of unused provisioned throughput as a burst bucket.
  Spikes that fit within the burst window (short duration, within
  accumulated capacity) do NOT throttle. Sustained spikes exhaust burst
  and throttle.
- **Adaptive capacity is reactive, not preventive.** It temporarily
  moves unused capacity from cold partitions to hot ones. This delays
  throttling but does not eliminate it. For sustained hot partitions,
  write sharding is the only durable fix.
- **GSI throttling back-pressures the base table.** If a GSI's partition
  key is hot, the GSI throttles and the base table write also throttles
  (GSI backpressure). GSI partition key design is as important as base
  table partition key design.
- **On-demand mode eliminates provisioned-throughput throttling.** In
  on-demand mode, DynamoDB instantly allocates capacity for any
  sustained throughput up to the previous peak (2x previous peak for
  sudden spikes). On-demand is more expensive but eliminates
  ProvisionedThroughputExceededException for most workloads.

## Quick reference -- verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| ThrottledRequests > 0 AND partition key cardinality is low (hot partition) | **FURTHER_OPTIMIZATION_AVAILABLE** (write sharding) | Step 1 -- add random suffix to partition key |
| ThrottledRequests > 0 AND burst capacity exhausted (sustained spikes > 5 min) | **FURTHER_OPTIMIZATION_AVAILABLE** (capacity mode) | Step 5 -- switch to on-demand OR increase WCU |
| ThrottledRequests > 0 AND GSI partition key is hot (GSI backpressure) | **FURTHER_OPTIMIZATION_AVAILABLE** (GSI design) | Step 4 -- redesign GSI partition key or use sparse index |
| Sustained writes > 1000 items/s AND using PutItem (not BatchWriteItem) | **FURTHER_OPTIMIZATION_AVAILABLE** (batch) | Step 6 -- migrate to BatchWriteItem |
| ThrottledRequests > 0 AND no exponential backoff on client | **FURTHER_OPTIMIZATION_AVAILABLE** (retry) | Step 7 -- implement backoff with jitter |
| BillingMode = PROVISIONED AND throttling on bursty, unpredictable writes | **FURTHER_OPTIMIZATION_AVAILABLE** (capacity mode) | Step 5 -- switch to on-demand |
| ThrottledRequests = 0 AND partition key well-distributed AND batch writes used | **OPTIMIZED** | Emit post-state verification |
| CloudWatch metrics absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day CloudWatch data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Throttling diagnosis requires CloudWatch metrics and table configuration.
Pull these before any recommendation. Full CLI sequences are in
`references/throttling-metrics-and-write-sharding.md`.

**Required data sources** (summarized):
1. Table config: `aws dynamodb describe-table`
2. ThrottledRequests (14-30 day window): `aws cloudwatch get-metric-statistics`
3. ConsumedWriteCapacityUnits, ConsumedReadCapacityUnits
4. GSI configuration: `aws dynamodb describe-table --query 'GlobalSecondaryIndexes'`
5. Scaling policies: `aws application-autoscaling describe-scaling-policies`
6. CloudTrail events for throttling: `aws cloudtrail lookup-events`
7. Account limits: `aws dynamodb describe-limits`

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `ThrottledRequests` Sum = 0 over 14 days | Emit **OPTIMIZED** with note "no throttling observed." |
| `ConsumedWriteCapacityUnits` absent | **NEED_MORE_INFO**. Cannot assess write pressure. |
| Observation window < 14 days | **NEED_MORE_INFO**. Minimum 14 days; 30 days preferred. |
| Table `TableStatus != ACTIVE` | Skip optimization; surface as BLOCKED. |
| GSI `IndexStatus != ACTIVE` (backfilling) | GSI throttling expected during backfill; defer analysis. |

## Process -- Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

- **Burst capacity is NOT infinite.** DynamoDB accumulates up to 300
  seconds of unused provisioned throughput. A spike of 5x provisioned
  for 60 seconds uses 240 seconds of burst (4x60=240). Sustained spikes
  beyond 5 minutes exhaust burst and throttle.
- **Adaptive capacity has a delay.** It activates within seconds of a
  hot partition but the redistribution is temporary (minutes). It does
  not fix sustained hot partitions.
- **GSI backpressure throttles the base table.** If a GSI's partition
  key is hot, writes to the base table throttle even if the base table
  partition key is well-distributed. Always check GSI partition key
  distribution.
- **On-demand has a 2x spike limit.** On-demand instantly doubles the
  previous-peak sustained throughput. A sudden 10x spike beyond previous
  peak can still throttle. For extreme spikes, provisioned with
  auto-scaling headroom may be needed.
- **BatchWriteItem consumes WCU per item, not per request.** 16 items
  in one BatchWriteItem consume the same total WCU as 16 PutItem calls.
  The savings are in request count, network overhead, and client-side
  latency -- not in consumed capacity.
- **Conditional writes reduce wasted capacity.** A conditional
  `PutItem` with `attribute_not_exists(pk)` costs 1 WCU regardless of
  whether the condition matches. If it fails (item exists), the write
  is rejected -- saving downstream processing but not WCU.
- **TTL deletions consume WCU.** TTL-expired items are deleted
  asynchronously, consuming background WCU. Large TTL batches can cause
  throttling on provisioned tables. Stagger TTL or use on-demand.
- **Write sharding changes the partition key.** Adding a random suffix
  (e.g., `user_id#01` through `user_id#10`) spreads writes across 10
  partitions. Reads must aggregate across all suffixes. This is a
  read-write trade-off.
- **DynamoDB Streams can help diagnose throttling.** The stream records
  all writes in near-real-time. Analyzing stream records for write
  patterns can reveal hot partition keys.
- **ProvisionedThroughputExceededException is client-side.** The SDK
  retries automatically with exponential backoff by default, but custom
  retry logic (with jitter) is more effective for sustained throttling.

### Step 1: Partition key design (hot partition detection, write sharding)

Partition key design is the #1 lever because DynamoDB distributes data
and throughput across partitions by partition key value. A hot partition
key (few distinct values, uneven write distribution) causes throttling
even when table-level consumed capacity is below provisioned.

**Hot partition detection:**
```bash
# Check ThrottledRequests by table
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -d '-30 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 3600 \
  --statistics Sum --output json

# Check write distribution via CloudTrail (look for concentrated keys)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=<table> \
  --start-time $(date -d '-1 day' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --max-results 50
```

**Hot partition diagnosis decision tree:**
```
Is ThrottledRequests > 0?
├── NO → No partition-level throttling. Check other dimensions.
└── YES → Is partition key cardinality high (>10,000 distinct values)?
    ├── NO → HOT PARTITION. Apply write sharding (Step 1).
    └── YES → Is write distribution even across keys?
        ├── NO → HOT PARTITION (skewed writes). Apply write sharding.
        └── YES → Check burst capacity exhaustion (Step 2) or GSI (Step 4).
```

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

**Write sharding trade-offs:**

| Factor | Unsharded | Sharded (10 suffixes) |
|---|---|---|
| Write throughput on hot key | 1,000 WCU/partition | 10,000 WCU (10 partitions) |
| Read (single key) | 1 Query | 10 parallel Queries |
| Read (scan by key prefix) | 1 Query | 10 parallel Queries + merge |
| Complexity | Low | Medium (parallel reads) |

Use write sharding ONLY for genuinely hot keys. Over-sharding low-volume
keys adds read complexity without benefit.

### Step 2: Burst capacity utilization

DynamoDB accumulates unused provisioned throughput (up to 300 seconds)
as burst capacity. Understanding burst utilization is key to diagnosing
intermittent throttling.

**Burst capacity math:**
```
burst_bucket_max = 300 seconds × provisioned_wcu
burst_available = min(burst_bucket_max, accumulated_unused_wcu)

Example: 1000 WCU provisioned
  burst_bucket_max = 300 × 1000 = 300,000 WCUs
  A spike of 2000 WCU for 60 seconds uses 60 × (2000-1000) = 60,000 WCUs
  Remaining burst: 300,000 - 60,000 = 240,000 WCUs (sustained for 240 more seconds)
```

**Diagnosis:**

| Pattern | Root cause | Fix |
|---|---|---|
| Throttling only during brief spikes (<5 min) | Burst capacity exhausted | Increase WCU or switch to on-demand |
| Throttling during sustained writes (>5 min) | Provisioned too low | Increase WCU or on-demand |
| No throttling, burst heavily used | Near limit | Monitor closely, pre-provision |

### Step 3: Adaptive capacity understanding

Adaptive capacity automatically redistributes unused throughput from
cold partitions to hot partitions. It is a safety net, not a design fix.

**Key facts:**
- Activates within seconds of a hot partition exceeding its share.
- Redirection is temporary (minutes), not permanent.
- Does NOT prevent throttling for sustained hot partitions.
- No configuration needed -- always on for provisioned tables.

**Anti-pattern:** Designing a table with a known hot partition key and
relying on adaptive capacity to prevent throttling. Adaptive capacity
delays throttling; write sharding (Step 1) fixes it permanently.

### Step 4: GSI partition key distribution

GSI partition key design is as critical as base table partition key
design. A hot GSI partition key causes GSI throttling, which
back-pressures and throttles the base table.

**GSI hot partition diagnosis:**
```bash
# Check if throttling correlates with GSI writes
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table>,Name=GlobalSecondaryIndexName,Value=<gsi> \
  --start-time $(date -d '-7 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 3600 \
  --statistics Sum --output json
```

**GSI optimization strategies:**

| Problem | Fix |
|---|---|
| GSI partition key has low cardinality (e.g., `status` with 3 values) | Use composite key: `status#date` or write sharding |
| GSI is a "full table scan" pattern (all items under one key) | Redesign GSI partition key for distribution |
| GSI backfilling causes throttling | Reduce backfill rate or use on-demand temporarily |
| GSI is sparse but back-pressures base table | Ensure GSI partition key distributes writes evenly |

### Step 5: Write capacity mode (provisioned vs on-demand)

**Capacity mode decision matrix:**

| Pattern | Recommended mode | Rationale |
|---|---|---|
| Steady, predictable traffic | Provisioned + auto-scaling | Lower cost; predictable capacity |
| Bursty, unpredictable traffic | On-demand | No throttling from capacity limits |
| Spikes >2x previous peak | Provisioned with headroom | On-demand 2x spike limit may throttle |
| Low traffic (<1000 WCU sustained) | On-demand | Simpler; no auto-scaling config needed |
| High traffic (>50,000 WCU sustained) | Provisioned | On-demand cost premium too high |

**Switching capacity mode:**
```bash
aws dynamodb update-table --table-name <table> \
  --billing-mode PAY_PER_REQUEST  # or PROVISIONED
```

### Step 6: Batch write API (BatchWriteItem for 16x throughput)

BatchWriteItem writes up to 16 items (up to 16 MB total) in a single
request. This reduces request count, network overhead, and client-side
latency.

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

**Batch vs individual write comparison:**

| Metric | 16x PutItem | 1x BatchWriteItem |
|---|---|---|
| Network round trips | 16 | 1 |
| Consumed WCU | Same | Same (per-item WCU) |
| Client-side latency | 16x RTT | 1x RTT |
| Request count | 16 | 1 |
| Connection pool pressure | High | Low |

**UnprocessedItems handling:** BatchWriteItem may return unprocessed
items (throttled at partition level). The SDK's `batch_writer()`
automatically retries `UnprocessedItems` with exponential backoff.

### Step 7: Exponential backoff with jitter

When `ProvisionedThroughputExceededException` occurs, the client must
retry with exponential backoff and jitter. The AWS SDK retries
automatically by default, but custom retry logic with jitter is more
effective for sustained throttling.

**Backoff with jitter pattern:**
```python
import time
import random

MAX_RETRIES = 10
BASE_DELAY = 0.05  # 50 ms

def write_with_backoff(write_fn, *args):
    for attempt in range(MAX_RETRIES):
        try:
            return write_fn(*args)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ProvisionedThroughputExceededException':
                raise
            # Full jitter: random between 0 and exponential delay
            delay = random.uniform(0, BASE_DELAY * (2 ** attempt))
            time.sleep(delay)
    raise Exception(f"Max retries ({MAX_RETRIES}) exceeded")
```

**Retry best practices:**

| Strategy | When to use |
|---|---|
| SDK default retry (3 attempts) | Low-volume, occasional throttling |
| Custom backoff with jitter (10 attempts) | Sustained throttling, batch workloads |
| Adaptive retry (circuit breaker) | High-volume, latency-sensitive APIs |

### Step 8: Conditional writes and TTL

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

**TTL for data lifecycle:**
```bash
# Enable TTL on an attribute
aws dynamodb update-time-to-live \
  --table-name <table> \
  --time-to-live-specification Enabled=true,AttributeName=ttl

# Set ttl attribute on write: item['ttl'] = int(time.time()) + 86400  # 24h
```

TTL reduces table size over time, which reduces storage cost and scan
time. TTL deletions consume background WCU -- stagger TTL values to
avoid batch-expiry throttling on provisioned tables.

## Configuration dependency graph

```
                ┌──────────────────────────┐
                │ ThrottledRequests > 0?   │
                └────────────┬─────────────┘
                             │
              ┌──────────────┴──────────────┐
              YES                           NO
              │                             │
       ┌──────▼──────┐              ┌───────▼───────┐
       │ Partition   │              │ Batch write   │
       │ key hot?    │              │ used?         │
       └──────┬──────┘              └───────┬───────┘
              │                             │
       ┌──────┴──────┐              ┌───────┴───────┐
      YES          NO              YES             NO
       │            │               │               │
 ┌─────▼─────┐ ┌────▼────┐  ┌───────▼───┐   ┌───────▼───────┐
 │ Write     │ │ GSI     │  │ OPTIMIZED │   │ Check        │
 │ sharding  │ │ hot?    │  │           │   │ capacity     │
 │ (Step 1)  │ └────┬────┘  └───────────┘   │ mode (Step 5)│
 └───────────┘      │                       └──────────────┘
               YES  │  NO
               │    └──→ Burst capacity (Step 2)
         ┌─────▼─────┐
         │ GSI       │
         │ redesign  │
         │ (Step 4)  │
         └───────────┘
```

Decision order: partition key (write sharding) -> GSI distribution ->
burst/capacity mode -> batch write -> exponential backoff.

## Output format

```text
TARGET: <table-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <billing-mode>, <WCU>, <partition key>, <GSI status>, <batch write status>
  Proposed: <billing-mode>, <WCU>, <partition key>, <GSI status>, <batch write status>
  Dimensions changed: <partition_key | burst | adaptive | gsi | capacity_mode | batch_write | backoff>
  Dimensions checked: <list ALL eight, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> -- <one-line rationale>
ESTIMATED_THROUGHPUT_IMPACT:
  Current throttled requests/day: <count>
  Projected throttled requests/day: <count>
  Throughput improvement: <description>
  Root cause: <hot partition | burst exhaustion | GSI backpressure | insufficient capacity>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <table-name> in <region>.
  Proceed? (yes/no)"
```

Full worked examples are in `references/worked-examples.md`.

## STRICT output contract

The rules below are hard constraints. Self-check EVERY emitted block
against these rules before returning. Do NOT substitute markdown headings
or camelCase for the literal labels.

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Projected throttled requests/day` equal to current.** If every
   dimension nets zero improvement, verdict MUST be `OPTIMIZED`.

2. **NEVER recommend write sharding without warning about read
   complexity.** Write sharding adds parallel read overhead. The
   MIGRATION_STEPS MUST note the read pattern change.

3. **NEVER recommend on-demand mode without citing the cost premium.**
   On-demand is significantly more expensive than provisioned for
   steady workloads. Always pair with a cost-justification note.

4. **NEVER recommend BatchWriteItem as a throttling fix without noting
   that consumed WCU is unchanged.** BatchWriteItem reduces request
   count, not consumed capacity. It helps with client-side latency and
   connection pool pressure, not partition-level throttling.

5. **NEVER attribute throttling to insufficient capacity without checking
   partition key distribution.** Throttling is per-partition. A hot
   partition throttles even when table-level consumed < provisioned.
   Always check partition key cardinality and write distribution first.

6. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all eight dimensions.

7. **NEVER emit scratch lines** ("WAIT -- recompute", "Hmm, let me redo")
   in the output.

### Perfect example output -- FURTHER_OPTIMIZATION_AVAILABLE

```text
TARGET: user-events-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: PROVISIONED table with 45,000 ThrottledRequests on Write over 30
  days. Partition key (user_id) has high write skew -- top 1% of user_ids
  generate 80% of writes (detected via CloudTrail). Write sharding with
  random suffix (10 shards) will spread writes across 10 partitions,
  eliminating hot-partition throttling.
RECOMMENDATION:
  Current: PROVISIONED, 3000 WCU, pk=user_id (skewed), 1 GSI, PutItem
  Proposed: PROVISIONED, 3000 WCU, pk=user_id#NN (10 shards), 1 GSI, BatchWriteItem
  Dimensions changed: partition_key (Step 1) + batch_write (Step 6)
  Dimensions checked: partition_key → (shard)  burst ✓  adaptive ✓
    gsi ✓ (well-distributed)  capacity_mode ✓  batch_write → (migrate)
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

**Self-check before emit:**
- [ ] All eight dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] Write sharding recommendation includes read-pattern warning?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete throttling-prevention recommendation. |
| `OPTIMIZED` | All dimensions pass (no throttling, partition keys well-distributed, batch writes used, backoff configured). |
| `NEED_MORE_INFO` | Data gate failed: ThrottledRequests metrics absent, window < 14 days, or CloudTrail unavailable. |
| `BLOCKED` | Hard precondition prevents evaluation: TableStatus != ACTIVE, GSI backfilling. |

## Anti-Patterns -- NEVER (top 5)

1. **NEVER recommend increasing WCU as the first fix for throttling.**
   Throttling is per-partition. A hot partition throttles regardless of
   table-level WCU. Always check partition key distribution first.

2. **NEVER rely on adaptive capacity as a design strategy.** Adaptive
   capacity is a temporary safety net. It delays throttling for minutes;
   it does not fix sustained hot partitions. Write sharding is the
   durable fix.

3. **NEVER recommend on-demand mode without citing the cost premium.**
   On-demand can be 3-5x more expensive than provisioned for steady
   workloads. Always pair with a cost-justification check.

4. **NEVER recommend BatchWriteItem as a partition-level throttling fix.**
   BatchWriteItem reduces request count, not consumed capacity per item.
   It helps with client-side patterns, not partition-level hot-spot
   throttling.

5. **NEVER add a GSI without checking its partition key distribution.**
   A hot GSI partition key causes GSI throttling, which back-pressures
   the base table. GSI partition key design is as important as base
   table partition key design.

Extended anti-patterns in `references/error-handling-and-edge-cases.md`.

## Expert heuristic

DynamoDB throttling optimization follows a clear priority: write
sharding for high-cardinality hot keys (adding a random suffix to the
partition key spreads writes across N partitions, eliminating per-
partition throttling even when the logical key is the same), burst
capacity (the 300-second window absorbs intermittent spikes -- if
throttling only occurs during brief bursts, the table is operating at
the edge of its burst budget, not necessarily under-provisioned), and
adaptive capacity (automatically redirects unused throughput from cold
partitions to hot ones within seconds, but this is a reactive safety net
and not a substitute for proper partition-key design -- sustained hot
partitions will eventually exhaust adaptive capacity and throttle
regardless).

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval.
- **Write sharding changes the partition key.** All reads must be
  updated to fan out across suffixes. Test read paths before deploying.
- **GSI changes require backfill time.** Creating or modifying a GSI
  takes minutes to hours depending on table size. Plan for backfill.
- **Capacity mode switch is instant but has implications.** Provisioned
  to on-demand is instant; on-demand to provisioned requires setting
  WCU/RCU. Test auto-scaling after switching to provisioned.
- **BatchWriteItem migration requires code changes.** Ensure the client
  handles `UnprocessedItems` correctly.
- **TTL activation has a delay.** TTL deletions begin within 48 hours
  of enabling. Stagger TTL values to avoid batch-expiry throttling.
- **Bulk-operation limit:** 5 tables per batch. Sort by ThrottledRequests
  count.

## Recent AWS features (2024-2026)

- **On-demand capacity mode (revised pricing 2024):** Charges per
  request for both read and write. Instant 2x spike capacity beyond
  previous peak.
- **Adaptive capacity (GA since 2019):** Automatic redistribution within
  seconds. No configuration needed.
- **Burst capacity (revised 2024):** 300-second burst bucket. Clearly
  visible in CloudWatch as `BurstCapacityBalance`.
- **DynamoDB Streams enhanced (2024):** Near-real-time write records for
  hot-partition diagnosis.
- **GSI backfill improvements (2025):** Faster GSI creation with
  throttled backfill rate (avoids base-table throttling during creation).
- **CloudTrail Insights for DynamoDB (2025):** Automatic detection of
  unusual write patterns that indicate hot partitions.

## References

- `references/throttling-metrics-and-write-sharding.md` -- CloudWatch
  metrics reference, write sharding patterns, BatchWriteItem examples,
  exponential backoff code, capacity mode decision matrix, GSI
  distribution analysis, partition splitting strategies.
- `references/worked-examples.md` -- write sharding migration, GSI
  redesign, capacity mode switch, batch write migration, already-
  optimized, NEED_MORE_INFO, end-to-end walkthrough.
- `references/error-handling-and-edge-cases.md` -- CLI/data-source
  failure handling, GSI backfill edge cases, TTL batch-expiry
  throttling, extended NEVER list, partition splitting guidance.

## Domain

AWS CloudOps / DynamoDB Throttling Prevention & Partition Key Optimization.

## AWS documentation

- **DynamoDB Developer Guide** -- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Welcome.html
- **DynamoDB partition key design** -- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html
- **DynamoDB burst capacity** -- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/burst-capacity.html
- **DynamoDB adaptive capacity** -- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html#bp-partition-key-adaptive
- **DynamoDB BatchWriteItem** -- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/WorkingWithItems.html#WorkingWithItems.BatchOperations
- **DynamoDB error handling** -- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Programming.Errors.html
- **DynamoDB capacity modes** -- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html
- **DynamoDB GSI** -- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GSI.html
- **DynamoDB TTL** -- https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html
- **AWS CLI DynamoDB reference** -- https://docs.aws.amazon.com/cli/latest/reference/dynamodb/
- **Well-Architected -- Performance Efficiency** -- https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html
