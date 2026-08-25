---
name: redshift-wlm-optimizer
description: 'Optimises Amazon Redshift Workload Management (WLM) across eleven dimensions: WLM queue configuration (auto vs manual WLM with static concurrency slots), concurrency scaling (automatic additional clusters that elastically scale query throughput), query priority (Highest/High/Normal/Low for ranked queue processing), queue assignment rules (user/group/query-label based routing), Short Query Acceleration (SQA — isolates short queries from long-running ones without a dedicated queue), workload management concurrency tuning (slots per queue, memory % per queue), memory allocation per queue (explicit % of cluster memory for manual WLM), query monitoring rules (QMR — metrics-based abort for runaway queries with CPU time, row count, query duration, and memory thresholds), AQUA (Advanced Query Accelerator for compute-heavy scans), materialized views (pre-computed aggregates for dashboard workloads with auto-refresh), data catalog external table optimization (Spectrum pushdown and partition pruning), and COPY...'
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline recommendation classification works from pasted STL/SYS system table query output, WLM configuration JSON, and CloudWatch RedshiftInsights metrics. Live-account optimization uses aws redshift describe-clusters, aws redshift describe-cluster-configuration, aws redshift describe-query, aws redshift describe-queries, aws redshift modify-cluster, aws cloudwatch get-metric-statistics (CPUUtilization...
metadata:
  domain: aws-cloudops
  complexity: medium
  requires_llm: 'true'
  phase: '3'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: optimize
  skill_class: capability
  lifecycle_status: active
  verdict_shape: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
  when_to_use: Optimising Redshift WLM queue configuration, switching from manual WLM to auto WLM with concurrency scaling, enabling Short Query Acceleration, defining queue assignment rules, tuning queue concurrency and memory %, writing query monitoring rules to abort runaway queries, evaluating AQUA for compute-heavy scans, adding materialized views for dashboard workloads, optimising Spectrum external table queries, or tuning COPY command bulk loads.
  when_not_to_use: Redshift cluster rightsizing or node type migration (use redshift-node-optimizer), Redshift Serverless capacity tuning (different configuration surface), Redshift data lake formation setup, Redshift ML model lifecycle, or Redshift troubleshooting (connection failures, query errors, node events — use the Redshift troubleshooter). This skill focuses on WLM and query-throughput optimization, not functional debugging of broken clusters.
  activation_triggers: optimise Redshift WLM, Redshift auto WLM, Redshift concurrency scaling, Redshift Short Query Acceleration, Redshift SQA, Redshift query priority, Redshift queue assignment rules, Redshift query monitoring rules, Redshift QMR runaway query, Redshift materialized views, Redshift AQUA, Redshift COPY command optimization, Redshift Spectrum external tables, Redshift slot count tuning, Redshift memory allocation per queue, Redshift queue stalls, Redshift FinOps, Redshift query throughput
  invocation_schema: 'Input: either (a) a cluster identifier + live-account context, (b) a describe-cluster-configuration WLM JSON payload, OR (c) STL_QUERY / STV_WLM_QUERY_STATE / STL_QUERY_METRICS query output with at least 14 days of observation. Output: a deterministic TARGET/VERDICT/REASON/RECOMMENDATION/ ESTIMATED_IMPACT/MIGRATION_STEPS block per cluster, where VERDICT is one of OPTIMIZED, FURTHER_OPTIMIZATION_AVAILABLE.'
  invocation_example: "# Minimal valid input (offline WLM classification):\nClusterIdentifier: analytics-cluster-prod\nNodeType: ra3.16xlarge\nNumberOfNodes: 4\nRegion: us-east-1\nWLM mode: manual (3 static queues)\nConcurrency scaling: disabled\nSQA: disabled\nMetrics (last 30 days):\n  - CPUUtilization avg: 88%, p95: 97%\n  - QueryDuration avg: 45 s, p95: 180 s\n  - QueryThroughput avg: 12/s, peak: 18/s\n  - WLMQueueLength avg: 4, p99: 22\n  - ConcurrencyScalingClustersActive: 0\nTop queries: dashboard aggregation (4 joins, GROUP BY date, 12B row scan)\nMaterialized views: none\nEmit the standard optimization block (TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_IMPACT, MIGRATION_STEPS)."
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: Redshift, WLM, Workload Management, auto WLM, concurrency scaling, Short Query Acceleration, SQA, query priority, queue assignment rules, query monitoring rules, QMR, materialized views, AQUA, COPY command, bulk load, Spectrum, external tables, data catalog, slot count, memory allocation, Analytics, FinOps
  tags: redshift, analytics, workload-management, wlm, cost-optimization, finops, concurrency-scaling, query-priority
---

# Redshift WLM Optimizer

## What this skill does

Translates an Amazon Redshift cluster's workload management
configuration and query execution patterns into a concrete
throughput-and-cost optimization recommendation. The verdict is the
highest-leverage action across eleven dimensions — WLM mode, concurrency
scaling, SQA, query priority, queue rules, concurrency tuning, memory
allocation, query monitoring rules, AQUA, materialized views, and bulk
load paths — applied in priority order. Always pairs the recommendation
with exact CLI commands or Data API statements.

## Quick navigation

| Section | What it covers | When to jump here |
|---|---|---|
| Quick start | Five headline rules and the throughput math | First read |
| Mindset | Why auto WLM + concurrency scaling wins | Approach |
| Verdict thresholds | Decision matrix at a glance | Classifying |
| Pre-flight data gate | STL/SYS tables, CloudWatch, describe-cluster | Before any rec |
| Step 0 non-obvious behaviours | Auto vs manual caveats, SQA, QMR | Edge cases |
| Step 1 WLM mode | Auto WLM vs manual WLM decision | Headline dimension |
| Step 2 Concurrency scaling | Elastic cluster add for throughput peaks | Queue stalls |
| Step 3 SQA | Short Query Acceleration isolation | Mixed workloads |
| Step 4 Priority and queue rules | Priority ranking and routing | Multi-tenant |
| Step 5 Concurrency + memory | Slots and memory % per queue | Manual WLM |
| Step 6 QMR | Metrics-based abort for runaway queries | Runaway defence |
| Step 7 AQUA | Advanced Query Accelerator | Compute-heavy scans |
| Step 8 Materialized views | Pre-computed aggregates for dashboards | Dashboards |
| Step 9 Spectrum and COPY | External table pushdown, bulk load | Data lake + ingest |
| Output format | VERDICT block + worked examples | Emitting result |
| Anti-Patterns — NEVER | Common misclassifications | Self-check |
| Pre-flight safety | CONFIRM gate, snapshot, maintenance | Before apply CLI |

## Quick start

- **Auto WLM is the default in 2026.** Auto WLM dynamically allocates
  memory and concurrency based on query mix. Pair it with concurrency
  scaling for elastic throughput. Manual WLM with static slots is a
  legacy pattern — only justified for highly predictable, single-
  workload clusters with strict isolation requirements.
- **Throughput formula (memorise this):**
  `effective_concurrency = base_slots × (1 + concurrency_scaling_clusters_active)`
  When queues stall, WLMQueueLength grows; concurrency scaling adds
  clusters to drain the backlog.
- **SQA prevents short queries from queuing behind long ones.** A 200 ms
  lookup should NOT wait behind a 30-minute aggregate. Enable SQA on
  every mixed-workload cluster.
- **Materialized views are the dashboard accelerator.** A 12-billion-row
  scan with 4 joins and GROUP BY date becomes a sub-second lookup when
  materialised. Auto-refresh keeps the view fresh.
- **COPY is the only performant bulk load path.** Single-row INSERTs
  generate as many VACUUM-required deletes as rows. Always use COPY
  with COMPUPDATE ON for first loads and MAXROWS tuning for sort-key
  alignment.

## Mindset

Redshift WLM optimization is a throughput-and-isolation decision, not
pure query tuning. The goal is the WLM configuration that maximises
query throughput while preserving workload isolation (short queries
complete fast, long queries get their fair share) — not the absolute
minimum concurrency that runs queries.

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Mindset — the four principles".
> Load when: deciding between auto/manual WLM, concurrency scaling, isolation levers, or data-path levers.

## Quick reference — verdict thresholds

| Observation (14-30 day window) | Verdict | Recommendation |
|---|---|---|
| WLM mode = manual AND mixed workload (short + long queries) | **FURTHER_OPTIMIZATION_AVAILABLE** (WLM mode) | Step 1 — switch to auto WLM |
| Concurrency scaling = disabled AND WLMQueueLength p99 > 10 AND ConcurrencyScalingClustersActive = 0 | **FURTHER_OPTIMIZATION_AVAILABLE** (concurrency scaling) | Step 2 — enable concurrency scaling |
| SQA = disabled OR SQA enabled with max-execution-time misconfigured AND short queries (>0 p95 wait time) exist | **FURTHER_OPTIMIZATION_AVAILABLE** (SQA) | Step 3 — enable / tune SQA |
| All queries at Normal priority AND business-critical workloads compete with batch | **FURTHER_OPTIMIZATION_AVAILABLE** (priority) | Step 4 — set query priority + queue rules |
| Manual WLM AND queue memory % misallocated (one queue > 60%, another < 10%) | **FURTHER_OPTIMIZATION_AVAILABLE** (memory tuning) | Step 5 — rebalance queue memory % |
| No query monitoring rules AND STL_QUERY_METRICS shows queries exceeding 10x median CPU/duration | **FURTHER_OPTIMIZATION_AVAILABLE** (QMR) | Step 6 — define QMR abort rules |
| AQUA = disabled AND workload dominated by scanning large VARCHAR columns | **FURTHER_OPTIMIZATION_AVAILABLE** (AQUA) | Step 7 — enable AQUA |
| Dashboard queries (repeated GROUP BY date pattern) AND no materialized views | **FURTHER_OPTIMIZATION_AVAILABLE** (materialized views) | Step 8 — create materialized views with auto-refresh |
| Spectrum queries scanning unpartitioned external tables | **FURTHER_OPTIMIZATION_AVAILABLE** (Spectrum) | Step 9 — add partitions and statistics |
| COPY operations with COMPUPDATE OFF OR single-row INSERTs in load path | **FURTHER_OPTIMIZATION_AVAILABLE** (COPY) | Step 9 — switch to COPY with COMPUPDATE ON |
| All dimensions verified AND auto WLM + concurrency scaling + SQA + QMR + materialized views in place | **OPTIMIZED** | Emit post-state verification |
| STL_QUERY data absent or window < 14 days | **NEED_MORE_INFO** | Pull 14-30 day STL/SYS data, re-evaluate |

## Pre-flight: data gate (run before any optimization decision)

Optimization decisions are only as good as the underlying data. Pull
these metrics before any recommendation. Full CLI and Data API
sequences are in `references/redshift-wlm-configuration-and-pricing.md`.

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Pre-flight data gate — data sources".
> Load when: gathering the eight required data sources (CLI, WLM JSON, STV/SYS/STL tables, CloudWatch) before any recommendation.

### Data-quality short-circuits

| Condition | Effect on optimization |
|---|---|
| `describe-clusters` returns `ClusterNotFound` | Cluster does not exist in this region. Skip. |
| `SYS_QUERY_HISTORY` empty over 14 days | Cluster dormant or SYS access misconfigured. **NEED_MORE_INFO**. |
| Observation window < 14 days | Workload may reflect atypical load. **NEED_MORE_INFO**. |
| `ConcurrencyScalingClustersActive` metric absent | Concurrency scaling not enabled. Confirm via WLM JSON. |
| `STL_QUERY_METRICS` rows < 100 | Sample too small for QMR thresholds. Use absolute thresholds. |
| Cluster `AvailabilityStatus = Maintenance` | Surface BLOCKED. Resolve maintenance before WLM change. |
| Cluster paused (serverless) | Different config surface. Surface scope mismatch. |

When STL/SYS system tables and CloudWatch disagree, the system tables
win — they are the source of truth for per-query execution detail.

## Process — Optimization logic (apply in order)

### Step 0: Non-obvious behaviours that change the recommendation

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 0: Non-obvious behaviours".
> Load when: applying any step — pairing rules, SQA boundary, priority semantics, slot/memory constraints, QMR counters, AQUA scan patterns, MV refresh, COMPUPDATE, VACUUM debt.

### Step 1: WLM mode — auto WLM vs manual WLM

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 1 — auto vs manual behaviour".
> Load when: comparing auto vs manual WLM behaviour before the decision gate.

**Decision gate:**

| Cluster workload | Verdict | Action |
|---|---|---|
| Mixed (short + long queries), variable mix | **FURTHER_OPTIMIZATION_AVAILABLE** | Switch to auto WLM + enable concurrency scaling |
| Single-workload, predictable, strict isolation required | KEEP manual WLM | Proceed to Step 5 (memory tuning) |
| Already on auto WLM with concurrency scaling enabled | No WLM-mode finding | Proceed to other dimensions |

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 1 — switch-to-auto-WLM CLI".
> Load when: applying the switch to auto WLM via parameter group.

### Step 2: Concurrency scaling — elastic throughput

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 2 — scaling behaviour and pricing".
> Load when: reasoning about per-second billing and typical cost share.

**Decision gate:**

| Observation | Verdict | Action |
|---|---|---|
| WLMQueueLength p99 > 10 AND ConcurrencyScalingClustersActive = 0 AND scaling disabled | **FURTHER_OPTIMIZATION_AVAILABLE** | Enable concurrency scaling |
| Scaling enabled AND active > 60 minutes/day | Verify the queue backlog is real (Step 5) | May need cluster resize instead |
| Scaling enabled AND active < 5 minutes/day | No scaling finding | Continue monitoring |

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 2 — enable scaling JSON".
> Load when: writing the per-queue concurrency_scaling JSON.

### Step 3: Short Query Acceleration (SQA)

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 3 — SQA isolation detail".
> Load when: explaining how SQA bypass works.

**SQA decision gate:**

| Observation | Verdict | Action |
|---|---|---|
| SQA disabled AND short queries (>0 p95 wait) exist | **FURTHER_OPTIMIZATION_AVAILABLE** | Enable SQA |
| SQA enabled but max-execution-time misconfigured | **FURTHER_OPTIMIZATION_AVAILABLE** | Tune SQA threshold |
| All queries long-running (no short queries in mix) | No SQA finding | Skip |

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 3 — enable SQA JSON".
> Load when: writing the SQA queue JSON and tuning max_execution_time.

### Step 4: Query priority and queue assignment rules

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 4 — priority and routing detail".
> Load when: routing queries by user, group, or query label.

**Priority guidance:**

| Workload | Suggested priority |
|---|---|
| Customer-facing dashboard or API | Highest |
| Operational reporting (hourly) | High |
| Batch ETL | Normal |
| Ad-hoc analyst queries | Low |
| Background maintenance (VACUUM, ANALYZE) | Low |

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 4 — queue rule examples".
> Load when: writing user_group / query_group routing rules.

### Step 5: Concurrency and memory tuning (manual WLM only)

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 5 — manual WLM queue JSON".
> Load when: defining slot counts and memory_percent per manual queue.

**Memory % must sum to 100 across all queues.** Rebalance when
adding/removing a queue. Slot count guidance:

| Workload type | Slots per queue | Rationale |
|---|---|---|
| Dashboard / API (short, parallel) | 10-20 | Many parallel slots, low memory per slot |
| ETL (long, memory-heavy) | 3-7 | Fewer slots, more memory per slot |
| Ad-hoc analyst | 2-5 | Limit blast radius |

### Step 6: Query monitoring rules (QMR)

QMR observes per-query metrics in STL_QUERY_METRICS and either logs,
hops, or aborts queries that breach thresholds.

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 6 — QMR metrics and rule".
> Load when: writing QMR predicates or validating thresholds before promoting to abort.

### Step 7: AQUA (Advanced Query Accelerator)

AQUA accelerates specific scan patterns by pushing computation to the
storage layer.

**AQUA acceleration applies to:** LIKE / ILIKE on large VARCHAR columns,
REGEXP pattern matching, hash joins on string columns, UDFs on scanned
data.

**AQUA does NOT accelerate:** Numeric aggregation (SUM, AVG, COUNT),
date/time filtering, equality joins on integer keys.

**Decision gate:**

| Workload | AQUA value |
|---|---|
| Dominated by LIKE/REGEXP on large VARCHAR | High |
| Mixed scan with some LIKE/REGEXP | Medium |
| Pure numeric aggregation | None — skip |

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 7 — enable AQUA CLI".
> Load when: enabling AQUA via modify-cluster (requires reboot).

### Step 8: Materialized views for dashboard workloads

Materialized views pre-compute aggregates. For dashboards with repeated
GROUP BY date patterns, a materialised view converts a multi-minute
aggregate into a sub-second lookup.

**Pattern detection:** Same query shape repeated many times per day
(from SYS_QUERY_HISTORY); heavy aggregate (GROUP BY date, dimension);
base table changes less frequently than the query runs.

> **Moved verbatim** → [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) § "Step 8 — materialized view example".
> Load when: creating the dashboard materialized view with AUTO REFRESH.

### Step 9: Spectrum external tables and COPY bulk load

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Step 9 — Spectrum and COPY".
> Load when: optimizing external tables (partitions, pushdown, ANALYZE) or COPY loads (COMPUPDATE, MAXROWS, file splitting).

### Step 10: Impact estimation

Compute the throughput improvement for each recommendation:

```
current_effective_concurrency = base_slots × (1 + avg_active_scaling_clusters)
projected_effective_concurrency = projected_base_slots × (1 + projected_avg_scaling_clusters)
throughput_improvement = (projected - current) / current
```

For materialized views, compute the dashboard duration improvement
from STL_QUERY baseline vs. estimated sub-second MV hit.

Always state assumptions: queue length baseline, concurrency scaling
active minutes/day, query mix (% short vs long), materialized view hit
rate, and node type.

### Step 11: Final verdict

- Any dimension recommends a change → **FURTHER_OPTIMIZATION_AVAILABLE**.
- All dimensions verified AND auto WLM + concurrency scaling + SQA +
  QMR + materialized views in place → **OPTIMIZED**.
- Change applied and verified this session → **OPTIMIZED** (post-state).
- Data insufficient (STL empty, window < 14 days) → **NEED_MORE_INFO**.

Never emit `FURTHER_OPTIMIZATION_AVAILABLE` without first discharging
every `NEED_MORE_INFO` / `BLOCKED` gate.

## Output format

```text
TARGET: <cluster-identifier>
VERDICT: OPTIMIZED | FURTHER_OPTIMIZATION_AVAILABLE
REASON: <1-2 sentences naming the recommendation and the supporting data>
RECOMMENDATION:
  Current: <WLM mode>, concurrency scaling <on/off>, SQA <on/off>, <queue count> queues,
    <materialized view count> materialized views, QMR <rule count> rules
  Proposed: <WLM mode>, concurrency scaling <on/off>, SQA <on/off>, <queue count> queues,
    <materialized view count> materialized views, QMR <rule count> rules
  Dimensions changed: <wlm_mode | concurrency_scaling | sqa | priority | memory_tuning | qmr | aqua | materialized_views | spectrum | copy>
  Dimensions checked: <list ALL eleven, each ✓ (no finding) or → (finding)>
  Confidence: <HIGH/MEDIUM/LOW> — <one-line rationale>
ESTIMATED_IMPACT:
  Current throughput: <queries/sec, p95 wait time>
  Projected throughput: <queries/sec, p95 wait time>
  Throughput improvement: <percent>
  Monthly concurrency-scaling cost delta: $<amount>
  Net monthly cost impact: $<amount>
  Assumptions: <list (cluster size, queue baseline, etc.)>
MIGRATION_STEPS:
  1. <specific action with CLI command>
  2. <verification step>
CONFIRM: Before executing any state-changing CLI, emit and await operator
  approval: "CONFIRM: About to <action> on <cluster-identifier> in <region>.
  Proceed? (yes/no)"
```

Full worked examples are in `references/worked-examples-and-edge-cases.md`.

## STRICT output contract

These rules are hard constraints. Violating any one produces a
misclassification or an arithmetic contradiction that breaks downstream
FinOps automation. Self-check EVERY emitted block before returning.

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: FURTHER_OPTIMIZATION_AVAILABLE` with
   `Throughput improvement: 0%`.** If every dimension nets zero
   throughput delta, the verdict MUST be `OPTIMIZED`.
2. **NEVER show savings math that does not balance.** `Current
   throughput + projected delta MUST equal Projected throughput`.
3. **NEVER emit scratch lines** ("WAIT — recompute", "Hmm, let me redo",
   "corrected:") in the output. Finalize the math before emitting.
4. **NEVER recommend switching to auto WLM without also recommending
   concurrency scaling.** The two are paired.
5. **NEVER omit a dimension from the RECOMMENDATION block.** The
   `Dimensions checked` line MUST list all eleven dimensions.
6. **NEVER present a cost-increasing change as "OPTIMIZED."** Surface
   the cost delta explicitly; set verdict `FURTHER_OPTIMIZATION_AVAILABLE`
   if the recommendation increases spend, even if throughput improves.
7. **NEVER round intermediate formula steps differently from the final
   figure.** Compute at full precision, round only the displayed result.

### Perfect example output — FURTHER_OPTIMIZATION_AVAILABLE

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
  Monthly concurrency-scaling cost delta: $185.00
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
  → auto WLM + concurrency scaling + SQA). Throughput ~250% at peak;
  concurrency-scaling cost +$185/month. Proceed? (yes/no)
```

**Self-check before emit:**
- [ ] `Current throughput + projected delta == Projected throughput`?
- [ ] All eleven dimensions listed in `Dimensions checked`?
- [ ] Every `→` dimension has a corresponding MIGRATION_STEPS entry?
- [ ] No scratch/recompute text in the block?

## Verdict semantics

| Verdict | When to emit |
|---|---|
| `FURTHER_OPTIMIZATION_AVAILABLE` | At least one dimension has a concrete, throughput-improving or cost-reducing recommendation. |
| `OPTIMIZED` | All dimensions pass (auto WLM + concurrency scaling + SQA + QMR + materialized views in place); OR a change was applied and verified this session with metrics confirming improvement. |
| `NEED_MORE_INFO` | Data gate failed: STL/SYS tables empty, window < 14 days, or describe-cluster-configuration inaccessible. |
| `BLOCKED` | Hard precondition prevents evaluation: cluster in Maintenance, IAM denies redshift:DescribeClusters, serverless cluster (different surface). |

**Zero-improvement rule:** If throughput_improvement == 0% AND cost
delta == $0 for every dimension, verdict MUST be `OPTIMIZED`, never
`FURTHER_OPTIMIZATION_AVAILABLE`. Exception: a latency-only improvement
with no cost or throughput change is surfaced in REASON, not as a
throughput improvement.

## Anti-Patterns — NEVER (top 5)

1. **NEVER recommend switching to auto WLM without also recommending
   concurrency scaling.** Auto WLM without scaling still bounds
   throughput at base cluster capacity. The pair is the unit of
   recommendation.

2. **NEVER enable concurrency scaling without verifying the queue
   backlog is real.** If WLMQueueLength is consistently 0 and the
   scaling cluster activates, the workload is misclassified (long
   queries at low concurrency masquerading as a backlog). Fix the WLM
   queue first, then enable scaling.

3. **NEVER set a QMR rule to `action: abort` on the first pass.**
   Always run with `action: log` for 7 days to validate the threshold
   against false positives. An over-aggressive abort rule kills
   legitimate long-running ETL.

4. **NEVER recommend AQUA for a numeric-aggregation workload.** AQUA
   accelerates LIKE/REGEXP/hash-join on VARCHAR columns only; it does
   not accelerate SUM/AVG/COUNT. A misapplied AQUA recommendation adds
   cost with no benefit.

5. **NEVER create a materialized view without also recommending
   auto-refresh.** A stale materialized view silently returns wrong
   results; auto-refresh keeps the view consistent with the base table
   on a managed schedule.

Extended anti-patterns in `references/worked-examples-and-edge-cases.md`.

## Pre-flight safety checks (run before any remediation CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation,
  emit and await operator approval. Do NOT execute until confirmed.
- **Snapshot the cluster before any WLM change.** WLM parameter-group
  changes take effect on the next query; a snapshot is the rollback net.
- **WLM JSON changes apply on the next query, not instantly.** Allow
  up to 5 minutes for the configuration to propagate.
- **Concurrency scaling adds clusters within 60 seconds.** First query
  on a scaling cluster may see a 1-2 second routing latency.
- **QMR rule changes apply immediately.** An abort rule on a running
  query will abort it. Confirm before promoting log to abort.
- **Materialized view creation locks the base table briefly.** Schedule
  during low-traffic windows for very large tables.
- **AQUA enable requires a cluster reboot.** Schedule in maintenance.
- **Verify Spectrum partitions are in the same region as the cluster.**
  Cross-region Spectrum reads add latency and data-transfer cost.
- **COPY COMPUPDATE ON recomputes encodings.** Use only on first load;
  turn OFF for incremental loads to avoid wasted compute.
- **Bulk-operation limit:** Process at most 3 clusters per batch. Sort
  by estimated throughput improvement, verify each batch first.

## Recent AWS features (2024-2026)

> **Moved verbatim** → [references/advanced-patterns.md](references/advanced-patterns.md) § "Recent AWS features (2024-2026)".
> Load when: using Auto WLM GA, per-second scaling billing, SQA tuning, MV auto-refresh, AQUA on RA3, Data API, query priority, or SYS_QUERY_HISTORY.

## References

- `references/redshift-wlm-configuration-and-pricing.md` — pricing
  tables, node-type memory mapping, WLM JSON schema, SQA threshold
  guidance, QMR metric reference, AQUA acceleration patterns,
  materialized view refresh intervals, regional pricing multipliers.
- `references/worked-examples-and-edge-cases.md` — full worked
  examples (auto WLM migration, SQA enablement, materialized views,
  QMR setup, already-optimal, NEED_MORE_INFO, end-to-end walkthrough),
  CLI failure handling, operational edge cases, extended NEVER list.

## References (load on demand)

- [references/redshift-wlm-configuration-and-pricing.md](references/redshift-wlm-configuration-and-pricing.md) — pricing tables and WLM JSON schema; now also holds the pre-flight data-source listing and the per-step WLM/SQA/QMR/AQUA/MV CLI and JSON moved from SKILL.md
- [references/worked-examples-and-edge-cases.md](references/worked-examples-and-edge-cases.md) — full worked examples, CLI failure handling, operational edge cases, extended NEVER list (existing)
- [references/advanced-patterns.md](references/advanced-patterns.md) — four mindset principles, Step 0 gotchas, Spectrum/COPY optimization detail, recent AWS features

## Domain

AWS CloudOps / Redshift Analytics Workload Management & FinOps.

## AWS documentation

- **Amazon Redshift Database Developer Guide** — https://docs.aws.amazon.com/redshift/latest/dg/welcome.html
- **Redshift WLM** — https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm.html
- **Redshift Concurrency Scaling** — https://docs.aws.amazon.com/redshift/latest/dg/concurrency-scaling.html
- **Short Query Acceleration** — https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm-short-query-acceleration.html
- **Query Monitoring Rules** — https://docs.aws.amazon.com/redshift/latest/dg/cm-c-wlm-query-monitoring-rules.html
- **AQUA (Advanced Query Accelerator)** — https://docs.aws.amazon.com/redshift/latest/dg/aqua.html
- **Materialized Views** — https://docs.aws.amazon.com/redshift/latest/dg/materialized-view-overview.html
- **Amazon Redshift Spectrum** — https://docs.aws.amazon.com/redshift/latest/dg/c-using-spectrum.html
- **COPY command** — https://docs.aws.amazon.com/redshift/latest/dg/r_COPY.html
- **Redshift system tables (STL/SYS)** — https://docs.aws.amazon.com/redshift/latest/dg/c_intro_STL_tables.html
- **AWS CLI Redshift reference** — https://docs.aws.amazon.com/cli/latest/reference/redshift/
- **AWS Well-Architected Framework — Performance Efficiency** — https://docs.aws.amazon.com/wellarchitected/latest/performance-efficiency-pillar/welcome.html
