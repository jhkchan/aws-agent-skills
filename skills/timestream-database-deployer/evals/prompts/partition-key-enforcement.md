# Eval: partition-key-enforcement

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — partition key enforcement REQUIRED for query performance on high-cardinality dimension-filtered workload

## Prompt

Create a Timestream database named MetricsDB and table
HighCardinalityMetrics in us-east-1. Memory store TTL 1 hour,
magnetic store TTL 90 days. Enable partition key enforcement
with EnforcementInRecord=REQUIRED. Queries frequently filter by
device_id and region. Tags: Environment=production,
Workload=high-cardinality.
