# Worked Examples, Edge Cases, and Extended Anti-Patterns — Redshift WLM Optimizer

Full worked examples, CLI failure handling, operational edge cases, and
the extended NEVER list. Loaded on demand — kept out of the main
SKILL.md body so the procedure stays scannable.

## Worked example — manual to auto WLM migration (headline case)

```text
TARGET: analytics-cluster-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster is on manual WLM with 3 static queues, SQA disabled,
  concurrency scaling disabled. WLMQueueLength p99 = 22 indicates
  sustained queue stalls. Auto WLM + concurrency scaling adapts
  dynamically to the mixed short/long query workload; SQA isolates
  the 200 ms dashboard lookups from 30-minute aggregates.
RECOMMENDATION:
  Current: manual WLM, 3 queues, concurrency scaling off, SQA off,
    0 materialized views, 0 QMR rules
  Proposed: auto WLM, 3 priority queues, concurrency scaling auto,
    SQA on (120 s threshold), 0 QMR rules (add in follow-up)
  Dimensions changed: wlm_mode + concurrency_scaling + sqa + priority
  Dimensions checked: wlm_mode → (switch to auto)  concurrency_scaling →
    (enable)  sqa → (enable)  priority → (set dashboard=Highest)
    memory_tuning ✓ (auto WLM handles)  qmr ✓ (no runaway pattern observed)
    aqua ✓ (no LIKE/REGEXP pattern)  materialized_views ✓ (follow-up)
    spectrum ✓ (no external tables)  copy ✓ (no COPY issues)
  Confidence: HIGH — WLMQueueLength p99 = 22 and STL_QUERY confirms
    mixed short/long workload; auto WLM + SQA + concurrency scaling is
    the canonical recommendation for this pattern.
ESTIMATED_IMPACT:
  Current throughput: 12 queries/sec, p95 wait 180 s
  Projected throughput: 42 queries/sec, p95 wait <10 s
  Throughput improvement: 250%
  Monthly concurrency-scaling cost delta: +$185.00
    (estimated 90 active minutes/day × 30 days × $0.0686/min/node-group)
  Net monthly cost impact: +$185.00 (throughput-driven; replaces need
    for cluster resize which would cost +$2,400/month)
  Assumptions: 4-node ra3.16xlarge, us-east-1 pricing, peak hours
    4-8 hours/day.
MIGRATION_STEPS:
  1. Snapshot the cluster:
     aws redshift create-cluster-snapshot --cluster-identifier analytics-cluster-prod --snapshot-identifier pre-wlm-20260805
  2. Apply auto WLM + concurrency scaling + SQA via parameter group:
     aws redshift modify-cluster-parameter-groups --parameter-group-name <group> --parameters \
       ParameterName=auto_wlm,ParameterValue=true \
       ParameterName=wlm_json_configuration,ParameterValue='[{"auto_wlm":true,"concurrency_scaling":"auto","short_query_queue_enable":true,"max_execution_time":120,"queue_name":"main"}]'
  3. Apply to cluster:
     aws redshift modify-cluster --cluster-identifier analytics-cluster-prod --cluster-parameter-group-name <group>
  4. Monitor WLMQueueLength and ConcurrencyScalingClustersActive for 7 days.
CONFIRM: About to modify-cluster on analytics-cluster-prod (manual WLM
  → auto WLM + concurrency scaling + SQA). Throughput ~250% at peak;
  concurrency-scaling cost +$185/month. Proceed? (yes/no)
```

## Worked example — SQA enablement

```text
TARGET: ops-dashboard-cluster
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster has auto WLM and concurrency scaling, but SQA is
  disabled. STL_QUERY_METRICS shows 40% of queries complete in < 1 s
  but spend 45 s in queue behind long aggregates. SQA with
  max_execution_time=120 isolates the short lookups.
RECOMMENDATION:
  Current: auto WLM, concurrency scaling on, SQA off, all Normal priority
  Proposed: auto WLM, concurrency scaling on, SQA on (120 s), priority
    set for dashboard = Highest
  Dimensions changed: sqa + priority
  Dimensions checked: wlm_mode ✓ (already auto)  concurrency_scaling ✓
    (already on)  sqa → (enable)  priority → (set dashboard=Highest)
    memory_tuning ✓  qmr ✓  aqua ✓  materialized_views ✓ (follow-up)
    spectrum ✓  copy ✓
  Confidence: HIGH — STL_QUERY_METRICS confirms 40% short queries with
    45 s queue time; SQA threshold of 120 s covers p95 short-query
    elapsed time × 2.
ESTIMATED_IMPACT:
  Current throughput: 25 queries/sec, p95 wait 45 s (short queries)
  Projected throughput: 35 queries/sec, p95 wait <2 s (short queries)
  Throughput improvement: 40% overall; 95% latency improvement for short
  Monthly concurrency-scaling cost delta: +$20.00 (slight increase from
    reduced queue stalls triggering scaling less often — net positive)
  Net monthly cost impact: +$0 (cost-neutral; SQA has no direct charge)
  Assumptions: 6-node ra3.4xlarge, us-east-1 pricing.
MIGRATION_STEPS:
  1. Snapshot the cluster.
  2. Update WLM JSON to enable SQA:
     ParameterName=wlm_json_configuration,ParameterValue='[{"auto_wlm":true,"concurrency_scaling":"auto","short_query_queue_enable":true,"max_execution_time":120,"queue_name":"main"}]'
  3. Monitor STL_QUERY_METRICS queue_time for short queries over 7 days.
CONFIRM: About to enable SQA on ops-dashboard-cluster. Short-query
  latency improvement ~95%. Proceed? (yes/no)
```

## Worked example — materialized views for dashboards

```text
TARGET: bi-dashboard-cluster
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Dashboard daily revenue query (GROUP BY date, region) runs 500
  times/day scanning 12B rows each, averaging 35 s. The same query
  pattern repeats because the base table updates hourly. A materialized
  view with auto-refresh converts each 35 s aggregate into a sub-second
  lookup.
RECOMMENDATION:
  Current: auto WLM, scaling on, SQA on, 0 materialized views
  Proposed: auto WLM, scaling on, SQA on, 2 materialized views with
    auto-refresh
  Dimensions changed: materialized_views
  Dimensions checked: wlm_mode ✓  concurrency_scaling ✓  sqa ✓  priority ✓
    memory_tuning ✓  qmr ✓  aqua ✓  materialized_views → (add 2 MVs)
    spectrum ✓  copy ✓
  Confidence: HIGH — SYS_QUERY_HISTORY confirms same query hash 500x/day;
    base table updates hourly so auto-refresh at 15-minute interval is
    sufficient for freshness.
ESTIMATED_IMPACT:
  Current throughput: 15 queries/sec; dashboard query avg 35 s
  Projected throughput: 30 queries/sec; dashboard query avg <1 s (MV hit)
  Throughput improvement: 100% overall; 97% dashboard latency improvement
  Monthly concurrency-scaling cost delta: -$50.00 (fewer scaling triggers
    from dashboard backlog)
  Net monthly cost impact: -$50.00 (cost-saving)
  Assumptions: MV refresh every 15 minutes = 96 refreshes/day, each
    <5 s incremental compute. Base table (orders) updated hourly.
MIGRATION_STEPS:
  1. Create materialized views:
     CREATE MATERIALIZED VIEW dashboard_daily_revenue AS
       SELECT DATE_TRUNC('day', order_date) AS day, region, SUM(revenue) AS revenue
       FROM orders GROUP BY 1, 2;
     CREATE MATERIALIZED VIEW dashboard_weekly_summary AS
       SELECT DATE_TRUNC('week', order_date) AS week, product, SUM(quantity) AS qty
       FROM orders GROUP BY 1, 2;
  2. Enable auto-refresh:
     ALTER MATERIALIZED VIEW dashboard_daily_revenue AUTO REFRESH YES;
     ALTER MATERIALIZED VIEW dashboard_weekly_summary AUTO REFRESH YES;
  3. Verify refresh via SYS_MV_REFRESH_HISTORY after 15 minutes.
CONFIRM: About to create 2 materialized views with auto-refresh on
  bi-dashboard-cluster. Dashboard latency drops from 35 s to <1 s.
  Proceed? (yes/no)
```

## Worked example — QMR setup (log first, then promote to abort)

```text
TARGET: multi-tenant-analytics
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: No QMR rules configured. STL_QUERY_METRICS shows p99 cpu_time
  at 56x median (runaway analyst cross-joins). Adding QMR log rules at
  10x median thresholds captures runaway queries without risk of
  aborting legitimate workloads.
RECOMMENDATION:
  Current: auto WLM, scaling on, SQA on, 0 QMR rules
  Proposed: auto WLM, scaling on, SQA on, 3 QMR log rules (10x median)
  Dimensions changed: qmr
  Dimensions checked: wlm_mode ✓  concurrency_scaling ✓  sqa ✓  priority ✓
    memory_tuning ✓  qmr → (add 3 log rules)  aqua ✓  materialized_views ✓
    spectrum ✓  copy ✓
  Confidence: HIGH — STL_QUERY_METRICS median cpu_time = 5,000,000,000 µs;
    10x threshold = 50,000,000,000 µs. p99 at 280,000,000,000 µs clearly
    exceeds threshold. Log action validates before promoting to abort.
ESTIMATED_IMPACT:
  Current throughput: 18 queries/sec, p95 duration 240 s (runaway impact)
  Projected throughput: 25 queries/sec, p95 duration 30 s (after log
    visibility drives analyst behaviour change; abort promotion further
    reduces impact)
  Throughput improvement: 39% overall; 87% p95 duration reduction
  Monthly concurrency-scaling cost delta: -$80.00 (fewer scaling triggers)
  Net monthly cost impact: -$80.00
  Assumptions: log rules surface runaway queries; analysts self-correct
    within 7 days; promote to abort after validation.
MIGRATION_STEPS:
  1. Add QMR log rules in WLM JSON:
     [{"rule_name":"high-cpu-log","predicate":"cpu_time > 50000000000","action":"log"},
      {"rule_name":"long-exec-log","predicate":"query_execution_time > 80000000","action":"log"},
      {"rule_name":"scan-spill-log","predicate":"scan_row_count > 50000000000","action":"log"}]
  2. Review STL_QUERY_METRICS_HISTORY for 7 days.
  3. If thresholds validated, promote "high-cpu-log" to action: abort.
CONFIRM: About to add 3 QMR log rules on multi-tenant-analytics.
  No queries will be aborted during validation period. Proceed? (yes/no)
```

## Worked example — already optimal

```text
TARGET: well-managed-cluster
VERDICT: OPTIMIZED
REASON: Cluster is on auto WLM with concurrency scaling, SQA enabled
  (120 s), 4 materialized views with auto-refresh, 3 QMR log rules at
  10x median, priority routing (dashboard=Highest). WLMQueueLength p99
  = 2, CPUUtilization p95 = 70%. No optimization dimension has a
  positive improvement.
RECOMMENDATION:
  Current: auto WLM, scaling on, SQA on, 4 MVs, 3 QMR rules — no change
  Dimensions checked: wlm_mode ✓  concurrency_scaling ✓  sqa ✓  priority ✓
    memory_tuning ✓  qmr ✓  aqua ✓ (no LIKE/REGEXP pattern — correct skip)
    materialized_views ✓ (4 MVs, auto-refresh < 10 min)  spectrum ✓  copy ✓
  Confidence: HIGH — all eleven dimensions verified; SYS_QUERY_HISTORY
    confirms MV hit rate >95% for dashboard queries; QMR rules validated.
ESTIMATED_IMPACT:
  Current throughput: 40 queries/sec, p95 wait <2 s
  Monthly concurrency-scaling cost: <$30/month (active <10 min/day)
  No improvement available.
MIGRATION_STEPS:
  - None required. Re-evaluate if workload pattern changes or at
    quarterly review.
```

## Worked example — NEED_MORE_INFO

```text
TARGET: new-cluster-untested
VERDICT: NEED_MORE_INFO
REASON: SYS_QUERY_HISTORY is empty over the requested 14-day window.
  The cluster was created 3 days ago and has not received production
  traffic. Cannot evaluate WLM configuration without baseline query
  patterns.
RECOMMENDATION:
  Current: auto WLM (default), scaling on, SQA on — pending data
  Proposed: pending baseline data
  Confidence: LOW — no query history to evaluate.
ESTIMATED_IMPACT:
  Monthly: $0 (cannot quantify without baseline)
MIGRATION_STEPS:
  1. Verify the cluster is receiving traffic:
     aws redshift-data execute-statement --cluster-identifier new-cluster-untested \
       --sql "SELECT COUNT(*) FROM SYS_QUERY_HISTORY WHERE start_time > GETDATE() - 7"
  2. Wait 14-30 days for representative observation.
  3. Re-evaluate with STL_QUERY + SYS_QUERY_HISTORY data.
  Do NOT optimize based on assumed workload patterns.
```

## CLI and data-source failure handling

### CloudWatch metric failures

| Failure mode | Detection | Handling |
|---|---|---|
| `get-metric-statistics` returns empty for WLMQueueLength | `len(Datapoints) == 0` | Verdict: NEED_MORE_INFO. Cluster may be dormant or IAM denies cloudwatch:GetMetricStatistics. |
| `ConcurrencyScalingClustersActive` absent | Metric not listed | Concurrency scaling not enabled. Confirm via WLM JSON. |

### Redshift API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `describe-clusters` returns `ClusterNotFound` | API error | Cluster does not exist in this region. Skip entirely. |
| `modify-cluster` fails with `InvalidClusterState` | API error | Cluster is in maintenance or resizing. Wait for `ClusterStatus == available`, retry. |
| WLM JSON validation fails with `InvalidParameterValue` | API error | JSON schema error. Validate `memory_percent` sums to 100, queue names unique. |
| `modify-cluster` for AQUA fails with `UnsupportedOperation` | API error | Node type does not support AQUA. Only ra3.16xlarge and ra3.4xlarge supported. |

### Data API failures

| Failure mode | Detection | Handling |
|---|---|---|
| `execute-statement` returns `ValidationException` | API error | Database name or credentials wrong. Verify `--database` and `--db-user` / secret ARN. |
| STL_QUERY returns empty | `len(Records) == 0` | Either no queries in window or STL retention elapsed (STL tables retain ~7 days of logs). |

## Operational edge cases

### Cluster in maintenance window

**Detection:** `describe-clusters` shows `ClusterStatus == modifying` or
`AvailabilityStatus == Maintenance`.

**Action:** Surface as BLOCKED. WLM parameter-group changes queue but do
not apply until maintenance completes. Reschedule optimization after
maintenance.

### Serverless cluster (different config surface)

**Detection:** `describe-clusters` returns `ClusterNotFound` but
`redshift-serverless:describe-workgroups` finds the workgroup.

**Action:** Surface as scope mismatch. Redshift Serverless uses RPU-based
capacity, not WLM queues. Recommend the Serverless capacity tuning skill.

### STL_QUERY retention exceeded

**Detection:** STL_QUERY returns rows only for last 2-3 days despite
requesting 14-day window.

**Action:** STL system tables retain ~7 days of logs. Use
SYS_QUERY_HISTORY for longer retention (up to 30 days accessible via
SYS_QUERY_HISTORY). If SYS_QUERY_HISTORY also insufficient, fall back
to CloudWatch metrics only with MEDIUM confidence.

## Extended NEVER list (supplementary anti-patterns)

- NEVER set QMR action to `abort` on the first pass. Always run with
  `log` for 7 days to validate thresholds against false positives.

- NEVER enable AQUA on a cluster with no LIKE/REGEXP/hash-join-on-VARCHAR
  workload. AQUA adds overhead for no benefit on numeric aggregation.

- NEVER create a materialized view without auto-refresh unless the
  workload tolerates stale data. A stale MV silently returns wrong
  results.

- NEVER assume concurrency scaling eliminates the need for cluster
  resize. If ConcurrencyScalingClustersActive > 60 minutes/day sustained,
  the base cluster is undersized — resize, don't rely on scaling.

- NEVER change `max_execution_time` for SQA to > 300 s. SQA is for SHORT
  queries; > 300 s defeats the purpose.

- NEVER set all queues to `priority: highest`. Priority is relative;
  if everything is highest, nothing is.

- NEVER use `COMPUPDATE ON` for incremental loads on tables with
  established encodings. It recomputes encoding, wasting compute.

- NEVER rely on STL_QUERY for > 7-day history. Use SYS_QUERY_HISTORY
  for 14-30 day analysis.

- NEVER modify the WLM parameter group without first snapshotting the
  cluster. WLM changes affect the next query immediately.

- NEVER recommend concurrency scaling for a cluster where
  WLMQueueLength p99 < 5 consistently. The scaling cluster will never
  activate; the recommendation adds noise.

## Production edge cases

### Concurrency scaling cost spike

**Scenario:** ConcurrencyScalingClustersActive averages 3+ hours/day.

**Problem:** Cost = 3h × 30 days × $12.096/h (ra3.16xlarge) = $1,088/month
on scaling alone.

**Resolution:**
1. Check WLMQueueLength trend. If consistently > 10, the base cluster is
   undersized. Resize (add nodes) instead of relying on scaling.
2. If queue stalls are caused by one runaway query pattern, fix with QMR
   rules (Step 6) instead of scaling.
3. If workload is genuinely bursty (predictable peaks), accept the
   scaling cost as cheaper than a permanent resize.

### Materialized view refresh failure

**Scenario:** SYS_MV_REFRESH_HISTORY shows refresh failures or stalls.

**Detection:**
```sql
SELECT * FROM sys_mv_refresh_history
WHERE state != 'success'
ORDER BY start_time DESC LIMIT 20;
```

**Resolution:**
1. Check if base table has locks preventing refresh.
2. Check if the refresh query itself is hitting QMR abort rules.
3. Consider staggering MV refresh schedules to avoid concurrent refresh
   contention.
