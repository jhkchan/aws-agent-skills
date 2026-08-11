# Eval prompt: write-sharding-hot-partition

Optimise the following DynamoDB table for throttling prevention. Walk
the throttling decision framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_THROUGHPUT_IMPACT, MIGRATION_STEPS).

TableName: tbl-write-sharding-hot-partition
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
  - ReturnedItemCount: avg 50/query

Throttling pattern: spikes at top-of-hour batch writes (same
user_id values concentrated in few partitions). CloudTrail
analysis confirms 80/20 write skew — top 1% of user_ids
generate 80% of writes.

Workload context: user event tracking table. High-volume writes
from mobile app batch uploads. Writes concentrated on active
users. Reads are key-based lookups by user_id.
