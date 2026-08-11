---
description: Optimise DynamoDB throttling prevention through partition key design (hot partition detection, write sharding with random suffix), burst capacity utilization analysis, adaptive capacity understanding, GSI partition key distribution, write capacity mode selection (provisioned vs on-demand), BatchWriteItem migration (16x throughput), exponential backoff with jitter, and throttling root cause analysis via CloudTrail.
nl_triggers:
  - "prevent DynamoDB throttling"
  - "DynamoDB hot partition"
  - "DynamoDB ThrottledRequests"
  - "DynamoDB write sharding"
  - "DynamoDB burst capacity"
  - "DynamoDB adaptive capacity"
  - "DynamoDB GSI throttling"
  - "DynamoDB BatchWriteItem"
  - "DynamoDB exponential backoff"
  - "DynamoDB ProvisionedThroughputExceededException"
  - "DynamoDB partition key design"
  - "DynamoDB partition splitting"
  - "DynamoDB on-demand vs provisioned"
  - "DynamoDB throttling root cause"
  - "DynamoDB CloudTrail analysis"
  - "DynamoDB conditional writes"
  - "DynamoDB idempotency"
  - "DynamoDB TTL throttling"
routes_to: dynamodb-throttling-optimizer
---

# /aws:optimize-dynamodb-throttling

Activate the `dynamodb-throttling-optimizer` skill and optimize a DynamoDB
table's throttling prevention across eight dimensions: partition key design,
burst capacity, adaptive capacity, GSI distribution, write capacity mode,
batch write API, exponential backoff, and write sharding.

## What it does

Reads a table's CloudWatch metrics (ThrottledRequests,
ConsumedWriteCapacityUnits, ConsumedReadCapacityUnits, BurstCapacityBalance),
table configuration (BillingMode, ProvisionedThroughput, GSIs, partition key),
scaling policies, and CloudTrail events, then applies the ordered optimization
logic:

1. **Pre-flight** — data sufficiency gate. If ThrottledRequests metrics are
   absent, recommends enabling CloudWatch detailed metrics. If zero
   throttling in 30-day window, emits OPTIMIZED.
2. **Partition key design** — detect hot partitions via ThrottledRequests +
   CloudTrail write-pattern analysis. Recommend write sharding (random suffix)
   for high-cardinality hot keys.
3. **Burst capacity** — diagnose intermittent throttling from burst bucket
   exhaustion. Recommend WCU increase or capacity mode switch for sustained
   spikes.
4. **Adaptive capacity** — explain limits; recommend against relying on it
   as a design strategy.
5. **GSI distribution** — check GSI partition key cardinality and skew.
   Recommend composite key or write sharding for low-cardinality GSI keys.
6. **Write capacity mode** — evaluate provisioned vs on-demand for bursty,
   unpredictable traffic patterns.
7. **Batch write API** — migrate high-volume PutItem calls to BatchWriteItem
   (16x request reduction).
8. **Exponential backoff** — ensure client-side retry with jitter is
   configured for ProvisionedThroughputExceededException.
9. **Verdict** — FURTHER_OPTIMIZATION_AVAILABLE (any dimension has a
   recommendation), or OPTIMIZED (no throttling, all dimensions pass).

Emits a deterministic optimization block per table:

```text
TARGET: <table-name>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and supporting data>
RECOMMENDATION:
  Current: <billing-mode>, <WCU>, <partition key>, <GSI status>, <batch status>
  Proposed: <billing-mode>, <WCU>, <partition key>, <GSI status>, <batch status>
  Dimensions changed: <partition_key | burst | gsi | capacity_mode | batch_write | backoff>
  Confidence: <HIGH/MEDIUM/LOW>
ESTIMATED_THROUGHPUT_IMPACT:
  Current throttled requests/day: <count>
  Projected throttled requests/day: <count>
  Throughput improvement: <description>
  Root cause: <hot partition | burst exhaustion | GSI backpressure | insufficient capacity>
MIGRATION_STEPS:
  1. <action with CLI command>
  2. <verification step>
```

## When to invoke

Paste a DynamoDB table's metrics and ask any of:

- "prevent DynamoDB throttling on this table"
- "why is my DynamoDB table throttling?"
- "should I use write sharding?"
- "is my GSI causing throttling?"
- "should I switch DynamoDB to on-demand?"
- "how do I fix ProvisionedThroughputExceededException?"
- "DynamoDB hot partition diagnosis"
- "DynamoDB throttling root cause analysis"

A bare table name + any throttling verb ("fix throttling", "prevent
throttling") also routes here via the orchestrator.

## Inputs

- Table metadata: TableName, BillingMode, ProvisionedThroughput,
  PartitionKey, GSIs, TTL status, AutoScaling policies.
- CloudWatch metrics (last 14-30 days):
  - `ThrottledRequests` (Sum, by table and by GSI)
  - `ConsumedWriteCapacityUnits` (Average, Maximum)
  - `ConsumedReadCapacityUnits` (Average, Maximum)
  - `BurstCapacityBalance` (Average, Minimum)
- Optional: CloudTrail write-pattern analysis for hot partition diagnosis.
- Optional: client-side write patterns (PutItem vs BatchWriteItem, retry
  configuration, connection pool behavior).
- Optional: workload context (write distribution, GSI query patterns,
  traffic variability).

## Outputs

- One optimization block per table.
- Confidence level with rationale (HIGH requires CloudWatch + CloudTrail
  cross-check).
- Estimated throughput impact (throttled requests/day before vs after),
  broken down by root cause.
- Specific migration steps with CLI commands (update-table,
  update-time-to-live, batch_writer code patterns).
- Write sharding pattern with read-complexity warning.
- Capacity mode switch with cost-premium caveat.
- GSI redesign with backfill time estimate.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is the
  Phase 3 Optimize specialist for DynamoDB throttling prevention).
- `/aws:optimize-dynamodb-capacity` for DynamoDB cost optimization
  (on-demand vs provisioned crossover, RCU/WCU sizing, auto-scaling tuning —
  the cost-focused counterpart).
- `/aws:troubleshoot-dynamodb` for DynamoDB functional debugging
  (throttling diagnosis without optimization context, connection errors,
  configuration bugs).
