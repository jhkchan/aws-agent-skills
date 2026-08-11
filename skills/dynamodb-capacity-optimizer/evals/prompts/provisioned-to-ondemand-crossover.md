# Eval prompt: provisioned-to-ondemand-crossover

Optimise the following DynamoDB table for cost. Walk the capacity-mode
crossover analysis and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS, MIGRATION_STEPS).

TableName: tbl-provisioned-to-ondemand-crossover
Region: us-east-1
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 5000
  WriteCapacityUnits: 2000
AutoScaling:
  Read: target=70, min=5000, max=5000 (static, no scaling range)
  Write: target=70, min=2000, max=2000 (static, no scaling range)
GSIs: 1 (projected size: 20 GB, KEYS_ONLY)
TTL: not enabled
Table Class: STANDARD
Streams: disabled
Metrics (last 30 days):
  - ConsumedReadCapacityUnits: avg 750/s, max 1100/s, p99 980/s
  - ConsumedWriteCapacityUnits: avg 300/s, max 450/s, p99 420/s
  - ThrottledRequests: 0
  - SystemErrors: 0
Table size: 150 GB

Workload context: batch report generator triggered by scheduled jobs.
Traffic is sporadic — bursts every 4 hours for 30 minutes, idle in
between. No latency-sensitive queries.
