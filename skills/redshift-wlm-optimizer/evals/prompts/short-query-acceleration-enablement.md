# Eval prompt: short-query-acceleration-enablement

Optimise the following Redshift cluster's workload management for
query throughput and isolation. Walk the WLM decision framework and
emit the standard optimization block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterIdentifier: rs-short-query-acceleration-enablement
NodeType: ra3.4xlarge
NumberOfNodes: 6
Region: us-east-1
WLM mode: auto
Concurrency scaling: enabled (auto)
SQA: disabled
Query priority: all Normal

Metrics (last 30 days):
  - CPUUtilization avg: 65%, p95: 78%
  - QueryDuration avg: 12 s, p95: 95 s
  - QueryThroughput avg: 25/s, peak: 35/s
  - WLMQueueLength avg: 2, p99: 8
  - ConcurrencyScalingClustersActive avg: 0.3

Top queries (STL_QUERY, last 7 days):
  - Point lookup by primary key: avg 200 ms, p95 wait 45 s
  - Daily aggregate report: avg 90 s
  - Dashboard drill-down: avg 500 ms, p95 wait 60 s

STL_QUERY_METRICS:
  - Short queries (< 1 s elapsed): 40% of total queries
  - Short queries queue_time p95: 45,000,000 µs (45 s)
  - Long queries (> 60 s elapsed): 15% of total

Materialized views: none
QMR rules: none
AQUA: disabled

Workload context: operational dashboard. Lookups are customer-facing
and latency-sensitive. Aggregates run concurrently. SQA is the missing
isolation layer.
