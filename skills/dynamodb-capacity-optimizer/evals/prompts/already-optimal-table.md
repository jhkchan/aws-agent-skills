# Eval prompt: already-optimal-table

Optimise the following DynamoDB table for cost. Walk the capacity
analysis framework and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

TableName: tbl-already-optimal-table
Region: us-east-1
BillingMode: PAY_PER_REQUEST
GSIs: 1 (gsi-by-status, projection=INCLUDE, 3 attributes, size=8 GB)
TTL: enabled (attribute: expires_at, 30-day expiry)
Table Class: STANDARD
Streams: disabled
Table size: 50 GB (stable — TTL keeps growth flat)
Metrics (last 30 days):
  - ConsumedReadCapacityUnits: avg 500/s, p99 1200/s
  - ConsumedWriteCapacityUnits: avg 200/s, p99 600/s
  - ThrottledRequests: 0
  - SystemErrors: 0
Partition key distribution: uniform (user_id with random suffix)

Workload context: high-traffic API with unpredictable spikes. On-demand
confirmed optimal (consumed > 50% of equivalent provisioned cost during
peak hours). GSI queried 50K/day with only 3 projected attributes.
TTL eliminates 80% of items at 30-day boundary.
