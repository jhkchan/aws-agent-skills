# Advanced Patterns — Redshift WLM Optimizer

Mindset principles, Step 0 non-obvious behaviours, Step 9 Spectrum/COPY optimization detail, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

## Mindset — the four principles

Four principles guide every recommendation:

- **Auto WLM adapts; manual WLM does not.** Auto WLM observes the live
  query mix and reallocates memory across queues in real time. Manual
  WLM's static slots under-allocate for bursts and over-allocate for
  lulls. The only justification for manual WLM is a strict isolation
  requirement that auto WLM cannot enforce.
- **Concurrency scaling is the elastic safety valve.** When the queue
  length grows, Redshift transparently adds clusters that share the
  load. The added clusters bill at the same rate as the primary; the
  cost is proportional to the workload spike, not a reserved size.
- **SQA + query priority are the isolation levers.** SQA removes short
  queries from the queue entirely. Query priority (Highest/High/Normal/
  Low) biases resource allocation toward business-critical workloads
  without starving others.
- **Materialized views and COPY are the data-path levers.** A
  materialised view converts a 30-minute dashboard aggregate into a
  sub-second lookup. A properly tuned COPY loads 10x faster than
  single-row inserts and produces no VACUUM debt.

## Step 0: Non-obvious behaviours that change the recommendation

These operational gotchas route a recommendation away from the obvious
choice:

- **Auto WLM and concurrency scaling are paired.** Enabling auto WLM
  without concurrency scaling still bounds throughput at base cluster
  capacity. Always enable both together.
- **Concurrency scaling bills per second of active cluster.** Cost is
  proportional to queue backlog duration, not a reserved size. For most
  workloads, sub-5% of the primary cluster's monthly cost.
- **SQA has a max-execution-time boundary.** Queries estimated to
  complete within the threshold (default 120 s, configurable 0-300 s)
  are routed to SQA. Set too low and SQA never fires; set too high and
  long queries steal SQA slots.
- **Query priority only biases allocation.** A Highest-priority query
  does NOT preempt running queries; it gets preferred access to the next
  free slot. Not a real-time SLA lever.
- **Manual WLM queues have a fixed slot count.** Slots map to memory
  (cluster_memory / total_slots_per_slice). Over-allocating slots to a
  queue starves the others.
- **Memory % per queue must sum to 100.** Rebalance the entire queue
  set, not one queue in isolation.
- **QMR rules operate on STL_QUERY_METRICS counters.** Metric is per-
  query CPU time, row scan count, memory (MB), elapsed time. Set
  thresholds at 10x median, not arbitrary values.
- **QMR action is `log` or `hop` or `abort`.** Use `log` first to
  baseline, then promote to `abort` once thresholds are validated.
- **AQUA is only useful for specific scan patterns.** Accelerates LIKE,
  REGEXP, UDF, hash-join on large VARCHAR. Does NOT accelerate numeric
  aggregation. Verify the workload pattern before enabling.
- **Materialized views auto-refresh on schedule.** Auto-refresh issues
  an incremental refresh if the base table changed. For dashboards, a
  5-15 minute refresh interval is typical.
- **COPY COMPUPDATE is on by default for first loads.** For subsequent
  loads with established encodings, turn OFF to avoid wasted compute.
- **Single-row INSERT generates VACUUM debt.** Each single-row INSERT
  creates a micro-block VACUUM must consolidate. Use COPY or a staging
  table + INSERT INTO ... SELECT instead.

## Step 4 — priority and queue-rule routing detail

Query priority (Highest / High / Normal / Low) biases resource
allocation. Queue assignment rules route queries to specific queues
based on user, group, or query label.

## Step 9 — Spectrum optimization and COPY bulk load

**Spectrum optimization:**

| Issue | Fix |
|---|---|
| External table has no partitions | Add partition columns and run `MSCK REPAIR TABLE` |
| Spectrum query scans entire table | Push down filter predicates; partition the data in S3 |
| Statistics missing on external columns | Run `ANALYZE` on the external table |

**COPY command optimization:**
```sql
-- First load on a new table
COPY sales
FROM 's3://etc/sales/'
IAM_ROLE 'arn:aws:iam::<acct>:role/<role>'
COMPUPDATE ON
MAXROWS 100000;

-- Subsequent incremental loads on existing encoding
COPY sales
FROM 's3://etc/sales-incremental/'
IAM_ROLE 'arn:aws:iam::<acct>:role/<role>'
COMPUPDATE OFF
MAXROWS 100000;
```

- `COMPUPDATE ON` (default) auto-selects column encodings on first load.
  Turn OFF for subsequent loads — encoding is already established.
- `MAXROWS` controls batch size for sort-key alignment. Default is
  typically fine; tune up for tables with many sort keys.
- Split large files in S3 to match the cluster's slice count
  (one file per slice minimum; multiples of slice count for parallelism).

## Recent AWS features (2024-2026)

- **Auto WLM GA (2024):** Dynamic memory allocation across queues
  based on observed query mix. Default for new clusters since 2024.
- **Concurrency Scaling cost optimization (2024-2025):** Per-second
  billing with 60-second minimum. Cost visibility via AWS Cost
  Explorer `Redshift:ConcurrencyScaling` usage type.
- **SQA threshold tuning (2024):** `max_execution_time` configurable
  0-300 s via parameter group.
- **Materialized Views auto-refresh (2024-2025):** Incremental refresh
  on managed schedule; supports CREATE MATERIALIZED VIEW ... AUTO
  REFRESH YES. Refresh state visible in SYS_MV_REFRESH_HISTORY.
- **AQUA for RA3 node types (2024):** Available on ra3.16xlarge and
  ra3.4xlarge. Enabled via `aqua-configuration-status`.
- **Redshift Data API (2024-2026):** Direct STL/SYS query access via
  `aws redshift-data execute-statement` without a JDBC connection.
- **Query Priority (2024):** Highest/High/Normal/Low in WLM JSON.
  Priority biases slot allocation, does not preempt running queries.
- **SYS_QUERY_HISTORY (2024-2025):** Serverless and provisioned
  unified query history view. Replaces STL_QUERY for cross-engine
  analysis.
