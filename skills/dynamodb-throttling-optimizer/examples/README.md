# Example usage: dynamodb-throttling-optimizer

A walkthrough showing the skill optimizing a user events table with
severe hot-partition throttling, demonstrating the write sharding
decision, the throughput impact math, and the parallel-read migration.

## Input (user prompt)

> Our user events table is throttling during batch uploads. We have
> 45,000 throttled requests per month and our writes are concentrated
> on active users. Help me prevent the throttling.

```text
TableName: user-events-prod
Region: us-east-1
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 5000
  WriteCapacityUnits: 3000
PartitionKey: user_id (String)
GSI: event-type-index (partition key: event_type, 50 distinct values)
TTL: not enabled

Metrics (last 30 days):
  - ThrottledRequests: 45,000 (on Write)
  - ConsumedWriteCapacityUnits: avg 2800/s, max 3500/s
  - ConsumedReadCapacityUnits: avg 1200/s, max 1800/s

Throttling pattern: spikes at top-of-hour batch writes (same
user_id values concentrated in few partitions). CloudTrail
analysis confirms 80/20 write skew — top 1% of user_ids
generate 80% of writes.

Workload context: user event tracking table. High-volume writes
from mobile app batch uploads. Writes concentrated on active
users. Reads are key-based lookups by user_id.
```

## Skill output

```text
TARGET: user-events-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: PROVISIONED table with 45,000 ThrottledRequests on Write over
  30 days. Partition key (user_id) has severe write skew — top 1% of
  user_ids generate 80% of writes (confirmed via CloudTrail). Write
  sharding with 10 random suffixes will spread writes across 10
  partitions, eliminating hot-partition throttling.
RECOMMENDATION:
  Current: PROVISIONED, 3000 WCU, pk=user_id (80/20 skew), 1 GSI, PutItem
  Proposed: PROVISIONED, 3000 WCU, pk=user_id#NN (10 shards), 1 GSI, BatchWriteItem
  Dimensions changed: partition_key (Step 1) + batch_write (Step 6)
  Dimensions checked: partition_key → (shard)  burst ✓  adaptive ✓
    gsi ✓ (50 values, distributed)  capacity_mode ✓  batch_write → (migrate)
    backoff ✓ (SDK default active)
  Confidence: HIGH — CloudTrail confirms 80/20 write skew on user_id.
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

## What the skill caught that a generic assistant misses

1. **Throttling is per-partition, not per-table.** A generic assistant
   would recommend increasing WCU. The skill diagnoses the root cause
   (hot partition from write skew) and prescribes write sharding instead
   -- eliminating throttling without increasing cost.

2. **Write sharding read-pattern warning.** The skill explicitly warns
   that reads must fan out across all 10 suffixes. A generic assistant
   mentions sharding but ignores the read-path complexity.

3. **BatchWriteItem stacks on top of sharding.** The skill stacks two
   optimizations: write sharding (partition-level fix) + BatchWriteItem
   (request-count reduction). A generic assistant captures only one.

4. **Eight-dimension checklist.** The skill verifies all eight
   dimensions (partition key, burst, adaptive, GSI, capacity mode, batch
   write, backoff, conditional writes) and marks each. A generic
   assistant focuses on one dimension.

5. **CloudTrail as diagnostic evidence.** The skill cites CloudTrail
   confirming the 80/20 write skew. A generic assistant assumes the
   distribution without evidence.

6. **Throughput math is explicit.** The skill shows `1 partition -> 10
   partitions = 10x capacity` so the operator can verify the claim.

## Slash-command invocation

```
/aws:optimize-dynamodb-throttling
```

Or via the orchestrator:

```
/aws:pipeline
You: "prevent DynamoDB throttling on our events table"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: dynamodb-throttling-optimizer]` and
hands off to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After applying write sharding, validate:

```bash
# Confirm ThrottledRequests dropped to 0
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=user-events-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 3600 \
  --statistics Sum --output json

# Check burst capacity recovered
aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB \
  --metric-name BurstCapacityBalance \
  --dimensions Name=TableName,Value=user-events-prod \
  --start-time $(date -d '-7 days' +%FT%TZ) \
  --end-time $(date +%FT%TZ) --period 300 \
  --statistics Average,Minimum --output json
```

If ThrottledRequests persist after sharding, verify:
1. The sharding suffix is applied to ALL write paths (including batch
   upload workers and any async writers).
2. The backfill migration completed for existing items.
3. GSI partition key distribution is also adequate (Step 4).

## Fleet-wide extension

For a fleet of N DynamoDB tables, run the skill in batch mode:

1. Pull all tables with `aws dynamodb list-tables`.
2. For each, pull ThrottledRequests (30-day Sum).
3. Filter to tables with ThrottledRequests > 0.
4. For each throttled table, run the full eight-dimension analysis.
5. Sort by ThrottledRequests count (largest first).
6. Slice into batches of 5 tables.
7. For each batch: emit per-table MIGRATION_STEPS, then a single CONFIRM.
8. Verify each batch before proceeding.
