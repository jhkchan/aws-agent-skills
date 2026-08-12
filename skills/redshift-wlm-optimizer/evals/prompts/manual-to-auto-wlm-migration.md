# Eval prompt: manual-to-auto-wlm-migration

Optimise the following Redshift cluster's workload management for
query throughput and isolation. Walk the WLM decision framework and
emit the standard optimization block (TARGET, VERDICT, REASON,
RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterIdentifier: rs-manual-to-auto-wlm-migration
NodeType: ra3.16xlarge
NumberOfNodes: 4
Region: us-east-1
WLM mode: manual (3 static queues)
Concurrency scaling: disabled
SQA: disabled
Query priority: all Normal

Metrics (last 30 days):
  - CPUUtilization avg: 88%, p95: 97%
  - QueryDuration avg: 45 s, p95: 180 s
  - QueryThroughput avg: 12/s, peak: 18/s
  - WLMQueueLength avg: 4, p99: 22
  - ConcurrencyScalingClustersActive: 0

Top queries (STL_QUERY, last 7 days):
  - Dashboard aggregate (4 joins, GROUP BY date): avg 35 s, 12B row scan
  - Single-row lookup by primary key: avg 200 ms
  - ETL MERGE into fact table: avg 120 s

Materialized views: none
QMR rules: none
AQUA: disabled

Workload context: mixed — dashboard lookups (short) competing with ETL
aggregates (long) in the same queue. Customer-facing dashboards stall
during evening peak when ETL runs.
