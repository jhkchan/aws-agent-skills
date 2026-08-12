# Eval prompt: query-monitoring-rule-setup

Optimise the following Redshift cluster's workload management for
throughput protection and runaway query defence. Walk the WLM decision
framework and emit the standard optimization block (TARGET, VERDICT,
REASON, RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterIdentifier: rs-query-monitoring-rule-setup
NodeType: ra3.4xlarge
NumberOfNodes: 4
Region: us-east-1
WLM mode: auto
Concurrency scaling: enabled (auto)
SQA: enabled (max_execution_time: 120)
Query priority: all Normal

Metrics (last 30 days):
  - CPUUtilization avg: 82%, p95: 99%
  - QueryDuration avg: 35 s, p95: 240 s
  - QueryThroughput avg: 18/s
  - WLMQueueLength avg: 3, p99: 15

Top queries (STL_QUERY, last 14 days):
  - Analyst ad-hoc cross-join without filter: avg 300 s, cpu_time 280,000,000,000 µs
  - Analyst full-table scan with SELECT *: avg 180 s, scan_row_count 50,000,000,000
  - Normal workload: avg 8 s, cpu_time 5,000,000,000 µs

STL_QUERY_METRICS:
  - Median cpu_time: 5,000,000,000 µs (5,000 s CPU)
  - p99 cpu_time: 280,000,000,000 µs (56x median)
  - Median query_execution_time: 8,000,000 µs (8 s)
  - p99 query_execution_time: 300,000,000 µs (300 s, 37x median)

Materialized views: 3 (dashboard aggregates, auto-refresh on)
QMR rules: none
AQUA: disabled

Workload context: multi-tenant analytics cluster. Ad-hoc analysts
occasionally submit runaway cross-join queries that monopolize cluster
resources and stall production dashboard queries.
