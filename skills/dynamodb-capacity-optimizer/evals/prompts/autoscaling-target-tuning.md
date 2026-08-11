# Eval prompt: autoscaling-target-tuning

Optimise the following DynamoDB table for cost and performance. Walk the
auto-scaling target analysis and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
MIGRATION_STEPS).

TableName: tbl-autoscaling-target-tuning
Region: us-east-1
BillingMode: PROVISIONED
ProvisionedThroughput:
  ReadCapacityUnits: 3000 (current scaled value)
  WriteCapacityUnits: 1500 (current scaled value)
AutoScaling:
  Read: target=90, min=1000, max=5000, ScaleOutCooldown=60
  Write: target=90, min=500, max=3000, ScaleOutCooldown=60
GSIs: 0
TTL: not enabled
Table Class: STANDARD
Streams: disabled
Metrics (last 30 days):
  - ConsumedReadCapacityUnits: avg 2400/s, max 3200/s, p99 2900/s
  - ConsumedWriteCapacityUnits: avg 1200/s, max 1600/s, p99 1450/s
  - ThrottledRequests: 145,000 (on Read), 12,000 (on Write)
  - SystemErrors: 0
Table size: 80 GB
Traffic variability: CV = 0.8 (bursty, latency-sensitive API)

Workload context: real-time API backend for a mobile app. Traffic
spikes during peak hours. Latency SLO: p99 < 50ms. Current throttling
is causing user-visible errors during peak.
