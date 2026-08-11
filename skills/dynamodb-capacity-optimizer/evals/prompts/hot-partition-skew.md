# Eval prompt: hot-partition-skew

Optimise the following DynamoDB table for cost and performance. Walk the
partition skew analysis and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

TableName: tbl-hot-partition-skew
Region: us-east-1
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 5000
  WriteCapacityUnits: 3000
AutoScaling: disabled (static provisioning)
GSIs: 0
TTL: not enabled
Table Class: STANDARD
Streams: disabled
Metrics (last 30 days):
  - ConsumedReadCapacityUnits: avg 1800/s (36% of provisioned)
  - ConsumedWriteCapacityUnits: avg 1200/s (40% of provisioned)
  - ThrottledRequests: 890,000 (significant, on both Read and Write)
  - SystemErrors: 0
Partition key: "status" with values: "active" (80% of items),
"pending" (15%), "completed" (5%)
Table size: 120 GB

Workload context: order processing table. Partition key is "status"
which creates extreme skew — nearly all traffic goes to the "active"
partition. The table is provisioned at 5000 RCU / 3000 WCU but is
throttling despite only consuming 36-40% because the "active" partition
is saturated.
