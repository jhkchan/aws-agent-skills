# Eval prompt: materialized-view-for-dashboard

Optimise the following Redshift cluster's workload management for
query throughput and dashboard latency. Walk the WLM decision framework
and emit the standard optimization block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterIdentifier: rs-materialized-view-for-dashboard
NodeType: ra3.16xlarge
NumberOfNodes: 4
Region: us-east-1
WLM mode: auto
Concurrency scaling: enabled (auto)
SQA: enabled (max_execution_time: 120)
Query priority: dashboard = Highest, ETL = Normal

Metrics (last 30 days):
  - CPUUtilization avg: 75%, p95: 85%
  - QueryDuration avg: 28 s, p95: 120 s
  - QueryThroughput avg: 15/s
  - WLMQueueLength avg: 1, p99: 5
  - ConcurrencyScalingClustersActive avg: 0.2

Top queries (SYS_QUERY_HISTORY, last 14 days):
  - Dashboard daily revenue (GROUP BY date, region): 500 executions/day, avg 35 s each
    Query hash: qh_a1b2c3d4, same SQL pattern, scans 12B rows
  - Dashboard weekly summary (GROUP BY week, product): 100/day, avg 45 s
  - ETL MERGE: 10/day, avg 90 s

STL_QUERY_METRICS:
  - Dashboard daily revenue: scan_row_count = 12,000,000,000
  - Dashboard weekly summary: scan_row_count = 12,000,000,000

Materialized views: none
QMR rules: 2 rules (log action, query_execution_time > 300 s)
AQUA: disabled

Workload context: BI dashboard serving executive reports. Same
aggregate queries run every few minutes. Base table (orders) updated
hourly by ETL.
