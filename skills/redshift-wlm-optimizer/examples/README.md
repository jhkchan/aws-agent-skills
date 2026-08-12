# Example usage: redshift-wlm-optimizer

A walkthrough showing the skill optimizing a mixed-workload Redshift
cluster running legacy manual WLM, demonstrating the auto WLM + concurrency
scaling migration, SQA enablement, priority queue setup, and the
throughput improvement math.

## Input (user prompt)

> Review our Redshift analytics cluster before the Q4 FinOps review.
> Dashboard queries are stalling during the evening peak when ETL runs.
> Help me optimize the WLM configuration.

```text
ClusterIdentifier: analytics-cluster-prod
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
```

## Skill output

```text
TARGET: analytics-cluster-prod
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Cluster is on manual WLM with 3 static queues, SQA disabled,
  concurrency scaling disabled. WLMQueueLength p99 = 22 indicates
  sustained queue stalls. Auto WLM + concurrency scaling adapts
  dynamically to the mixed short/long query workload; SQA isolates
  the 200 ms dashboard lookups from 30-minute aggregates. Combined
  throughput improvement ~3.5x at peak with sub-5% concurrency-scaling
  cost.
RECOMMENDATION:
  Current: manual WLM, 3 queues, concurrency scaling off, SQA off,
    0 materialized views, 0 QMR rules
  Proposed: auto WLM, 4 priority queues, concurrency scaling auto,
    SQA on (120 s threshold), 2 materialized views, 3 QMR log rules
  Dimensions changed: wlm_mode + concurrency_scaling + sqa + priority +
    materialized_views + qmr
  Dimensions checked: wlm_mode → (switch to auto)  concurrency_scaling →
    (enable)  sqa → (enable)  priority → (set dashboard=Highest)
    memory_tuning ✓ (auto WLM handles)  qmr → (add 3 rules)  aqua ✓
    (no LIKE/REGEXP pattern)  materialized_views → (add 2 MVs)
    spectrum ✓ (no external tables)  copy ✓ (no COPY issues)
  Confidence: HIGH — WLMQueueLength p99 = 22 and STL_QUERY confirms
    mixed short/long workload; auto WLM + SQA + concurrency scaling is
    the canonical recommendation for this pattern.
ESTIMATED_IMPACT:
  Current throughput: 12 queries/sec, p95 wait 180 s
  Projected throughput: 42 queries/sec, p95 wait <10 s
  Throughput improvement: 250% (12 → 42 queries/sec)
  Monthly concurrency-scaling cost delta: +$185.00
    (estimated 90 active minutes/day × 30 days × $0.0686/min/node-group)
  Net monthly cost impact: +$185.00 (throughput-driven; replaces
    need for cluster resize which would cost +$2,400/month)
  Assumptions: 4-node ra3.16xlarge, us-east-1 pricing, peak hours
    4-8 hours/day, queue stalls cluster in those hours.
MIGRATION_STEPS:
  1. Snapshot the cluster (safety net):
     aws redshift create-cluster-snapshot --cluster-identifier analytics-cluster-prod --snapshot-identifier pre-wlm-20260805
  2. Apply auto WLM + concurrency scaling + SQA via parameter group:
     aws redshift modify-cluster-parameter-groups --parameter-group-name <group> --parameters \
       ParameterName=auto_wlm,ParameterValue=true \
       ParameterName=wlm_json_configuration,ParameterValue='[{"auto_wlm":true,"concurrency_scaling":"auto","short_query_queue_enable":true,"max_execution_time":120}]'
  3. Apply to cluster:
     aws redshift modify-cluster --cluster-identifier analytics-cluster-prod --cluster-parameter-group-name <group>
  4. Create dashboard materialized views (Step 8 SQL).
  5. Add QMR log rules (Step 6 JSON); review 7 days before promoting to abort.
  6. Monitor WLMQueueLength and ConcurrencyScalingClustersActive for 7 days.
CONFIRM: About to modify-cluster on analytics-cluster-prod (manual WLM
  → auto WLM + concurrency scaling + SQA). Throughput improvement ~250%
  at peak; concurrency-scaling cost +$185/month. Proceed? (yes/no)
```

## What the skill caught that a generic assistant misses

1. **Auto WLM and concurrency scaling are a paired recommendation.**
   A generic assistant says "add more queues to manual WLM." The skill
   identifies that manual WLM is the root cause — auto WLM + concurrency
   scaling together eliminate the static-slot bottleneck. The pair is
   the unit of recommendation.

2. **SQA is identified as the isolation layer.** The 200 ms lookups stuck
   behind 30-minute aggregates are an SQA problem, not a queue-count
   problem. The skill routes SQA as the third recommendation after
   WLM mode and scaling.

3. **Concurrency scaling cost is quantified.** The skill calculates $185/month
   scaling cost and contrasts it with the $2,400/month alternative of a
   permanent cluster resize. A generic assistant says "enable scaling"
   without the cost math.

4. **Priority routing prevents queue contention.** The skill recommends
   query priority (dashboard=Highest) and queue assignment rules so
   business-critical workloads get preferred slot allocation. A generic
   assistant leaves all queries at Normal priority.

5. **Materialized views stack on top of WLM tuning.** The dashboard
   aggregate scanning 12B rows is a materialized-view candidate. The
   skill stacks this data-path optimization on top of the WLM config
   change. A generic assistant captures only the WLM change.

6. **QMR rules start with log, not abort.** The skill recommends
   `action: log` first, then promotes to abort after 7 days of
   validation. A generic assistant jumps to abort, risking false
   positives on legitimate ETL.

## Slash-command invocation

```
/aws:optimize-redshift-wlm
```

Or via the orchestrator:

```
/aws:pipeline
You: "optimize our Redshift WLM for the Q4 FinOps review"
```

The orchestrator emits
`[Phase: Optimize | Skills routed: redshift-wlm-optimizer]` and hands off
to this skill for the optimization block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the new WLM configuration:

```bash
# Confirm auto WLM + concurrency scaling + SQA landed
aws redshift describe-cluster-configuration \
  --cluster-identifier analytics-cluster-prod \
  --output json | jq '.WLMConfiguration'

# Monitor WLMQueueLength for 7 days post-change
aws cloudwatch get-metric-statistics --namespace AWS/Redshift \
  --metric-name WLMQueueLength \
  --dimensions Name=ClusterIdentifier,Value=analytics-cluster-prod \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output json

# Monitor ConcurrencyScalingClustersActive
aws cloudwatch get-metric-statistics --namespace AWS/Redshift \
  --metric-name ConcurrencyScalingClustersActive \
  --dimensions Name=ClusterIdentifier,Value=analytics-cluster-prod \
  --start-time $(date -u -d '-7 days' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Sum --output json
```

If WLMQueueLength p99 drops below 5 and ConcurrencyScalingClustersActive
stays under 60 min/day, the optimization is confirmed.

## Fleet-wide extension

For a fleet of N Redshift clusters:

1. Pull all clusters with `aws redshift describe-clusters`.
2. Filter to clusters with `NodeType` starting with `ra3` (RA3 nodes).
3. Pull WLM JSON for each via `describe-cluster-configuration`.
4. For each cluster on manual WLM: flag for auto WLM migration.
5. For each cluster with WLMQueueLength p99 > 10: flag for concurrency
   scaling.
6. Sort by estimated throughput improvement (largest first).
7. Slice into batches of 3 clusters.
8. For each batch: emit per-cluster MIGRATION_STEPS, then a single
   CONFIRM for the batch.
9. Verify each batch before proceeding to the next.
