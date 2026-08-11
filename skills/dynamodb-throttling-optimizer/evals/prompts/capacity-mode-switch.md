# Eval prompt: capacity-mode-switch

Optimise the following DynamoDB table for throttling prevention. Walk
the throttling decision framework and emit the standard optimization
block (TARGET, VERDICT, REASON, RECOMMENDATION,
ESTIMATED_THROUGHPUT_IMPACT, MIGRATION_STEPS).

TableName: tbl-capacity-mode-switch
Region: us-east-1
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 2000
  WriteCapacityUnits: 1000
AutoScaling:
  Write: target=70, min=500, max=5000
PartitionKey: session_id (String, UUID — well-distributed)
GSI: none
TTL: enabled (24h expiry)

Metrics (last 30 days):
  - ThrottledRequests: 15,000 (on Write)
  - ConsumedWriteCapacityUnits: avg 800/s, max 4500/s
  - ConsumedReadCapacityUnits: avg 600/s, max 1200/s

Throttling pattern: unpredictable traffic spikes — typically
3-5x normal traffic for 10-15 minutes, several times per day.
Auto-scaling reacts too slowly (minutes). Burst capacity
(300s bucket) exhausted during sustained spikes.

Workload context: session tracking table for a consumer app.
Traffic spikes driven by viral content — unpredictable timing
and magnitude. Partition key (UUID) is well-distributed; the
issue is capacity, not distribution.
