# Throttling Metrics and Write Sharding Reference

Supplementary reference for the DynamoDB Throttling Optimizer skill.
Loaded on-demand when detailed CloudWatch metrics, write sharding
patterns, BatchWriteItem examples, or exponential backoff code are
needed.

## CloudWatch metrics for throttling analysis

### Required metrics

| Metric | Namespace | What it measures |
|---|---|---|
| `ThrottledRequests` | AWS/DynamoDB | Requests throttled (per table or GSI) |
| `ConsumedReadCapacityUnits` | AWS/DynamoDB | RCU consumed per second |
| `ConsumedWriteCapacityUnits` | AWS/DynamoDB | WCU consumed per second |
| `ReturnedItemCount` | AWS/DynamoDB | Items returned by Query/Scan |
| `BurstCapacityBalance` | AWS/DynamoDB | Remaining burst capacity (percentage) |
| `SystemErrors` | AWS/DynamoDB | DynamoDB service errors (not client errors) |
| `SuccessfulRequestLatency` | AWS/DynamoDB | End-to-end request latency |

### Throttling diagnosis CLI

```bash
# Check ThrottledRequests by table (30-day window)
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -d '-30 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 3600 \
  --statistics Sum --output json

# Check GSI-specific throttling
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=<table> \
               Name=GlobalSecondaryIndexName,Value=<gsi> \
  --start-time $(date -d '-7 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 3600 \
  --statistics Sum --output json

# Check burst capacity balance
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name BurstCapacityBalance \
  --dimensions Name=TableName,Value=<table> \
  --start-time $(date -d '-7 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 300 \
  --statistics Average,Minimum --output json
```

### CloudTrail for hot partition diagnosis

```bash
# Look for write patterns (concentrated keys)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventSource,AttributeValue=dynamodb.amazonaws.com \
  --start-time $(date -d '-1 day' +%FT%TZ) \
  --end-time $(date +%FT%TZ) \
  --max-results 50 \
  --query 'Events[?EventName==`PutItem`||EventName==`UpdateItem`||EventName==`BatchWriteItem`]'
```

## Burst capacity

### How burst capacity works

DynamoDB accumulates unused provisioned throughput (up to 300 seconds)
as a burst bucket. When actual traffic exceeds provisioned, DynamoDB
draws from the burst bucket.

```
burst_bucket_max = 300 × provisioned_wcu
burst_available = min(burst_bucket_max, accumulated_unused)

Example: 1000 WCU provisioned
  burst_bucket_max = 300 × 1000 = 300,000 WCUs
  If unused for 5 minutes: burst_available = 300,000
  Spike of 2000 WCU for 60 seconds: uses 60 × (2000-1000) = 60,000
  Remaining: 300,000 - 60,000 = 240,000 (240 more seconds at 2x)
```

### Burst capacity thresholds

| Burst balance | Risk | Action |
|---|---|---|
| >80% | Low | Monitor |
| 50-80% | Medium | Evaluate capacity headroom |
| 20-50% | High | Increase WCU or switch to on-demand |
| <20% | Critical | Immediate action required |

## Write sharding patterns

### Random suffix strategy

```python
import random

SHARD_COUNT = 10

def get_sharded_key(base_key):
    suffix = str(random.randint(1, SHARD_COUNT)).zfill(2)
    return f"{base_key}#{suffix}"

# Write: pk = "user123#07"
def put_item(table, user_id, data):
    pk = get_sharded_key(user_id)
    table.put_item(Item={'pk': pk, 'data': data})

# Read: fan out across all shards
def get_items(table, user_id):
    import concurrent.futures
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=SHARD_COUNT) as executor:
        futures = []
        for i in range(1, SHARD_COUNT + 1):
            pk = f"{user_id}#{str(i).zfill(2)}"
            futures.append(executor.submit(
                table.get_item, Key={'pk': pk}
            ))
        for f in concurrent.futures.as_completed(futures):
            item = f.result().get('Item')
            if item:
                results.append(item)
    return results
```

### Hash-based suffix strategy (deterministic)

```python
import hashlib

def get_sharded_key_hash(base_key, shard_count=10):
    h = int(hashlib.md5(base_key.encode()).hexdigest(), 16)
    suffix = str(h % shard_count + 1).zfill(2)
    return f"{base_key}#{suffix}"
```

### Write sharding trade-offs

| Factor | Unsharded | Sharded (10 suffixes) |
|---|---|---|
| Write throughput on hot key | 1,000 WCU/partition | 10,000 WCU (10 partitions) |
| Read (single key) | 1 Query | 10 parallel Queries |
| Complexity | Low | Medium (parallel read fan-out) |
| Best for | Even distribution | Known hot keys |

## BatchWriteItem

### Python example

```python
import boto3
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('<table>')

# batch_writer handles chunking (16 items/batch), retries, UnprocessedItems
with table.batch_writer() as batch:
    for item in items:
        batch.put_item(Item=item)
```

### Key facts

- Maximum 16 items per BatchWriteItem request
- Maximum 16 MB total request size
- Consumed WCU is per-item (no savings on consumed capacity)
- Savings: request count, network overhead, client-side latency
- `UnprocessedItems` returned when partition-level throttling occurs
- SDK `batch_writer()` automatically retries `UnprocessedItems`

## Exponential backoff with jitter

### Full jitter pattern

```python
import time
import random
from botocore.exceptions import ClientError

MAX_RETRIES = 10
BASE_DELAY = 0.05  # 50 ms
MAX_DELAY = 5.0    # 5 seconds

def write_with_backoff(write_fn, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return write_fn(*args, **kwargs)
        except ClientError as e:
            if e.response['Error']['Code'] != 'ProvisionedThroughputExceededException':
                raise
            # Full jitter: random between 0 and exponential delay
            delay = min(MAX_DELAY, BASE_DELAY * (2 ** attempt))
            jitter = random.uniform(0, delay)
            time.sleep(jitter)
    raise Exception(f"Max retries ({MAX_RETRIES}) exceeded")
```

### Equal jitter pattern (alternative)

```python
def get_equal_jitter_delay(attempt):
    temp = min(MAX_DELAY, BASE_DELAY * (2 ** attempt))
    return temp / 2 + random.uniform(0, temp / 2)
```

## Capacity mode decision matrix

| Pattern | Mode | Rationale |
|---|---|---|
| Steady, predictable traffic | Provisioned + auto-scaling | Lowest cost |
| Bursty, unpredictable traffic | On-demand | No throttling from capacity |
| Spikes >2x previous peak | Provisioned with headroom | On-demand 2x spike limit |
| Low traffic (<1,000 WCU) | On-demand | Simpler; no auto-scaling config |
| High traffic (>50,000 WCU) | Provisioned | On-demand cost premium too high |
| Mixed (steady + unpredictable) | Provisioned base + on-demand replicas | Cost optimization |

### Switching capacity mode

```bash
# Switch to on-demand
aws dynamodb update-table --table-name <table> \
  --billing-mode PAY_PER_REQUEST

# Switch to provisioned
aws dynamodb update-table --table-name <table> \
  --billing-mode PROVISIONED \
  --provisioned-throughput ReadCapacityUnits=<rcu>,WriteCapacityUnits=<wcu>
```

## GSI distribution analysis

### Diagnosis

```bash
# Check GSI consumed capacity
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ConsumedWriteCapacityUnits \
  --dimensions Name=TableName,Value=<table> \
               Name=GlobalSecondaryIndexName,Value=<gsi> \
  --start-time $(date -d '-7 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 3600 \
  --statistics Average,Maximum --output json
```

### GSI partition key strategies

| Problem | Strategy |
|---|---|
| Low cardinality (<10 values) | Composite key: `status#date` |
| Severe skew (one value dominates) | Write sharding on GSI partition key |
| Full table scan pattern | Redesign GSI or use sparse index |
| GSI backfill causing throttling | Use on-demand temporarily during backfill |

## Partition splitting via write sharding

For known hot keys with sustained write pressure:

1. Choose shard count based on throughput needed (10 shards = 10x capacity)
2. Use random suffix for write distribution
3. Use hash-based suffix for deterministic read routing
4. Backfill existing items with sharded keys
5. Update all read paths to fan out across shards
6. Monitor ThrottledRequests post-migration

The shard count should match the ratio of hot-key write rate to
per-partition throughput limit (approximately 1,000 WCU per partition
for most tables).
