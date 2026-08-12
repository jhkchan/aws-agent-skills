# Eval prompt: already-optimal-wlm-config

Optimise the following Redshift cluster's workload management. Walk all
WLM optimization dimensions (WLM mode, concurrency scaling, SQA, query
priority, queue rules, memory tuning, QMR, AQUA, materialized views,
Spectrum, COPY) and emit the standard optimization block (TARGET,
VERDICT, REASON, RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS).

ClusterIdentifier: rs-already-optimal-wlm-config
NodeType: ra3.16xlarge
NumberOfNodes: 4
Region: us-east-1
WLM mode: auto
Concurrency scaling: enabled (auto)
SQA: enabled (max_execution_time: 120)
Query priority: dashboard = Highest, ETL = Normal, ad-hoc = Low

Metrics (last 30 days):
  - CPUUtilization avg: 55%, p95: 70%
  - QueryDuration avg: 2.5 s, p95: 8 s
  - QueryThroughput avg: 40/s, peak: 55/s
  - WLMQueueLength avg: 0, p99: 2
  - ConcurrencyScalingClustersActive avg: 0.1 (active < 10 min/day)

Top queries (SYS_QUERY_HISTORY, last 14 days):
  - Dashboard daily revenue (MV hit): avg 300 ms, scans 50K rows from MV
  - Dashboard weekly summary (MV hit): avg 450 ms
  - ETL MERGE: avg 60 s

STL_QUERY_METRICS:
  - Median cpu_time: 1,000,000,000 µs
  - p99 cpu_time: 15,000,000,000 µs (15x median, within QMR threshold)

Materialized views: 4 (dashboard aggregates, auto-refresh on, last refresh < 10 min ago)
QMR rules: 3 rules (action: log, thresholds at 10x median, no aborts triggered)
AQUA: disabled (no LIKE/REGEXP workload pattern — correct skip)

Workload context: well-managed analytics cluster serving executive
dashboards and ETL. All WLM best practices already in place. No
optimization dimension has a positive improvement.
