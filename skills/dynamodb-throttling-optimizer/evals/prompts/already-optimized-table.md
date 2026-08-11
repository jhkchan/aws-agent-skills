# Eval prompt: already-optimized-table

Optimise the following DynamoDB table for throttling prevention. Walk
the throttling decision framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_THROUGHPUT_IMPACT, MIGRATION_STEPS).

TableName: tbl-already-optimized-table
Region: us-east-1
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 8000
  WriteCapacityUnits: 4000
AutoScaling:
  Read: target=70, min=2000, max=20000
  Write: target=70, min=1000, max=10000
PartitionKey: device_id (String, UUID — well-distributed)
GSI: device-type-index (partition key: device_type — 500+ values,
    evenly distributed)
TTL: enabled (7-day expiry, staggered)

Metrics (last 30 days):
  - ThrottledRequests: 0
  - ConsumedWriteCapacityUnits: avg 3200/s, max 3800/s
  - ConsumedReadCapacityUnits: avg 6500/s, max 7500/s
  - BurstCapacityBalance: avg 85% remaining

Client patterns:
  - Writes use BatchWriteItem (16 items/batch)
  - Exponential backoff with jitter configured (max 10 retries)
  - Conditional writes for idempotency on high-volume paths

Workload context: IoT telemetry ingestion. Partition key is UUID
(high cardinality, even distribution). GSI partition key has 500+
values, well-distributed. Batch writes from ingestion workers.
No throttling observed in 30-day window.
