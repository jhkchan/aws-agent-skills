# Eval prompt: batch-write-migration

Optimise the following DynamoDB table for throttling prevention. Walk
the throttling decision framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_THROUGHPUT_IMPACT, MIGRATION_STEPS).

TableName: tbl-batch-write-migration
Region: us-east-1
BillingMode: ON_DEMAND
PartitionKey: event_id (String, UUID — well-distributed)
GSI: none
TTL: not enabled

Metrics (last 30 days):
  - ThrottledRequests: 3,200 (sporadic, during write bursts)
  - ConsumedWriteCapacityUnits: avg 1200/s, max 3500/s
  - ConsumedReadCapacityUnits: avg 200/s

Client patterns:
  - Writes use individual PutItem calls
  - Write rate: ~1,200 items/second at peak
  - Connection pool exhaustion observed at peak (SDK errors)
  - No batch writes implemented
  - No exponential backoff configured

Throttling pattern: sporadic throttling during write bursts.
Root cause is request-rate pressure (1,200 individual PutItem
calls/second), not partition-level hot spots. Partition key is
well-distributed UUID.

Workload context: event logging service on on-demand mode.
High volume of small writes from application servers. Each
PutItem is a single item (~500 bytes).
