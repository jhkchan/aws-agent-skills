# Eval prompt: gsi-backpressure-throttling

Optimise the following DynamoDB table for throttling prevention. Walk
the throttling decision framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_THROUGHPUT_IMPACT, MIGRATION_STEPS).

TableName: tbl-gsi-backpressure-throttling
Region: us-east-1
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 10000
  WriteCapacityUnits: 5000
PartitionKey: order_id (String)
GSI: status-index (partition key: status — 3 values: PENDING,
    PROCESSING, COMPLETED)
TTL: not enabled

Metrics (last 30 days):
  - ThrottledRequests: 28,000 (on Write, correlated with GSI)
  - ConsumedWriteCapacityUnits: avg 4200/s, max 4800/s
  - GSI ConsumedWriteCapacityUnits: avg 1800/s, max 2500/s
  - ThrottledRequests (GSI): 22,000

Throttling pattern: GSI throttling dominates (22,000 of 28,000
total). The status-index GSI has only 3 distinct partition key
values. Writes to COMPLETED status (80% of writes) all go to
one GSI partition.

Workload context: order management table. Base table partition
key (order_id) is well-distributed (UUID). GSI partition key
(status) is low-cardinality with severe skew.
